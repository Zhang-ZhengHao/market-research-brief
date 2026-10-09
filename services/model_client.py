"""Optional OpenAI-compatible report client.

The demo never requires this module to make a network call.  It is deliberately
small so a client can point it at any compatible provider without putting a key
in the browser or repository.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import Report, SourceDocument, SourceSummary
from .report import evidence_excerpt


class ModelClientError(RuntimeError):
    """A user-readable model configuration or response error."""


AI_FEATURE_FLAG = "INSIGHT_MONITOR_AI_ENABLED"
MAX_AI_SOURCES = 5
MAX_AI_CHARS = 40_000
_TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}


def env_flag(name: str, default: bool = False) -> bool:
    """Read a conservative boolean feature flag from the environment."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


class OpenAICompatibleReportClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: int = 45,
        *,
        enabled: bool | None = None,
        max_sources: int = MAX_AI_SOURCES,
        max_chars: int = MAX_AI_CHARS,
    ) -> None:
        if not api_key.strip():
            raise ModelClientError("未配置模型 API Key")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model.strip() or "gpt-4o-mini"
        self.timeout = timeout
        # Direct construction remains a backwards-compatible programmatic
        # override.  Environment-created clients are offline unless the
        # explicit feature flag is enabled (see ``from_env``).
        self.enabled = True if enabled is None else bool(enabled)
        self.max_sources = max(1, int(max_sources))
        self.max_chars = max(1, int(max_chars))
        # Tests/integrators may inject a callable; otherwise resolve the module
        # seam at call time so monkeypatching remains effective.
        self._urlopen = None

    @classmethod
    def from_env(cls, *, enabled: bool | None = None) -> "OpenAICompatibleReportClient | None":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or not (env_flag(AI_FEATURE_FLAG) if enabled is None else enabled):
            return None
        return cls(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            enabled=True,
        )

    def generate_report(self, topic: str, angle: str, documents: list[SourceDocument]) -> Report:
        if not self.enabled:
            raise ModelClientError("真实 AI 功能未开启")
        if len(documents) > self.max_sources:
            raise ModelClientError(f"AI 一次最多处理 {self.max_sources} 份资料")
        total_chars = sum(len(document.text or "") for document in documents)
        if total_chars > self.max_chars:
            raise ModelClientError(
                f"AI 资料合计 {total_chars} 字符，最多支持 {self.max_chars} 字符"
            )
        successful = [document for document in documents if document.status == "success" and document.text]
        if not successful:
            raise ModelClientError("没有可发送给模型的正文")
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是严谨的研究助理。只根据给定来源生成中文 JSON。"
                        "不要编造来源没有说过的事实；每个结论都要能回到 source_index。"
                    ),
                },
                {"role": "user", "content": self._prompt(topic, angle, documents)},
            ],
        }
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "InsightMonitor/0.1",
            },
            method="POST",
        )
        try:
            open_fn = self._urlopen or urlopen
            with open_fn(request, timeout=self.timeout) as response:
                raw = response.read(1_000_000).decode("utf-8", errors="replace")
            body = json.loads(raw)
            content = body["choices"][0]["message"]["content"]
            data = _parse_json_content(content)
            return self._to_report(topic, angle, documents, data)
        except HTTPError as exc:
            raise ModelClientError(f"模型服务返回 HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise ModelClientError("模型服务连接失败或超时") from exc
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ModelClientError("模型返回格式无法识别") from exc

    @staticmethod
    def _prompt(topic: str, angle: str, documents: list[SourceDocument]) -> str:
        source_blocks = []
        for index, document in enumerate(documents):
            if document.status != "success":
                continue
            source_blocks.append(
                f"[source_index={index}] 标题：{document.title}\n正文：{document.text[:12000]}"
            )
        return (
            f"主题：{topic}\n报告角度：{angle}\n\n"
            "请返回 JSON，字段必须包括：executive_summary、common_points、differences、changes、actions，"
            "以及 sources。前五个字段都是字符串数组；sources 是对象数组，每项包括 source_index、summary。\n\n"
            + "\n\n".join(source_blocks)
        )

    @staticmethod
    def _to_report(topic: str, angle: str, documents: list[SourceDocument], data: dict) -> Report:
        source_data = data.get("sources") if isinstance(data.get("sources"), list) else []
        indexed_sources: dict[int, list[dict]] = {}
        malformed_index = False
        for item in source_data:
            if not isinstance(item, dict):
                malformed_index = True
                continue
            source_index = _coerce_source_index(item.get("source_index"))
            if source_index is None or not 0 <= source_index < len(documents):
                malformed_index = True
                continue
            indexed_sources.setdefault(source_index, []).append(item)

        duplicate_indexes = {index for index, items in indexed_sources.items() if len(items) > 1}
        successful_indexes = {
            index for index, document in enumerate(documents) if document.status == "success"
        }
        missing_indexes = successful_indexes - indexed_sources.keys()
        failed_indexes_returned = {
            index
            for index in indexed_sources
            if documents[index].status != "success"
        }
        source_summaries: list[SourceSummary] = []
        for index, document in enumerate(documents):
            matches = indexed_sources.get(index, [])
            match = matches[0] if len(matches) == 1 and index not in duplicate_indexes else {}
            if document.status != "success":
                summary = ""
            else:
                summary = str(match.get("summary", "")).strip() or evidence_excerpt(document.text)
            source_summaries.append(
                SourceSummary(
                    url=document.url,
                    title=document.title or "未命名资料",
                    summary=summary,
                    date_hint=document.date_hint,
                    status=document.status,
                    error=document.error,
                    source_kind=document.source_kind,
                    evidence=evidence_excerpt(document.text) if document.status == "success" else "",
                )
            )
        failed = [document for document in documents if document.status != "success"]
        warnings = ["AI 结果必须结合原文人工复核。"]
        if malformed_index or duplicate_indexes or missing_indexes:
            warnings.append(
                "模型返回的来源索引存在重复、缺失或越界，相关摘要已回退到原文证据，请人工复核。"
            )
        if failed_indexes_returned:
            warnings.append("模型为不可用资料返回了摘要，相关内容已丢弃，请人工复核。")
        if failed:
            warnings.append(f"有 {len(failed)} 份资料不可用。")
        return Report(
            topic=topic,
            angle=angle,
            mode="真实 AI",
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            executive_summary=_string_list(data.get("executive_summary")),
            common_points=_string_list(data.get("common_points")),
            differences=_string_list(data.get("differences")),
            changes=_string_list(data.get("changes")),
            actions=_string_list(data.get("actions")),
            sources=source_summaries,
            warnings=warnings,
        )


def _parse_json_content(content: object) -> dict:
    text = str(content or "").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.S)
    if fenced:
        text = fenced.group(1)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("response is not an object")
    return parsed


def _coerce_source_index(value: object) -> int | None:
    """Accept integer indexes and the numeric strings common in model JSON."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d+", value.strip()):
        return int(value.strip())
    return None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

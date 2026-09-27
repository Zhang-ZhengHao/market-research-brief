"""Build deterministic demo reports and provide a seam for real AI reports."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Protocol

from .models import Report, SourceDocument, SourceSummary


class ReportModelClient(Protocol):
    def generate_report(self, topic: str, angle: str, documents: list[SourceDocument]) -> Report:
        ...


EVIDENCE_MAX_CHARS = 240


def _first_sentences(text: str, limit: int = 240) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if len(normalized) <= limit:
        return normalized
    pieces = re.split(r"(?<=[。！？.!?])\s*", normalized)
    selected = ""
    for piece in pieces:
        if not piece:
            continue
        candidate = f"{selected}{piece}"
        if len(candidate) > limit:
            break
        selected = candidate
    return (selected or normalized[:limit]).rstrip() + "…"


def evidence_excerpt(text: str, limit: int = EVIDENCE_MAX_CHARS) -> str:
    """Return a bounded, verbatim excerpt that remains a substring of the source."""
    raw = str(text or "").strip()
    if len(raw) <= limit:
        return raw
    boundaries = [raw.rfind(mark, 0, limit + 1) for mark in "。！？.!?"]
    boundary = max(boundaries, default=-1)
    if boundary >= max(1, limit // 2):
        return raw[: min(boundary + 1, limit)].rstrip()
    return raw[:limit].rstrip()


def _angle_action(angle: str, topic: str) -> str:
    if angle == "内容选题":
        return f"围绕“{topic}”做一篇对比型内容，并在发布前回看每份来源原文。"
    if angle == "研究简报":
        return "把来源按日期和可信度再核验一次，再将结论交给相关负责人。"
    return "把共同点作为当前判断，把差异和未证实信息列入人工复核清单。"


def build_report(
    topic: str,
    angle: str,
    documents: list[SourceDocument],
    *,
    mode: str = "演示规则",
    model_client: ReportModelClient | None = None,
) -> Report:
    topic = (topic or "未命名主题").strip()
    angle = (angle or "竞品速览").strip()
    if model_client is not None:
        try:
            return model_client.generate_report(topic, angle, documents)
        except Exception as exc:
            fallback = _build_deterministic(topic, angle, documents, "演示规则（AI失败回退）")
            return Report(
                **{
                    **fallback.__dict__,
                    "warnings": [
                        *fallback.warnings,
                        f"真实 AI 汇总失败，已回退规则结果：{str(exc) or exc.__class__.__name__}",
                    ],
                }
            )
    return _build_deterministic(topic, angle, documents, mode)


def _build_deterministic(topic: str, angle: str, documents: list[SourceDocument], mode: str) -> Report:
    successful = [document for document in documents if document.status == "success" and document.text.strip()]
    failed = [document for document in documents if document.status != "success"]
    summaries = [
        SourceSummary(
            url=document.url,
            title=document.title or "未命名页面",
            summary=_first_sentences(document.text),
            date_hint=document.date_hint,
            status=document.status,
            error=document.error,
            source_kind=document.source_kind,
            evidence=evidence_excerpt(document.text) if document.status == "success" else "",
        )
        for document in documents
    ]

    if successful:
        executive = [
            f"本次围绕“{topic}”处理了 {len(successful)} 个成功来源。",
            "摘要来自用户提供的资料正文，重要判断仍需打开原文或回看粘贴内容人工复核。",
        ]
        common = [
            f"成功来源都与“{topic}”相关，适合先建立信息框架。",
            "各来源均保留了来源信息或原文证据，便于后续核验和补充。",
        ]
        differences = [
            "不同来源的叙述重点、发布时间和细节深度可能不同，不能直接视为同一事实。",
            "当前规则报告不会替用户判断来源权威性，需结合来源背景复核。",
        ]
        changes = [
            "后续新增资料可按日期与本次来源逐条对照，优先检查新出现的名词、数字和立场变化。"
        ]
        actions = [_angle_action(angle, topic)]
    else:
        executive = ["没有成功提取到可分析的资料正文，请补充公开地址或直接粘贴正文。"]
        common = []
        differences = []
        changes = []
        actions = ["先补充一个可公开访问的地址，或直接粘贴正文，再重新生成报告。"]

    warnings = []
    if mode != "真实 AI":
        warnings.append("当前为演示/规则汇总，不代表实时事实，也不保证结论准确。")
    if failed:
        warnings.append(f"有 {len(failed)} 个来源未能读取：" + "；".join(document.error for document in failed))

    return Report(
        topic=topic,
        angle=angle,
        mode=mode,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        executive_summary=executive,
        common_points=common,
        differences=differences,
        changes=changes,
        actions=actions,
        sources=summaries,
        warnings=warnings,
    )


def report_to_dict(report: Report) -> dict[str, Any]:
    return {
        "topic": report.topic,
        "angle": report.angle,
        "mode": report.mode,
        "generated_at": report.generated_at,
        "executive_summary": list(report.executive_summary),
        "common_points": list(report.common_points),
        "differences": list(report.differences),
        "changes": list(report.changes),
        "actions": list(report.actions),
        "sources": [
            {
                "url": source.url,
                "title": source.title,
                "summary": source.summary,
                "date_hint": source.date_hint,
                "status": source.status,
                "error": source.error,
                "source_kind": source.source_kind,
                "evidence": source.evidence,
            }
            for source in report.sources
        ],
        "warnings": list(report.warnings),
    }

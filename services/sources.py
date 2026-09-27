"""Helpers for normalizing user-provided research sources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .extractor import MAX_TEXT_CHARS
from .models import SourceDocument
from .urls import validate_urls


MAX_PASTED_SOURCES = 5
MAX_TOTAL_PASTED_CHARS = 40_000


def build_pasted_source(title: str, url: str, text: str) -> SourceDocument:
    """Validate and normalize one source pasted by the user."""
    cleaned_text = str(text or "").strip()
    if not cleaned_text:
        raise ValueError("请粘贴至少一段正文。")
    if len(cleaned_text) > MAX_TEXT_CHARS:
        raise ValueError(f"正文过长（{len(cleaned_text)} 字符），最多支持 {MAX_TEXT_CHARS} 字符。")
    cleaned_url = str(url or "").strip()
    if cleaned_url:
        validation = validate_urls([cleaned_url], max_urls=1)
        if validation.errors or not validation.urls:
            raise ValueError(validation.errors[0] if validation.errors else "来源链接无法识别。")
        cleaned_url = validation.urls[0]
    return SourceDocument(
        url=cleaned_url,
        title=str(title or "").strip() or "手工粘贴资料",
        text=cleaned_text,
        status="success",
        source_kind="pasted",
    )


def build_pasted_sources(entries: Sequence[Mapping[str, str]]) -> list[SourceDocument]:
    """Validate a batch of pasted sources atomically and preserve input order."""
    if not entries:
        raise ValueError("请至少填写一份资料。")
    if len(entries) > MAX_PASTED_SOURCES:
        raise ValueError(f"一次最多支持 {MAX_PASTED_SOURCES} 份资料。")

    documents: list[SourceDocument] = []
    total_chars = 0
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, Mapping):
            raise ValueError(f"第 {index} 份资料格式无法识别。")
        try:
            document = build_pasted_source(
                entry.get("title", ""),
                entry.get("url", ""),
                entry.get("text", ""),
            )
        except ValueError as exc:
            raise ValueError(f"第 {index} 份资料：{exc}") from exc
        total_chars += len(document.text)
        if total_chars > MAX_TOTAL_PASTED_CHARS:
            raise ValueError(
                f"粘贴资料当前合计 {total_chars} 字符，最多支持 {MAX_TOTAL_PASTED_CHARS} 字符，请删减或拆成多次报告。"
            )
        documents.append(document)
    return documents

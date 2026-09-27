"""Small dependency-free HTML text extractor."""

from __future__ import annotations

import re
from html.parser import HTMLParser

from .models import SourceDocument


MAX_TEXT_CHARS = 12_000
_SPACE_RE = re.compile(r"\s+")


class _PageParser(HTMLParser):
    _SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}
    _LAYOUT_SKIP_TAGS = {"nav", "footer", "header", "aside"}
    _CONTENT_TAGS = {"article", "main", "p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.fallback_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self._skip_depth = 0
        self._layout_skip_depth = 0
        self._body_depth = 0
        self._title_depth = 0
        self._content_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        if tag == "body":
            self._body_depth += 1
        if tag in self._LAYOUT_SKIP_TAGS:
            self._layout_skip_depth += 1
        if tag == "title":
            self._title_depth += 1
        if tag in self._CONTENT_TAGS:
            self._content_depth += 1
        if tag == "meta":
            name = (attr_map.get("name") or attr_map.get("property") or "").lower()
            content = attr_map.get("content", "").strip()
            if name and content:
                self.meta[name] = content

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag == "body" and self._body_depth:
            self._body_depth -= 1
        if tag in self._LAYOUT_SKIP_TAGS and self._layout_skip_depth:
            self._layout_skip_depth -= 1
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        if tag in self._CONTENT_TAGS and self._content_depth:
            self._content_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = _SPACE_RE.sub(" ", data).strip()
        if not cleaned:
            return
        if self._title_depth:
            self.title_parts.append(cleaned)
        if self._body_depth and not self._layout_skip_depth:
            self.fallback_parts.append(cleaned)
        if self._content_depth:
            self.body_parts.append(cleaned)


def _join(parts: list[str]) -> str:
    return _SPACE_RE.sub(" ", " ".join(parts)).strip()


def extract_html(html: str, url: str, max_chars: int = MAX_TEXT_CHARS) -> SourceDocument:
    parser = _PageParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        # A malformed page should become a readable empty result, not a server error.
        return SourceDocument(url=url, status="error", error="网页内容无法解析")

    title = _join(parser.title_parts) or parser.meta.get("og:title", "") or "未命名页面"
    text = _join(parser.body_parts) or _join(parser.fallback_parts)
    if not text:
        return SourceDocument(
            url=url,
            title=title,
            date_hint=_date_hint(parser.meta),
            status="error",
            error="页面没有可提取的正文",
        )
    return SourceDocument(
        url=url,
        title=title[:240],
        text=text[:max_chars],
        date_hint=_date_hint(parser.meta),
    )


def _date_hint(meta: dict[str, str]) -> str:
    for key in ("article:published_time", "date", "pubdate", "datepublished", "og:updated_time"):
        if meta.get(key):
            return meta[key][:80]
    return ""

"""Fetch public HTML pages with conservative SSRF and resource limits."""

from __future__ import annotations

import socket
import time
from collections.abc import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
    urlopen,
)

from .extractor import MAX_TEXT_CHARS, extract_html
from .models import SourceDocument
from .urls import PublicUrlError, normalize_public_url, resolve_public_host


DEFAULT_TIMEOUT = 12
DEFAULT_TOTAL_TIMEOUT = 20
MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 4
USER_AGENT = "InsightMonitor/0.1 (+public-page-research)"
_REDIRECT_CODES = {301, 302, 303, 307, 308}


class _NoRedirectHandler(HTTPRedirectHandler):
    """Return redirect responses to the caller for hop-by-hop validation."""

    def http_error_301(self, req, fp, code, msg, headers):  # noqa: N802
        return fp

    def http_error_302(self, req, fp, code, msg, headers):  # noqa: N802
        return fp

    def http_error_303(self, req, fp, code, msg, headers):  # noqa: N802
        return fp

    def http_error_307(self, req, fp, code, msg, headers):  # noqa: N802
        return fp

    def http_error_308(self, req, fp, code, msg, headers):  # noqa: N802
        return fp


_SAFE_OPENER = build_opener(_NoRedirectHandler())


def _header(response: object, name: str) -> str:
    headers = getattr(response, "headers", None)
    if headers is None:
        return ""
    try:
        value = headers.get(name, "")
    except AttributeError:
        return ""
    if not value:
        try:
            for key, candidate in headers.items():
                if str(key).lower() == name.lower():
                    value = candidate
                    break
        except AttributeError:
            return ""
    return str(value or "")


def _response_status(response: object) -> int:
    value = getattr(response, "status", None)
    if value is None:
        value = getattr(response, "code", 200)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 200


def _close_response(response: object) -> None:
    close = getattr(response, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            return


def _safe_open_once(
    request: Request,
    timeout: float,
    opener: Callable[..., object] | None,
) -> object:
    if opener is not None:
        return opener(request, timeout=timeout)
    # ``_SAFE_OPENER`` disables urllib's automatic redirect following.  The
    # explicit loop below validates every Location target before opening it.
    return _SAFE_OPENER.open(request, timeout=timeout)


def _redirect_target(current_url: str, response: object) -> str | None:
    status = _response_status(response)
    if status not in _REDIRECT_CODES:
        return None
    location = _header(response, "Location").strip()
    if not location:
        return None
    return urljoin(current_url, location)


def _read_limited(response: object, max_bytes: int, deadline: float) -> bytes:
    declared = _header(response, "Content-Length").strip()
    if declared:
        try:
            declared_size = int(declared)
        except ValueError:
            # Ignore malformed metadata and enforce the byte limit while reading.
            pass
        else:
            if declared_size > max_bytes:
                raise PublicUrlError("页面太大，已停止读取")

    read = getattr(response, "read", None)
    if not callable(read):
        raise PublicUrlError("网页响应无法读取")
    if time.monotonic() >= deadline:
        raise TimeoutError("read deadline exceeded")
    # A bounded read protects normal HTTP responses and the +1 sentinel catches
    # servers (or test doubles) that ignore the requested size.
    raw = read(max_bytes + 1)
    if time.monotonic() > deadline:
        raise TimeoutError("read deadline exceeded")
    if len(raw) > max_bytes:
        raise PublicUrlError("页面太大，已停止读取")
    return bytes(raw)


def _validate_destination(url: str, resolver: Callable[..., Iterable[object]] | None) -> str:
    normalized, error = normalize_public_url(url)
    if not normalized:
        raise PublicUrlError(error or "只支持公开网页地址（http/https）")
    parts = urlsplit(normalized)
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError as exc:
        raise PublicUrlError("地址端口无效") from exc
    resolve_public_host(parts.hostname or "", port, resolver=resolver)
    return normalized


def fetch_document(
    url: str,
    *,
    opener: Callable[..., object] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_bytes: int = MAX_RESPONSE_BYTES,
    resolver: Callable[..., Iterable[object]] | None = None,
    max_redirects: int = MAX_REDIRECTS,
    total_timeout: float = DEFAULT_TOTAL_TIMEOUT,
) -> SourceDocument:
    """Fetch one public HTML document, validating DNS on every redirect hop."""

    total_seconds = float(total_timeout)
    if total_seconds <= 0:
        return SourceDocument(url=url, status="error", error="抓取超时")
    if float(timeout) <= 0:
        return SourceDocument(url=url, status="error", error="抓取超时")
    deadline = time.monotonic() + total_seconds
    current_url = url
    redirects = 0
    try:
        while True:
            current_url = _validate_destination(current_url, resolver)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("request deadline exceeded")
            request = Request(
                current_url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            response = _safe_open_once(request, min(float(timeout), remaining), opener)
            try:
                target = _redirect_target(current_url, response)
                if target is not None:
                    redirects += 1
                    if redirects > max_redirects:
                        raise PublicUrlError("网页重定向次数过多，已停止读取")
                    # Validate the next destination at the top of the loop before
                    # any connection is attempted.
                    current_url = target
                    continue

                content_type = _header(response, "Content-Type")
                if content_type and "html" not in content_type.lower() and "xhtml" not in content_type.lower():
                    return SourceDocument(url=current_url, status="error", error="页面不是 HTML 内容")
                raw = _read_limited(response, max_bytes, deadline)
                html = raw.decode("utf-8", errors="replace")
                return extract_html(html, current_url, max_chars=MAX_TEXT_CHARS)
            finally:
                _close_response(response)
    except (TimeoutError, socket.timeout):
        return SourceDocument(url=url, status="error", error="抓取超时")
    except PublicUrlError as exc:
        return SourceDocument(url=url, status="error", error=str(exc))
    except HTTPError as exc:
        return SourceDocument(url=url, status="error", error=f"网页返回 HTTP {exc.code}")
    except URLError as exc:
        return SourceDocument(url=url, status="error", error=f"无法访问网页：{exc.reason}")
    except Exception as exc:
        return SourceDocument(url=url, status="error", error=f"抓取失败：{exc.__class__.__name__}")

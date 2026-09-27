"""URL validation for public-page research."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit

from collections.abc import Callable, Iterable


MAX_URLS = 5
_BLOCKED_HOST_NAMES = {"localhost", "localhost.localdomain", "host.docker.internal"}


class PublicUrlError(ValueError):
    """Raised when a URL cannot be used as a public fetch destination."""


@dataclass(frozen=True)
class UrlValidation:
    urls: tuple[str, ...]
    errors: tuple[str, ...]
    duplicates: tuple[str, ...]
    limit_exceeded: bool = False

    @property
    def valid(self) -> bool:
        return bool(self.urls) and not self.errors


def _is_private_or_local(hostname: str) -> bool:
    normalized = hostname.rstrip(".").lower()
    if normalized in _BLOCKED_HOST_NAMES or normalized.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_reserved,
            address.is_multicast,
            address.is_unspecified,
        )
    )


def _coerce_resolved_ip(record: object) -> str | None:
    """Extract the address component from common ``getaddrinfo`` records."""
    try:
        sockaddr = record[4]  # type: ignore[index]
        value = sockaddr[0]
    except (IndexError, KeyError, TypeError):
        return None
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def resolve_public_host(
    hostname: str,
    port: int | None = None,
    *,
    resolver: Callable[..., Iterable[object]] | None = None,
) -> tuple[str, ...]:
    """Resolve a host and fail closed if any result is not public.

    DNS is intentionally checked at fetch time (rather than only during form
    validation), so each redirect hop gets a fresh resolution check.  A
    resolver can be injected by tests; production uses ``socket.getaddrinfo``.
    """

    normalized = str(hostname or "").rstrip(".").lower()
    if not normalized:
        raise PublicUrlError("地址缺少主机名")
    if _is_private_or_local(normalized):
        raise PublicUrlError("不接受本地或内网地址")
    resolve = resolver or socket.getaddrinfo
    lookup_port = int(port or 443)
    try:
        try:
            records = resolve(normalized, lookup_port, type=socket.SOCK_STREAM)
        except TypeError:
            # Small injected resolvers often only accept host and port.
            records = resolve(normalized, lookup_port)
        addresses = tuple(
            address
            for address in (_coerce_resolved_ip(record) for record in records)
            if address
        )
    except (OSError, socket.gaierror) as exc:
        raise PublicUrlError("无法解析公开网页地址") from exc
    if not addresses:
        raise PublicUrlError("无法解析公开网页地址")
    blocked = next((address for address in addresses if _is_private_or_local(address)), None)
    if blocked:
        raise PublicUrlError("地址解析到内网、回环、链路本地或保留地址")
    return tuple(dict.fromkeys(addresses))


def normalize_public_url(raw: str) -> tuple[str | None, str | None]:
    """Normalize and syntactically validate one public URL.

    DNS is deliberately not performed here; callers that make a network
    request must call :func:`resolve_public_host` immediately before opening
    the connection.
    """

    return _normalize(raw)


def _normalize(raw: str) -> tuple[str | None, str | None]:
    value = str(raw or "").strip()
    if not value:
        return None, None
    try:
        parts: SplitResult = urlsplit(value)
    except ValueError:
        return None, "地址格式无法识别"
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return None, "只支持公开网页地址（http/https）"
    if _is_private_or_local(parts.hostname):
        return None, "不接受本地或内网地址，请换成公开网页"
    try:
        normalized_host = parts.hostname.lower()
        if parts.username or parts.password:
            return None, "地址不能包含登录凭据"
        port = parts.port
        if port is not None and not (0 < port <= 65535):
            return None, "端口号无效"
        # ``urlunsplit`` needs brackets around an IPv6 literal in netloc.
        netloc_host = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
        netloc = netloc_host
        if port is not None and not (
            (parts.scheme.lower() == "http" and port == 80)
            or (parts.scheme.lower() == "https" and port == 443)
        ):
            netloc = f"{netloc}:{port}"
        # Keep the parsed path/query but deliberately discard fragments.
        normalized = urlunsplit(
            (parts.scheme.lower(), netloc, parts.path or "/", parts.query, "")
        )
    except ValueError:
        return None, "地址端口无效"
    return normalized, None


def validate_urls(
    raw_lines: list[str] | tuple[str, ...],
    max_urls: int = MAX_URLS,
    *,
    resolver: Callable[..., Iterable[object]] | None = None,
) -> UrlValidation:
    urls: list[str] = []
    errors: list[str] = []
    duplicates: list[str] = []
    seen: set[str] = set()
    limit_exceeded = False

    for raw in raw_lines:
        normalized, error = _normalize(raw)
        if normalized is None:
            if error:
                errors.append(f"{str(raw).strip() or '空地址'}：{error}")
            continue
        if normalized in seen:
            duplicates.append(normalized)
            continue
        if resolver is not None:
            try:
                parts = urlsplit(normalized)
                resolve_public_host(
                    parts.hostname or "",
                    parts.port or (443 if parts.scheme == "https" else 80),
                    resolver=resolver,
                )
            except (PublicUrlError, ValueError) as exc:
                errors.append(f"{str(raw).strip() or '空地址'}：{exc}")
                continue
        if len(urls) >= max_urls:
            limit_exceeded = True
            errors.append(f"最多处理 {max_urls} 个公开网页地址，请先删减后再试")
            continue
        seen.add(normalized)
        urls.append(normalized)

    return UrlValidation(tuple(urls), tuple(errors), tuple(duplicates), limit_exceeded)

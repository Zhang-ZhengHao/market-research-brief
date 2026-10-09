"""Pure syntax normalization for user-supplied reference links."""

from __future__ import annotations

from urllib.parse import SplitResult, urlsplit, urlunsplit


def normalize_reference_link(raw: object) -> str:
    """Return normalized inert HTTP(S) metadata without resolving or fetching it."""
    value = str(raw or "").strip()
    if not value:
        return ""
    if any(character.isspace() for character in value):
        raise ValueError("参考链接格式无法识别。")
    try:
        parts: SplitResult = urlsplit(value)
    except ValueError as exc:
        raise ValueError("参考链接格式无法识别。") from exc

    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("参考链接只支持 http/https 地址。")
    if parts.username is not None or parts.password is not None:
        raise ValueError("参考链接不能包含登录凭据。")

    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError("参考链接端口无效。") from exc

    hostname = parts.hostname.lower()
    host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and not (
        (scheme == "http" and port == 80)
        or (scheme == "https" and port == 443)
    ):
        host = f"{host}:{port}"

    return urlunsplit((scheme, host, parts.path or "/", parts.query, ""))

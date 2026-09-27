import io
import json
import socket
import zipfile

import pytest

from services.demo_data import DEMO_DOCUMENTS
import services.export as export_service
from services.fetcher import fetch_document
from services.model_client import ModelClientError, OpenAICompatibleReportClient
from services.models import SourceDocument
from services.report import build_report
import services.demo_data as demo_data
from services.urls import validate_urls


class _Response:
    def __init__(self, body=b"", *, status=200, location="", content_type="text/html"):
        self.body = body
        self.status = status
        self.code = status
        self.headers = {"Content-Type": content_type}
        if location:
            self.headers["Location"] = location

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _resolver(mapping):
    def resolve(host, port, *args, **kwargs):
        value = mapping[host]
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (value, port))]

    return resolve


def test_fetch_rechecks_dns_before_following_redirect_to_private_address():
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)
        return _Response(status=302, location="https://redirect.test/private")

    document = fetch_document(
        "https://public.test/start",
        opener=opener,
        resolver=_resolver({"public.test": "93.184.216.34", "redirect.test": "127.0.0.1"}),
    )

    assert document.status == "error"
    assert "内网" in document.error or "回环" in document.error
    assert calls == ["https://public.test/start"]


def test_fetch_rejects_dns_resolving_to_link_local_or_reserved_address():
    for address in ("169.254.169.254", "240.0.0.1"):
        document = fetch_document(
            "https://public.test/metadata",
            opener=lambda *_args, **_kwargs: _Response(b"<p>should not read</p>"),
            resolver=_resolver({"public.test": address}),
        )
        assert document.status == "error"
        assert "地址" in document.error or "内网" in document.error


def test_fetch_rejects_response_declaring_more_than_maximum_bytes_before_reading():
    class DeclaredLarge(_Response):
        def __init__(self):
            super().__init__(b"<p>small body</p>")
            self.headers["Content-Length"] = "1001"

    reads = []

    class Tracked(DeclaredLarge):
        def read(self, size=-1):
            reads.append(size)
            return super().read(size)

    document = fetch_document(
        "https://public.test/large",
        opener=lambda *_args, **_kwargs: Tracked(),
        resolver=_resolver({"public.test": "93.184.216.34"}),
        max_bytes=1000,
    )

    assert document.status == "error"
    assert "太大" in document.error
    assert reads == []


def test_fetch_treats_response_header_names_case_insensitively():
    response = _Response(b"<p>small body</p>")
    response.headers = {"content-type": "text/html", "content-length": "1001"}

    document = fetch_document(
        "https://public.test/large",
        opener=lambda *_args, **_kwargs: response,
        resolver=_resolver({"public.test": "93.184.216.34"}),
        max_bytes=1000,
    )

    assert document.status == "error"
    assert "太大" in document.error


def test_fetch_keeps_injected_opener_seam_for_integrators():
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        return _Response("<html><body><p>公开正文</p></body></html>".encode())

    document = fetch_document(
        "https://public.test/seam",
        opener=fake_urlopen,
        resolver=_resolver({"public.test": "93.184.216.34"}),
    )

    assert document.status == "success"
    assert calls and calls[0][0] == "https://public.test/seam"


def test_validate_urls_can_apply_injected_dns_gate_before_fetch():
    result = validate_urls(
        ["https://public.test/a", "https://private.test/b"],
        resolver=_resolver({"public.test": "93.184.216.34", "private.test": "10.0.0.8"}),
    )

    assert result.urls == ("https://public.test/a",)
    assert any("内网" in error for error in result.errors)


def test_validate_urls_preserves_brackets_for_public_ipv6_literals():
    result = validate_urls(["https://[2001:4860:4860::8888]/dns-query#fragment"])

    assert result.urls == ("https://[2001:4860:4860::8888]/dns-query",)


def test_fetch_stops_after_redirect_limit_and_keeps_each_hop_public():
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)
        return _Response(status=302, location="https://public.test/next")

    document = fetch_document(
        "https://public.test/start",
        opener=opener,
        resolver=_resolver({"public.test": "93.184.216.34"}),
        max_redirects=2,
    )

    assert document.status == "error"
    assert "重定向" in document.error
    assert len(calls) == 3


def test_fetch_returns_timeout_when_total_deadline_is_already_exhausted():
    document = fetch_document(
        "https://public.test/slow",
        opener=lambda *_args, **_kwargs: _Response(b"<p>not read</p>"),
        resolver=_resolver({"public.test": "93.184.216.34"}),
        total_timeout=0,
    )

    assert document.status == "error"
    assert "超时" in document.error


def test_fetch_treats_non_positive_connection_timeout_as_timeout():
    called = False

    def opener(*_args, **_kwargs):
        nonlocal called
        called = True
        return _Response(b"<p>not read</p>")

    document = fetch_document(
        "https://public.test/slow",
        opener=opener,
        resolver=_resolver({"public.test": "93.184.216.34"}),
        timeout=0,
    )

    assert document.status == "error"
    assert "超时" in document.error
    assert called is False


def test_ai_client_is_offline_by_default_even_when_a_key_exists(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("INSIGHT_MONITOR_AI_ENABLED", raising=False)

    assert OpenAICompatibleReportClient.from_env() is None


def test_disabled_ai_client_never_calls_provider():
    called = False

    def fail_if_called(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("provider must not be called")

    client = OpenAICompatibleReportClient("test-key", enabled=False)
    client._urlopen = fail_if_called
    with pytest.raises(ModelClientError, match="未开启"):
        client.generate_report("主题", "竞品速览", [SourceDocument("", "资料", "正文")])
    assert called is False


def test_ai_client_enforces_source_and_character_limits():
    client = OpenAICompatibleReportClient("test-key", enabled=True)
    too_many = [SourceDocument("", str(index), "正文") for index in range(6)]
    with pytest.raises(ModelClientError, match="最多处理 5"):
        client.generate_report("主题", "竞品速览", too_many)

    too_long = [SourceDocument("", "资料", "x" * 40_001)]
    with pytest.raises(ModelClientError, match="字符"):
        client.generate_report("主题", "竞品速览", too_long)


def test_ai_client_from_env_requires_explicit_flag(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("INSIGHT_MONITOR_AI_ENABLED", "1")
    client = OpenAICompatibleReportClient.from_env()
    assert client is not None
    assert client.enabled is True


def test_ai_limit_fallback_exposes_a_safe_user_readable_limit_message():
    client = OpenAICompatibleReportClient("test-key", enabled=True)
    report = build_report(
        "主题",
        "竞品速览",
        [SourceDocument("", "资料", "x" * 40_001)],
        mode="真实 AI",
        model_client=client,
    )

    assert report.mode == "演示规则（AI失败回退）"
    assert any("40000" in warning for warning in report.warnings)


def test_research_templates_are_synthetic_and_cover_customer_angles():
    templates = getattr(demo_data, "RESEARCH_TEMPLATES", ())
    get_template = getattr(demo_data, "get_template", lambda _key: None)
    assert {template.key for template in templates} >= {
        "competitor_snapshot",
        "industry_weekly",
        "content_ideas",
    }
    assert {template.angle for template in templates} >= {
        "竞品速览",
        "行业周报",
        "内容选题",
    }
    for template in templates:
        assert template.documents
        assert all("合成" in document.text for document in template.documents)
    assert get_template("industry_weekly").angle == "行业周报"


def test_research_project_exports_include_metadata_and_report_files():
    report = build_report(
        "宠物用品竞品",
        "竞品速览",
        [SourceDocument("https://example.com/a", "示例", "合成正文。")],
    )

    payload = json.loads(
        export_service.report_to_project_json(report, template_key="competitor_snapshot")
    )
    markdown = export_service.report_to_project_markdown(report, template_key="competitor_snapshot")
    archive = export_service.research_project_to_zip(report, template_key="competitor_snapshot")

    assert payload["schema_version"] == "insight-monitor.research-project.v1"
    assert payload["project"]["template_key"] == "competitor_snapshot"
    assert payload["report"]["sources"][0]["url"] == "https://example.com/a"
    assert "研究项目元数据" in markdown
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        assert set(bundle.namelist()) == {"project.json", "report.md"}
        assert json.loads(bundle.read("project.json"))["schema_version"] == payload["schema_version"]


def test_research_project_zip_is_deterministic_for_same_report():
    report = build_report(
        "主题",
        "行业周报",
        [SourceDocument("https://example.com/a", "示例", "合成正文。")],
    )

    first = export_service.research_project_to_zip(report, template_key="industry_weekly")
    second = export_service.research_project_to_zip(report, template_key="industry_weekly")

    assert first == second

import io
import json
from pathlib import Path
import zipfile

import pytest

from services.demo_data import DEMO_DOCUMENTS
import services.export as export_service
from services.model_client import ModelClientError, OpenAICompatibleReportClient
from services.models import SourceDocument
from services.report import build_report
import services.demo_data as demo_data


def test_source_ingestion_tree_has_no_page_fetch_runtime():
    root = Path(__file__).parents[1]

    assert not (root / "services" / "fetcher.py").exists()
    assert not (root / "services" / "urls.py").exists()
    assert not (root / "services" / "extractor.py").exists()
    for path in [root / "app.py", *(root / "services").glob("*.py")]:
        if path.name == "model_client.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert "urllib.request" not in source
        assert "socket.getaddrinfo" not in source


def test_synthetic_demo_sources_do_not_offer_placeholder_external_links():
    template_documents = [
        document
        for template in demo_data.RESEARCH_TEMPLATES
        for document in template.documents
    ]

    assert all(document.url == "" for document in [*DEMO_DOCUMENTS, *template_documents])


def test_release_docs_match_the_paste_only_network_boundary():
    root = Path(__file__).parents[1]
    english = (root / "README.md").read_text(encoding="utf-8")
    chinese = (root / "README.zh-CN.md").read_text(encoding="utf-8")
    security = (root / "SECURITY.md").read_text(encoding="utf-8")
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8") if (root / "CHANGELOG.md").exists() else ""

    assert "Exactly two input modes" in english
    assert "仅提供两种资料模式" in chinese
    assert "不读取网页" in security
    assert "## [0.1.0] - 2026-10-09" in changelog
    for document in (english, chinese, security):
        assert "services/fetcher.py" not in document
        assert "ssrf-protection" not in document.lower()


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

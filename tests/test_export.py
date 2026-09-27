import json

from services.models import SourceDocument
from services.export import report_to_json, report_to_markdown
from services.report import build_report


def test_exports_are_readable_and_keep_citation_urls():
    report = build_report(
        "宠物用品竞品",
        "内容选题",
        [SourceDocument("https://example.com/a", "示例来源", "一段公开正文。")],
        mode="演示规则",
    )

    markdown = report_to_markdown(report)
    payload = json.loads(report_to_json(report))

    assert "宠物用品竞品" in markdown
    assert "https://example.com/a" in markdown
    assert payload["sources"][0]["url"] == "https://example.com/a"
    assert payload["angle"] == "内容选题"
    assert payload["sources"][0]["source_kind"] == "web"
    assert payload["sources"][0]["evidence"]
    assert "原文证据片段" in markdown
    assert payload["sources"][0]["evidence"] in markdown


def test_export_does_not_fake_a_link_for_pasted_source_and_keeps_special_text():
    report = build_report(
        "手工资料",
        "研究简报",
        [SourceDocument("", "<手工标题>", "第一行 <原文>。\n第二行。", source_kind="pasted")],
        mode="演示规则",
    )

    markdown = report_to_markdown(report)
    payload = json.loads(report_to_json(report))

    assert "未提供（手工粘贴资料）" in markdown
    assert "[打开来源]" not in markdown
    assert payload["sources"][0]["source_kind"] == "pasted"
    assert "第一行 <原文>。" in payload["sources"][0]["evidence"]

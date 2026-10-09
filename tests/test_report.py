from services.models import SourceDocument
from services.report import build_report


class _FailingModelClient:
    def generate_report(self, topic, angle, documents):
        raise RuntimeError("fake model outage")


def test_build_report_preserves_sources_and_separates_unavailable_material():
    documents = [
        SourceDocument(
            url="https://example.com/a",
            title="来源 A",
            text="来源 A 的第一句。来源 A 的第二句。",
            date_hint="2026-09-20",
        ),
        SourceDocument(
            url="https://example.com/b",
            title="来源 B",
            text="",
            status="error",
            error="资料不可用",
        ),
    ]

    report = build_report("竞品动态", "竞品速览", documents, mode="演示规则")

    assert report.topic == "竞品动态"
    assert len(report.sources) == 2
    assert report.sources[0].summary
    assert report.sources[1].status == "error"
    assert any("资料不可用" in warning for warning in report.warnings)
    assert report.executive_summary
    assert report.actions
    assert report.sources[0].evidence
    assert report.sources[0].evidence in documents[0].text
    assert report.sources[1].evidence == ""


def test_evidence_is_a_bounded_verbatim_excerpt_for_long_source_text():
    text = "第一句是可核对的原文。" + ("后续材料。" * 100)
    document = SourceDocument("https://example.com/long", "长来源", text)

    report = build_report("测试主题", "研究简报", [document])

    evidence = report.sources[0].evidence
    assert evidence
    assert len(evidence) <= 240
    assert evidence in text


def test_ai_failure_marks_report_as_rule_fallback_instead_of_real_ai():
    report = build_report(
        "测试主题",
        "研究简报",
        [SourceDocument("https://example.com/a", "来源 A", "原文内容。")],
        mode="真实 AI",
        model_client=_FailingModelClient(),
    )

    assert report.mode == "演示规则（AI失败回退）"
    assert any("已回退规则结果" in warning for warning in report.warnings)


def test_empty_report_only_guides_the_user_to_paste_source_text():
    report = build_report("测试主题", "研究简报", [])

    guidance = " ".join([*report.executive_summary, *report.actions])
    assert "粘贴" in guidance
    assert "公开地址" not in guidance

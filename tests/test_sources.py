import pytest

from services import sources
from services.sources import build_pasted_source


def test_build_pasted_source_normalizes_optional_metadata_without_faking_a_url():
    source = build_pasted_source(
        title="  手工资料标题  ",
        url="  ",
        text="  第一段正文。\n第二段正文。  ",
    )

    assert source.source_kind == "pasted"
    assert source.title == "手工资料标题"
    assert source.url == ""
    assert source.text == "第一段正文。\n第二段正文。"
    assert source.status == "success"


def test_build_pasted_source_rejects_blank_or_oversized_text():
    with pytest.raises(ValueError, match="正文"):
        build_pasted_source(title="资料", url="", text=" \n\t")

    with pytest.raises(ValueError, match="12000"):
        build_pasted_source(title="资料", url="", text="x" * 12_001)


def test_build_pasted_source_rejects_unsafe_links_and_normalizes_public_links():
    with pytest.raises(ValueError, match="http/https"):
        build_pasted_source(title="资料", url="javascript:alert(1)", text="正文")

    source = build_pasted_source(
        title="资料", url=" HTTPS://Example.COM/story#section ", text="正文"
    )
    assert source.url == "https://example.com/story"


def test_build_pasted_sources_preserves_order_and_source_metadata():
    result = sources.build_pasted_sources(
        [
            {"title": "资料 A", "url": "", "text": "第一份正文。"},
            {"title": "资料 B", "url": "https://example.com/b", "text": "第二份正文。"},
        ]
    )

    assert [source.title for source in result] == ["资料 A", "资料 B"]
    assert [source.source_kind for source in result] == ["pasted", "pasted"]
    assert result[1].url == "https://example.com/b"


def test_build_pasted_sources_reports_index_and_total_size_limits():
    with pytest.raises(ValueError, match="第 2 份资料"):
        sources.build_pasted_sources(
            [
                {"title": "资料 A", "url": "", "text": "有内容"},
                {"title": "资料 B", "url": "", "text": "   \n\t"},
            ]
        )

    with pytest.raises(ValueError, match="最多支持 40000"):
        sources.build_pasted_sources(
            [
                {"title": str(index), "url": "", "text": "x" * 10_000}
                for index in range(5)
            ]
        )

    accepted = sources.build_pasted_sources(
        [{"title": str(index), "url": "", "text": "x" * 10_000} for index in range(4)]
    )
    assert len(accepted) == 4

    with pytest.raises(ValueError, match="最多支持 40000"):
        sources.build_pasted_sources(
            [
                {"title": str(index), "url": "", "text": "x" * 10_000}
                for index in range(4)
            ]
            + [{"title": "额外", "url": "", "text": "x"}]
        )

    with pytest.raises(ValueError, match="最多支持 5 份"):
        sources.build_pasted_sources(
            [{"title": str(index), "url": "", "text": "内容"} for index in range(6)]
        )

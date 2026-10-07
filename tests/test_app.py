from pathlib import Path

from streamlit.testing.v1 import AppTest
from services.demo_data import DEMO_DOCUMENTS, DEMO_TOPIC


def test_product_title_matches_repository_manifest():
    root = Path(__file__).parents[1]
    app = AppTest.from_file(root / "app.py").run()

    assert not app.exception
    assert any(
        "Market Research Brief" in item.value and "(Insight Monitor)" in item.value
        for item in app.markdown
    )
    assert 'name = "Market Research Brief (Insight Monitor)"' in (
        root / "app.toml"
    ).read_text(encoding="utf-8")


def test_demo_entry_is_generic_and_not_football(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py").run()

    source_options = list(app.radio[0].options)
    assert "示例资料" in source_options
    assert "足球演示数据" not in source_options
    assert "宠物" in app.text_input[0].value
    assert all("足球" not in DEMO_TOPIC and "足球" not in document.text for document in DEMO_DOCUMENTS)


def test_generic_demo_entry_still_runs_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py").run()

    app.radio[0].set_value("示例资料").run()
    app.button[0].click().run()

    assert not app.exception
    assert any("已载入 3 个宠物用品竞品合成演示来源" in item.value for item in app.success)
    assert any("宠物" in item.value or "竞品" in item.value for item in app.markdown)


def test_demo_ai_checkbox_explains_missing_key_instead_of_silently_ignoring(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py").run()

    app.checkbox[0].set_value(True)
    app.button[0].click().run()

    assert not app.exception
    assert any("未检测到 OPENAI_API_KEY" in item.value for item in app.warning)


def test_pasted_source_count_renders_three_ordered_sources(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py").run()
    app.radio[0].set_value("粘贴正文").run()
    app.number_input[0].set_value(3).run()

    for widget in app.text_input:
        if widget.label == "资料标题（可选）":
            widget.set_value("资料 A")
        elif widget.label == "资料 2 标题（可选）":
            widget.set_value("资料 B")
        elif widget.label == "资料 3 标题（可选）":
            widget.set_value("资料 C")
    for widget in app.text_area:
        if widget.label == "资料正文（必填，最多 12,000 字符）":
            widget.set_value("A 原文。")
        elif widget.label == "资料 2 正文（必填，最多 12,000 字符）":
            widget.set_value("B 原文。")
        elif widget.label == "资料 3 正文（必填，最多 12,000 字符）":
            widget.set_value("C 原文。")
    app.button[0].click().run()

    assert not app.exception
    assert any("已载入 3 份" in item.value for item in app.success)
    assert any("按资料顺序对照，共 3 份" in item.label for item in app.expander)

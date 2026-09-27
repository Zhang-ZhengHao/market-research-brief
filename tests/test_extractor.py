from services.extractor import extract_html


def test_extract_html_returns_title_date_and_readable_body_without_scripts():
    html = """
    <html><head>
      <title>示例标题</title>
      <meta property="article:published_time" content="2026-09-20">
    </head><body>
      <nav>导航内容</nav>
      <main><h1>示例标题</h1><p>第一段正文。</p><p>第二段正文。</p></main>
      <script>不要把脚本内容放进正文</script>
    </body></html>
    """

    page = extract_html(html, "https://example.com/story")

    assert page.title == "示例标题"
    assert page.date_hint == "2026-09-20"
    assert "第一段正文" in page.text
    assert "第二段正文" in page.text
    assert "不要把脚本内容" not in page.text


def test_extract_html_limits_text_and_reports_empty_pages():
    long_text = "。".join(["长文本"] * 100)
    page = extract_html(
        f"<html><body><p>{long_text}</p></body></html>",
        "https://example.com",
        max_chars=120,
    )

    assert len(page.text) <= 120

    empty = extract_html("<html><body><script>only script</script></body></html>", "https://example.com/empty")
    assert empty.text == ""


def test_extract_html_falls_back_to_visible_body_divs():
    page = extract_html(
        "<html><body><div>正文放在普通 div 里。</div><div>第二段。</div></body></html>",
        "https://example.com/div",
    )

    assert "正文放在普通 div 里" in page.text
    assert "第二段" in page.text

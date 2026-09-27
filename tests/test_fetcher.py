from services.fetcher import fetch_document


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "text/html; charset=utf-8"):
        self.body = body
        self.headers = {"Content-Type": content_type}

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_fetch_document_extracts_successful_html_with_injected_opener():
    html = "<html><head><title>远程页面</title></head><body><p>公开正文</p></body></html>".encode()

    def opener(request, timeout):
        assert request.full_url == "https://example.com/story"
        assert timeout > 0
        return FakeResponse(html)

    document = fetch_document("https://example.com/story", opener=opener)

    assert document.status == "success"
    assert document.title == "远程页面"
    assert document.text == "公开正文"


def test_fetch_document_keeps_failure_as_data_instead_of_raising():
    def opener(request, timeout):
        raise TimeoutError("timed out")

    document = fetch_document("https://example.com/slow", opener=opener)

    assert document.status == "error"
    assert "超时" in document.error
    assert document.text == ""

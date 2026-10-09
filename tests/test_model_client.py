import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from services.model_client import OpenAICompatibleReportClient
from services.models import SourceDocument
from services.report import build_report


def test_model_prompt_sends_title_and_text_but_not_inert_reference_link():
    document = SourceDocument(
        url="https://reference.example/private-token?value=secret",
        title="用户资料",
        text="允许发送给已配置模型的正文。",
        source_kind="pasted",
    )

    prompt = OpenAICompatibleReportClient._prompt("测试主题", "研究简报", [document])

    assert "用户资料" in prompt
    assert "允许发送给已配置模型的正文" in prompt
    assert document.url not in prompt


def test_ai_report_uses_local_source_evidence_instead_of_model_supplied_quote():
    document = SourceDocument(
        url="",
        title="手工资料",
        text="原文里的可核对句子。",
        source_kind="pasted",
    )
    report = OpenAICompatibleReportClient._to_report(
        "测试主题",
        "研究简报",
        [document],
        {
            "executive_summary": ["模型摘要"],
            "sources": [
                {
                    "source_index": 0,
                    "summary": "模型摘要里的来源概括",
                    "evidence": "模型编造的并不存在的证据",
                }
            ],
        },
    )

    assert report.sources[0].source_kind == "pasted"
    assert report.sources[0].summary == "模型摘要里的来源概括"
    assert report.sources[0].evidence == "原文里的可核对句子。"


def test_duplicate_or_out_of_range_source_indexes_do_not_silently_choose_a_summary():
    documents = [
        SourceDocument("https://example.com/a", "来源 A", "A 原文。"),
        SourceDocument("https://example.com/b", "来源 B", "B 原文。"),
    ]
    report = OpenAICompatibleReportClient._to_report(
        "测试主题",
        "研究简报",
        documents,
        {
            "sources": [
                {"source_index": 0, "summary": "第一份冲突摘要"},
                {"source_index": 0, "summary": "第二份冲突摘要"},
                {"source_index": 9, "summary": "越界摘要"},
            ]
        },
    )

    assert report.sources[0].summary == "A 原文。"
    assert any("模型返回的来源索引存在重复、缺失或越界" in warning for warning in report.warnings)


def test_missing_successful_source_index_is_visible_and_falls_back_to_local_evidence():
    documents = [
        SourceDocument("https://example.com/a", "来源 A", "A 原文。"),
        SourceDocument("https://example.com/b", "来源 B", "B 原文。"),
    ]
    report = OpenAICompatibleReportClient._to_report(
        "测试主题",
        "研究简报",
        documents,
        {"sources": [{"source_index": 0, "summary": "A 摘要"}]},
    )

    assert report.sources[1].summary == "B 原文。"
    assert any("模型返回的来源索引存在重复、缺失或越界" in warning for warning in report.warnings)


class _FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _size=-1):
        return self.body


def test_fake_openai_endpoint_accepts_fenced_json_and_string_source_indexes(monkeypatch):
    content = "```json\n" + json.dumps(
        {
            "executive_summary": ["接口摘要"],
            "sources": [{"source_index": "0", "summary": "来源摘要"}],
        },
        ensure_ascii=False,
    ) + "\n```"
    response_body = json.dumps({"choices": [{"message": {"content": content}}]}, ensure_ascii=False).encode()
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return _FakeResponse(response_body)

    monkeypatch.setattr("services.model_client.urlopen", fake_urlopen)
    client = OpenAICompatibleReportClient(
        api_key="test-key", base_url="https://fake.example/v1", model="fake-model"
    )
    report = client.generate_report(
        "测试主题",
        "研究简报",
        [SourceDocument("https://example.com/a", "来源 A", "原文证据。")],
    )

    assert report.mode == "真实 AI"
    assert report.executive_summary == ["接口摘要"]
    assert report.sources[0].summary == "来源摘要"
    assert report.sources[0].evidence == "原文证据。"
    assert requests[0][0].full_url == "https://fake.example/v1/chat/completions"
    assert requests[0][0].headers["Authorization"] == "Bearer test-key"


def test_ai_response_cannot_invent_a_summary_for_a_failed_source():
    documents = [
        SourceDocument("https://example.com/a", "来源 A", "成功正文。"),
        SourceDocument("https://example.com/b", "来源 B", "", status="error", error="资料不可用"),
    ]
    report = OpenAICompatibleReportClient._to_report(
        "测试主题",
        "研究简报",
        documents,
        {
            "sources": [
                {"source_index": 0, "summary": "真实摘要"},
                {"source_index": 1, "summary": "模型编造摘要"},
            ]
        },
    )

    assert report.sources[0].summary == "真实摘要"
    assert report.sources[1].summary == ""
    assert report.sources[1].error == "资料不可用"


@contextmanager
def _local_model_server(response_body: bytes):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - stdlib handler hook
            length = int(self.headers.get("Content-Length", "0"))
            requests.append(
                {
                    "path": self.path,
                    "authorization": self.headers.get("Authorization"),
                    "payload": json.loads(self.rfile.read(length)),
                }
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response_body)

        def log_message(self, _format, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_openai_compatible_server_keeps_source_indexes_and_excludes_failed_text():
    content = json.dumps(
        {
            "executive_summary": ["三源摘要"],
            "sources": [
                {"source_index": 0, "summary": "A 摘要"},
                {"source_index": 2, "summary": "C 摘要"},
            ],
        },
        ensure_ascii=False,
    )
    body = json.dumps({"choices": [{"message": {"content": content}}]}, ensure_ascii=False).encode()
    documents = [
        SourceDocument("https://example.com/a", "来源 A", "A 的私有测试正文。"),
        SourceDocument("https://example.com/b", "来源 B", "B 不应发送。", status="error", error="资料不可用"),
        SourceDocument("https://example.com/c", "来源 C", "C 的私有测试正文。"),
    ]

    with _local_model_server(body) as (base_url, requests):
        report = OpenAICompatibleReportClient(
            api_key="local-key", base_url=base_url, model="local-model"
        ).generate_report("测试主题", "研究简报", documents)

    assert report.executive_summary == ["三源摘要"]
    assert report.sources[0].summary == "A 摘要"
    assert report.sources[1].summary == ""
    assert report.sources[1].error == "资料不可用"
    assert report.sources[2].summary == "C 摘要"
    assert len(requests) == 1
    assert requests[0]["path"] == "/v1/chat/completions"
    assert requests[0]["authorization"] == "Bearer local-key"
    prompt = requests[0]["payload"]["messages"][1]["content"]
    assert "A 的私有测试正文" in prompt
    assert "C 的私有测试正文" in prompt
    assert "B 不应发送" not in prompt


def test_timeout_from_real_client_marks_build_report_as_rule_fallback(monkeypatch):
    def timeout(*_args, **_kwargs):
        raise TimeoutError("fake timeout")

    monkeypatch.setattr("services.model_client.urlopen", timeout)
    report = build_report(
        "测试主题",
        "研究简报",
        [SourceDocument("https://example.com/a", "来源 A", "原文证据。")],
        mode="真实 AI",
        model_client=OpenAICompatibleReportClient("key", base_url="https://fake.example/v1"),
    )

    assert report.mode == "演示规则（AI失败回退）"
    assert report.sources[0].evidence == "原文证据。"
    assert any("真实 AI 汇总失败" in warning for warning in report.warnings)

"""Export report objects for customers and demos."""

from __future__ import annotations

import json
import io
import zipfile

from .models import Report
from .report import report_to_dict


PROJECT_SCHEMA_VERSION = "insight-monitor.research-project.v1"
PROJECT_DISCLAIMER = (
    "研究项目是基于用户提供资料的辅助整理，不是事实核验或经营效果保证；"
    "发布或据此决策前请人工打开来源原文复核。"
)


def report_to_json(report: Report) -> str:
    return json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)


def report_to_markdown(report: Report) -> str:
    lines = [
        f"# {report.topic}",
        "",
        f"- 报告角度：{report.angle}",
        f"- 生成模式：{report.mode}",
        f"- 生成时间：{report.generated_at}",
        "",
        "## 执行摘要",
        "",
    ]
    lines.extend(f"- {item}" for item in report.executive_summary)
    for title, items in (
        ("共同点", report.common_points),
        ("差异与注意事项", report.differences),
        ("值得关注的变化", report.changes),
        ("行动/选题建议", report.actions),
    ):
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {item}" for item in items or ["暂无结果"])

    lines.extend(["", "## 来源明细", ""])
    for index, source in enumerate(report.sources, start=1):
        status = "已载入" if source.status == "success" else "不可用"
        source_kind = {"pasted": "用户粘贴", "demo": "合成示例"}.get(
            source.source_kind, source.source_kind
        )
        link_line = (
            f"- 参考链接（用户提供，应用未抓取或验证）：{source.url}"
            if source.url
            else "- 参考链接：未提供（手工粘贴资料）"
        )
        evidence = " ".join((source.evidence or "").splitlines())
        lines.extend(
            [
                f"### {index}. {source.title}（{status} · {source_kind}）",
                "",
                link_line,
                f"- 日期线索：{source.date_hint or '未提取到'}",
                f"- 摘要：{source.summary or source.error or '无'}",
                f"- 原文证据片段：{evidence or '暂无可用证据'}",
                "",
            ]
        )
    if report.warnings:
        lines.extend(["## 使用提醒", ""])
        lines.extend(f"- {warning}" for warning in report.warnings)
    return "\n".join(lines).rstrip() + "\n"


def research_project_payload(report: Report, *, template_key: str = "") -> dict:
    """Return a portable, session-only research project representation."""

    return {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "project": {
            "title": report.topic,
            "template_key": str(template_key or ""),
            "angle": report.angle,
            "generated_at": report.generated_at,
            "source_count": len(report.sources),
        },
        "report": report_to_dict(report),
        "disclaimer": PROJECT_DISCLAIMER,
    }


def report_to_project_json(report: Report, *, template_key: str = "") -> str:
    return json.dumps(
        research_project_payload(report, template_key=template_key),
        ensure_ascii=False,
        indent=2,
    )


def report_to_project_markdown(report: Report, *, template_key: str = "") -> str:
    payload = research_project_payload(report, template_key=template_key)
    metadata = [
        "# 研究项目元数据",
        "",
        f"- Schema：{payload['schema_version']}",
        f"- 项目标题：{payload['project']['title']}",
        f"- 模板：{payload['project']['template_key'] or '未指定'}",
        f"- 报告角度：{payload['project']['angle']}",
        f"- 生成时间：{payload['project']['generated_at']}",
        f"- 来源数量：{payload['project']['source_count']}",
        "",
        payload["disclaimer"],
        "",
        "---",
        "",
    ]
    return "\n".join(metadata) + report_to_markdown(report)


def research_project_to_zip(report: Report, *, template_key: str = "") -> bytes:
    """Build a deterministic download bundle without server-side persistence."""

    project_json = report_to_project_json(report, template_key=template_key).encode("utf-8")
    report_markdown = report_to_project_markdown(report, template_key=template_key).encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in (
            ("project.json", project_json),
            ("report.md", report_markdown),
        ):
            info = zipfile.ZipInfo(filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, content)
    return output.getvalue()

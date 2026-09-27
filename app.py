from __future__ import annotations

import html
import os

import streamlit as st

from services.demo_data import DEMO_DOCUMENTS, DEMO_TOPIC, RESEARCH_TEMPLATES
from services.export import (
    report_to_json,
    report_to_markdown,
    research_project_to_zip,
)
from services.fetcher import fetch_document
from services.model_client import AI_FEATURE_FLAG, OpenAICompatibleReportClient, env_flag
from services.report import build_report
from services.sources import build_pasted_sources
from services.urls import validate_urls
from services.version import BUILD_SHA


ANGLE_OPTIONS = ("竞品速览", "研究简报", "内容选题")
SOURCE_MODE_OPTIONS = ("示例资料", "公开网页", "粘贴正文")
TEMPLATE_OPTIONS = tuple(RESEARCH_TEMPLATES)


def _render_footer() -> None:
    st.divider()
    st.caption(f"版本 {BUILD_SHA} · 当前结果只保存在本次页面会话")


def _render_source(source) -> None:
    if source.status != "success":
        status = "未读取"
    else:
        status = "已载入" if source.source_kind == "pasted" else "已读取"
    source_kind = {"pasted": "用户粘贴", "demo": "演示资料", "web": "公开网页"}.get(
        source.source_kind, source.source_kind
    )
    safe_title = html.escape(source.title or "未命名页面")
    st.markdown(f"**{safe_title}**　`{status} · {source_kind}`", unsafe_allow_html=True)
    if source.url:
        if source.source_kind == "pasted":
            st.caption("链接仅供回看，本次正文来自用户粘贴")
        st.markdown(f"[打开来源]({html.escape(source.url, quote=True)})")
    elif source.source_kind == "pasted":
        st.caption("未提供外部链接（用户粘贴资料）")
    else:
        st.caption("未提供外部链接")
    if source.date_hint:
        st.caption(f"日期线索：{source.date_hint}")
    if source.summary:
        st.write(source.summary)
    if source.evidence:
        evidence_html = html.escape(source.evidence).replace("\n", "<br>")
        st.markdown(f"**原文证据片段**<blockquote>{evidence_html}</blockquote>", unsafe_allow_html=True)
    else:
        st.caption("暂无可用证据")
    if source.error:
        st.warning(source.error)


def _render_report(report, *, template_key: str = "") -> None:
    st.divider()
    st.subheader("研究报告")
    st.caption(f"{report.angle} · {report.mode} · 生成于 {report.generated_at}")

    for warning in report.warnings:
        st.warning(warning)

    sections = (
        ("执行摘要", report.executive_summary),
        ("共同点", report.common_points),
        ("差异与注意事项", report.differences),
        ("值得关注的变化", report.changes),
        ("行动 / 选题建议", report.actions),
    )
    for heading, items in sections:
        st.markdown(f"#### {heading}")
        if items:
            for item in items:
                st.markdown(f"- {item}")
        else:
            st.caption("暂无内容")

    source_heading = (
        f"来源明细（按资料顺序对照，共 {len(report.sources)} 份）"
        if len(report.sources) > 1
        else f"来源明细（{len(report.sources)}）"
    )
    with st.expander(source_heading, expanded=True):
        for source in report.sources:
            _render_source(source)
            st.divider()

    stem = "insight-monitor-report"
    left, middle, right = st.columns(3)
    with left:
        st.download_button(
            "下载 Markdown",
            data=report_to_markdown(report),
            file_name=f"{stem}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with middle:
        st.download_button(
            "下载 JSON",
            data=report_to_json(report),
            file_name=f"{stem}.json",
            mime="application/json",
            use_container_width=True,
        )
    with right:
        st.download_button(
            "下载研究项目包",
            data=research_project_to_zip(report, template_key=template_key),
            file_name="insight-monitor-research-project.zip",
            mime="application/zip",
            use_container_width=True,
        )


st.set_page_config(
    page_title="Insight Monitor",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
      --ink: #18222d; --muted: #617181; --border: #dbe2e8;
      --surface: #ffffff; --surface-muted: #f5f7f9; --accent: #245b75;
    }
    .block-container { max-width: 1080px; padding-top: 2.2rem; padding-bottom: 3rem; }
    .hero { border: 1px solid var(--border); border-radius: 16px; padding: 1.25rem 1.35rem;
            background: var(--surface-muted); margin-bottom: 1.1rem; }
    .hero h1 { color: var(--ink); letter-spacing: -0.04em; margin-bottom: .35rem; }
    .hero p { color: var(--muted); margin: 0; font-size: 1.02rem; }
    [data-testid="stFormSubmitButton"] button {
      background: var(--accent) !important; border-color: var(--accent) !important;
      color: #fff !important;
    }
    [data-testid="stFormSubmitButton"] button:hover { filter: brightness(.92); }
    [data-testid="stDownloadButton"] button { width: 100%; }
    @media (max-width: 700px) {
      .block-container { padding: 1rem .8rem 2rem; }
      .hero { padding: 1rem; }
      button[data-testid^="stBaseButton-"], [data-testid="stDownloadButton"] button {
        min-height: 44px !important; height: 44px !important;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <section class="hero">
      <h1>Insight Monitor</h1>
      <p>把几个公开来源整理成一份带出处的研究简报。适合竞品速览、行业调研和内容选题。</p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.info(
    "产品只处理你提供的公开网页或粘贴正文，不登录、不绕过付费墙，也不自动搜索全网。"
    "真实 AI 模式会把提取到的正文发送到你配置的模型服务。"
)

template = st.selectbox(
    "研究模板",
    TEMPLATE_OPTIONS,
    index=0,
    format_func=lambda item: item.label,
    help="模板只提供合成资料和报告角度，适合五分钟客户演示。",
)
source_mode = st.radio("资料来源", SOURCE_MODE_OPTIONS, horizontal=True)
pasted_source_count = 1
if source_mode == "粘贴正文":
    pasted_source_count = int(
        st.number_input(
            "资料份数（1–5）",
            min_value=1,
            max_value=5,
            value=1,
            step=1,
            help="每份资料会单独展示标题、摘要、证据片段和来源链接。",
        )
    )

with st.form("research_form"):
    topic = st.text_input("研究主题 / 关键词", value=template.topic or DEMO_TOPIC)
    angle = st.selectbox(
        "报告角度",
        ANGLE_OPTIONS,
        index=ANGLE_OPTIONS.index(template.angle) if template.angle in ANGLE_OPTIONS else 0,
    )
    urls_text = ""
    pasted_entries = []
    if source_mode == "公开网页":
        urls_text = st.text_area(
            "公开网页地址（每行一个，最多 5 个）",
            placeholder="https://example.com/article-1\nhttps://example.com/article-2",
            height=130,
        )
    elif source_mode == "粘贴正文":
        st.caption(
            "网页无法直接读取时，可把 1–5 份正文粘贴到这里；每份最多 12,000 字符，合计最多 40,000 字符，资料会按顺序单独对照。"
        )
        for index in range(pasted_source_count):
            with st.expander(f"资料 {index + 1}", expanded=index == 0):
                title_label = "资料标题（可选）" if index == 0 else f"资料 {index + 1} 标题（可选）"
                url_label = "来源链接（可选）" if index == 0 else f"资料 {index + 1} 来源链接（可选）"
                text_label = (
                    "资料正文（必填，最多 12,000 字符）"
                    if index == 0
                    else f"资料 {index + 1} 正文（必填，最多 12,000 字符）"
                )
                pasted_entries.append(
                    {
                        "title": st.text_input(
                            title_label,
                            placeholder="例如：行业周报第 12 期",
                            key=f"pasted_title_{index}",
                        ),
                        "url": st.text_input(
                            url_label,
                            placeholder="https://example.com/article",
                            key=f"pasted_url_{index}",
                        ),
                        "text": st.text_area(
                            text_label,
                            placeholder="把文章正文粘贴到这里…",
                            height=220,
                            key=f"pasted_text_{index}",
                        ),
                    }
                )
    ai_server_enabled = env_flag(AI_FEATURE_FLAG)
    ai_mode = st.checkbox(
        "使用真实 AI 汇总（需显式开启并配置 OPENAI_API_KEY）",
        value=False,
        help="默认离线规则模式。开启后会把成功来源正文发送到你配置的模型服务，可能产生费用；"
        "每次最多 5 份资料、合计 40,000 字符。",
    )
    if ai_server_enabled:
        st.caption("真实 AI 已由部署者显式开启：每次最多 5 份资料、合计 40,000 字符；请先确认模型费用与数据留存政策。")
    submitted = st.form_submit_button("生成研究报告", type="primary", use_container_width=True)

if submitted:
    st.session_state.pop("report", None)
    if not topic.strip():
        st.error("请先填写研究主题。")
        st.stop()

    if source_mode == "示例资料":
        documents = list(template.documents)
        mode = (
            "真实 AI"
            if ai_mode
            and ai_server_enabled
            and os.getenv("OPENAI_API_KEY", "").strip()
            else "演示规则"
        )
        if template.key == "competitor_snapshot":
            st.success("已载入 3 个宠物用品竞品合成演示来源；这些内容不代表实时事实。")
        else:
            st.success(f"已载入 {len(documents)} 个{template.label}合成演示来源；这些内容不代表实时事实。")
        if ai_mode and not os.getenv("OPENAI_API_KEY", "").strip():
            st.warning("未检测到 OPENAI_API_KEY，已使用演示规则生成报告。")
        elif ai_mode and not ai_server_enabled:
            st.warning(f"真实 AI 功能未开启（请由部署者设置 {AI_FEATURE_FLAG}=1），已使用演示规则生成报告。")
    elif source_mode == "公开网页":
        validation = validate_urls(urls_text.splitlines())
        for duplicate in validation.duplicates:
            st.info(f"已合并重复地址：{duplicate}")
        for error in validation.errors:
            st.error(error)
        if validation.limit_exceeded:
            st.warning("本次没有提交任何地址；请删减到 5 个以内后再生成报告。")
            st.stop()
        if not validation.urls:
            st.warning("请至少提供一个有效的公开网页地址。")
            st.stop()
        documents = []
        progress = st.progress(0, text="正在读取公开网页…")
        for index, url in enumerate(validation.urls, start=1):
            documents.append(fetch_document(url))
            progress.progress(index / len(validation.urls), text=f"已处理 {index}/{len(validation.urls)} 个来源")
        mode = (
            "真实 AI"
            if ai_mode
            and ai_server_enabled
            and os.getenv("OPENAI_API_KEY", "").strip()
            else "演示规则"
        )
        if ai_mode and not os.getenv("OPENAI_API_KEY", "").strip():
            st.warning("未检测到 OPENAI_API_KEY，已使用演示规则生成报告。")
        elif ai_mode and not ai_server_enabled:
            st.warning(f"真实 AI 功能未开启（请由部署者设置 {AI_FEATURE_FLAG}=1），已使用演示规则生成报告。")
    else:
        try:
            documents = build_pasted_sources(pasted_entries)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        mode = (
            "真实 AI"
            if ai_mode
            and ai_server_enabled
            and os.getenv("OPENAI_API_KEY", "").strip()
            else "演示规则"
        )
        st.success(f"已载入 {len(documents)} 份手工粘贴资料；本次会话不会发起网页抓取。")
        if ai_mode and not os.getenv("OPENAI_API_KEY", "").strip():
            st.warning("未检测到 OPENAI_API_KEY，已使用演示规则生成报告。")
        elif ai_mode and not ai_server_enabled:
            st.warning(f"真实 AI 功能未开启（请由部署者设置 {AI_FEATURE_FLAG}=1），已使用演示规则生成报告。")

    client = OpenAICompatibleReportClient.from_env(enabled=True) if mode == "真实 AI" else None
    report = build_report(topic, angle, documents, mode=mode, model_client=client)
    st.session_state["report"] = report
    st.session_state["report_template_key"] = template.key

report = st.session_state.get("report")
if report is not None:
    _render_report(report, template_key=st.session_state.get("report_template_key", ""))

_render_footer()

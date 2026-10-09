"""Synthetic research templates used by the customer-facing demo."""

from __future__ import annotations

from dataclasses import dataclass

from .models import SourceDocument


@dataclass(frozen=True)
class ResearchTemplate:
    key: str
    label: str
    angle: str
    topic: str
    documents: tuple[SourceDocument, ...]


def _source(title: str, text: str, date_hint: str) -> SourceDocument:
    return SourceDocument(
        url="",
        title=title,
        text=text,
        date_hint=date_hint,
        source_kind="demo",
    )


RESEARCH_TEMPLATES: tuple[ResearchTemplate, ...] = (
    ResearchTemplate(
        key="competitor_snapshot",
        label="竞品速览｜宠物用品示例",
        angle="竞品速览",
        topic="宠物用品竞品变化",
        documents=(
            _source(
                "合成来源 A｜宠物用品品牌动态",
                "这是一条用于演示的合成资料，不代表实时事实。示例品牌近期推出低尘猫砂和小包装试用装，"
                "并把除臭效果、便携储存和新手入门作为主要卖点。",
                "2026-09-18",
            ),
            _source(
                "合成来源 B｜宠物用品市场观察",
                "这是一条用于演示的合成资料，不代表实时事实。示例观察到组合装、定期购和快速配送成为常见促销方式，"
                "但不同店铺在赠品和售后承诺上差异较大。",
                "2026-09-17",
            ),
            _source(
                "合成来源 C｜宠物用品用户反馈",
                "这是一条用于演示的合成资料，不代表实时事实。示例用户更关注产品是否容易清理、成分是否说得明白，"
                "以及出现破损或不适用时能否快速处理。",
                "2026-09-15",
            ),
        ),
    ),
    ResearchTemplate(
        key="industry_weekly",
        label="行业周报｜本地咖啡门店示例",
        angle="行业周报",
        topic="本地咖啡门店行业动态",
        documents=(
            _source(
                "合成来源 A｜咖啡门店菜单观察",
                "这是一条用于演示的合成资料，不代表实时事实。示例门店把季节限定、低糖选项和外带套餐作为本周重点。",
                "2026-09-22",
            ),
            _source(
                "合成来源 B｜咖啡门店社区活动",
                "这是一条用于演示的合成资料，不代表实时事实。示例活动围绕办公区早餐、会员积分和周末手作课程展开。",
                "2026-09-21",
            ),
            _source(
                "合成来源 C｜咖啡消费者反馈",
                "这是一条用于演示的合成资料，不代表实时事实。示例反馈集中在等待时间、座位舒适度和菜单标注清晰度。",
                "2026-09-20",
            ),
        ),
    ),
    ResearchTemplate(
        key="content_ideas",
        label="内容选题｜轻食品牌示例",
        angle="内容选题",
        topic="轻食品牌内容方向",
        documents=(
            _source(
                "合成来源 A｜轻食菜单趋势",
                "这是一条用于演示的合成资料，不代表实时事实。示例菜单强调蛋白质搭配、可替换配菜和透明营养说明。",
                "2026-09-19",
            ),
            _source(
                "合成来源 B｜轻食品牌故事",
                "这是一条用于演示的合成资料，不代表实时事实。示例品牌用备餐流程、食材产地和用户日常场景讲述产品价值。",
                "2026-09-18",
            ),
            _source(
                "合成来源 C｜轻食用户反馈",
                "这是一条用于演示的合成资料，不代表实时事实。示例用户期待口味稳定、分量说明清楚，并能灵活调整忌口。",
                "2026-09-17",
            ),
        ),
    ),
)


def get_template(key: str) -> ResearchTemplate:
    for template in RESEARCH_TEMPLATES:
        if template.key == key:
            return template
    raise KeyError(f"unknown research template: {key}")

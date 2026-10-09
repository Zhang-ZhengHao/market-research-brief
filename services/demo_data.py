"""Clearly-labelled synthetic sources for a no-key product demo."""

from __future__ import annotations

from .models import SourceDocument
from .templates import RESEARCH_TEMPLATES, ResearchTemplate, get_template


DEMO_TOPIC = "宠物用品竞品变化"

DEMO_DOCUMENTS = [
    SourceDocument(
        url="",
        title="演示来源 A｜宠物用品品牌动态（示例资料）",
        date_hint="2026-09-18",
        text=(
            "这是一条用于演示的合成资料，不代表实时事实。示例资料提到品牌近期推出低尘猫砂和小包装试用装，"
            "并把除臭效果、便携储存和新手入门作为主要卖点。"
        ),
        source_kind="demo",
    ),
    SourceDocument(
        url="",
        title="演示来源 B｜宠物用品市场观察（示例资料）",
        date_hint="2026-09-17",
        text=(
            "这是一条用于演示的合成资料，不代表实时事实。示例资料观察到，组合装、定期购和快速配送成为宠物用品店的常见促销方式，"
            "但不同店铺在赠品和售后承诺上差异较大。"
        ),
        source_kind="demo",
    ),
    SourceDocument(
        url="",
        title="演示来源 C｜宠物用品用户反馈专题（示例资料）",
        date_hint="2026-09-15",
        text=(
            "这是一条用于演示的合成资料，不代表实时事实。示例资料认为，用户更关注产品是否容易清理、成分是否说得明白，"
            "以及出现破损或不适用时能否快速处理。"
        ),
        source_kind="demo",
    ),
]

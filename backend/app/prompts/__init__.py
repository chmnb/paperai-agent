"""Prompt 工程模块 — 集中管理所有 LLM 提示词模板

设计原则：
1. 函数封装（非裸字符串）— 可单测、IDE 有提示
2. Few-shot 示例与逻辑分离 — 示例是数据，逻辑是代码
3. 模块级 VERSION — 便于 A/B 测试与回溯
"""
from app.prompts.parser import (
    metadata_extraction_prompt,
    section_parsing_prompt,
)
from app.prompts.qa import (
    intent_recognition_prompt,
    planning_prompt,
    critic_review_prompt,
    answer_generation_prompt,
    INTENT_STYLE_PROMPTS,
)
from app.prompts.fallbacks import NO_INFO_FALLBACK

__all__ = [
    "metadata_extraction_prompt",
    "section_parsing_prompt",
    "intent_recognition_prompt",
    "planning_prompt",
    "critic_review_prompt",
    "answer_generation_prompt",
    "INTENT_STYLE_PROMPTS",
    "NO_INFO_FALLBACK",
]

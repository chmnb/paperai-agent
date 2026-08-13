"""问答 Agent 的 Prompt 模板 — 集中管理，函数化封装

设计：
- Few-shot 示例放在 _INTENT_EXAMPLES 数据结构里，与 prompt 逻辑分离
- 每个函数可独立单元测试
- VERSION 用于 A/B 测试回溯
"""
from typing import Dict, List

VERSION = "2.0"

# ── Few-shot 示例数据（与逻辑分离，可独立调整）─────────────────────
_INTENT_EXAMPLES = [
    ("这篇论文的作者是谁？", "general", "simple"),
    ("什么是注意力机制？", "concept", "simple"),
    ("论文使用的主要方法是什么？", "method", "complex"),
    ("这篇论文的主要贡献是什么？", "general", "complex"),
    ("实验结果如何？", "experiment", "complex"),
    ("论文的局限性有哪些？", "general", "complex"),
    ("方法和对比实验有什么关系？", "method", "complex"),
]

# 意图 → 回答风格映射
INTENT_STYLE_PROMPTS: Dict[str, str] = {
    "concept": "请给出清晰、准确的概念解释。",
    "method": "请详细分析论文使用的方法，并解释其原理。",
    "experiment": "请分析实验结果并给出专业评价。",
    "code": "请给出简洁、可运行的实现代码。",
    "general": "请给出准确、全面的回答。",
}


def intent_recognition_prompt(question: str) -> str:
    """意图识别 + 复杂度路由（决定走快速路径还是 Agent Loop）"""
    examples = "\n".join(
        f'"{q}" → {{"intent": "{i}", "complexity": "{c}"}}'
        for q, i, c in _INTENT_EXAMPLES
    )
    return f"""分析以下关于论文的问题，判断其意图类型和复杂度。

意图类型：concept / method / experiment / code / general
复杂度规则：
- simple：仅靠一次检索就能完整回答的简单问题（如"论文作者是谁"、"标题是什么"、"某个术语是什么意思"）
- complex：需要多步检索、跨章节综合或对比推理的问题（如"主要方法是什么"、"主要贡献有哪些"、"实验结果如何"、"局限性"、"A和B有什么关系"）

示例：
{examples}

现在分析这个问题：
问题：{question}
返回 JSON 格式：{{"intent": "意图类型", "complexity": "simple或complex", "reason": "一句话判断理由"}}"""


def planning_prompt(question: str, intent: str, metadata: Dict[str, str]) -> str:
    """Planner 节点：制定检索计划 + 生成首轮查询"""
    meta_text = (
        f"标题: {metadata.get('title', '')}\n"
        f"摘要: {metadata.get('abstract', '')[:300]}\n"
        f"关键词: {', '.join(metadata.get('keywords', []) or [])}"
    )
    return f"""你是论文问答系统的规划器。针对下面的问题制定检索计划。
论文元数据：
{meta_text}

用户问题：{question}
问题意图：{intent}

请制定检索计划，返回 JSON：
{{"plan": "一句话说明需要检索什么信息才能回答这个问题",
  "first_query": "第一轮检索使用的查询语句（可以是改写后更精确的版本）"}}"""


def critic_review_prompt(question: str, context: str) -> str:
    """Critic 节点：判断已检索信息是否足以回答问题"""
    return f"""你是论文问答系统的评判器。判断当前检索到的信息是否足以回答用户问题。
用户问题：{question}

已检索到的信息：
{context}

返回 JSON：
{{"sufficient": true或false,
  "missing_info": "如果不足，说明缺少什么信息（这将作为下一轮检索的查询依据）",
  "reason": "判断理由"}}"""


def answer_generation_prompt(
    question: str,
    context: str,
    intent: str,
    info_quality: str = "sufficient",
) -> str:
    """最终答案生成 — partial 档自动附加反幻觉约束"""
    style = INTENT_STYLE_PROMPTS.get(intent, INTENT_STYLE_PROMPTS["general"])

    base = f"""基于以下论文内容回答问题：
问题：{question}
参考内容：{context}
{style}"""

    if info_quality == "partial":
        base += """

重要要求：参考内容可能不完整。只依据参考内容回答，明确说明哪些部分论文中没有提及，严禁编造论文中不存在的信息。"""

    return base

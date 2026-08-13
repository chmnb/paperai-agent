"""论文解析 Agent 的 Prompt 模板"""
from typing import List, Dict, Any

VERSION = "1.0"


def metadata_extraction_prompt(raw_text: str) -> str:
    """从论文开头提取元数据（标题/作者/摘要/关键词）"""
    return f"""从以下学术论文的开头部分提取信息:
{raw_text}
请提取以下信息并返回 JSON 格式:
- title: 论文标题
- authors: 作者列表 (字符串, 用逗号分隔)
- abstract: 摘要内容
- keywords: 关键词列表 (数组)
如果某项无法提取, 返回空字符串或空数组。"""


def section_parsing_prompt(raw_text: str, max_sections: int = 8) -> str:
    """按章节解析论文结构"""
    return f"""将以下学术论文按章节解析:
{raw_text}
请识别主要章节, 返回 JSON 数组格式:
[{{"title": "章节标题", "content": "该章节的核心内容摘要 (100-200字)", "key_points": ["要点1", "要点2","要点3"]}}]
识别 5-{max_sections} 个主要章节, 包括: 引言、相关工作、方法、实验、结论等。"""

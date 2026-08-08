"""论文解析 Agent 工作流模块"""
from langgraph.graph import StateGraph, END
from app.agent.state import PaperParserState
from app.llm.client import get_llm_client
import json
import logging

logger = logging.getLogger(__name__)

async def extract_metadata(state: PaperParserState) -> PaperParserState:
    logger.info("📄 [论文解析Agent] 提取元数据")
    llm = get_llm_client()
    raw_text = state.get('raw_text', '')[:3000]
    prompt = f"""从以下学术论文的开头部分提取信息:
{raw_text}
请提取以下信息并返回 JSON 格式:
- title: 论文标题
- authors: 作者列表 (字符串, 用逗号分隔)
- abstract: 摘要内容
- keywords: 关键词列表 (数组)
如果某项无法提取, 返回空字符串或空数组。"""
    try:
        response = await llm.generate([prompt])
        text = response.generations[0][0].text.strip()
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        result = json.loads(text.strip())
        state['title'] = result.get('title', '')
        state['authors'] = result.get('authors', '')
        state['abstract'] = result.get('abstract', '')
        state['keywords'] = result.get('keywords', [])
        logger.info(f"✅ 元数据提取完成: {state['title'][:50]}...")
    except Exception as e:
        logger.error(f"❌ 元数据提取失败: {e}")
        state['title'] = '未知论文'
        state['authors'] = ''
        state['abstract'] = ''
        state['keywords'] = []
    return state

async def parse_sections(state: PaperParserState) -> PaperParserState:
    logger.info("📄 [论文解析Agent] 解析章节")
    llm = get_llm_client()
    raw_text = state.get('raw_text', '')[:8000]
    prompt = f"""将以下学术论文按章节解析:
{raw_text}
请识别主要章节, 返回 JSON 数组格式:
[{{"title": "章节标题", "content": "该章节的核心内容摘要 (100-200字)", "key_points": ["要点1", "要点2","要点3"]}}]
识别 5-8 个主要章节, 包括: 引言、相关工作、方法、实验、结论等。"""
    try:
        response = await llm.generate([prompt])
        text = response.generations[0][0].text.strip()
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        state['sections'] = json.loads(text.strip())
        logger.info(f"✅ 章节解析完成: {len(state['sections'])} 个章节")
    except Exception as e:
        logger.error(f"❌ 章节解析失败: {e}")
        state['sections'] = []
    return state

async def finalize_parsing(state: PaperParserState) -> PaperParserState:
    logger.info("✅ [论文解析Agent] 完成解析")
    state['parsed'] = True
    if not state.get('title'): state['title'] = '未知论文'
    if not state.get('sections'): state['sections'] = [{'title': '全文', 'content': state.get('raw_text', '')[:500], 'key_points': []}]
    return state

def create_paper_parser_graph():
    graph = StateGraph(PaperParserState)
    graph.add_node("extract_metadata", extract_metadata)
    graph.add_node("parse_sections", parse_sections)
    graph.add_node("finalize", finalize_parsing)
    graph.set_entry_point("extract_metadata")
    graph.add_edge("extract_metadata", "parse_sections")
    graph.add_edge("parse_sections", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()

_paper_parser = None

def get_paper_parser_agent():
    global _paper_parser
    if _paper_parser is None: _paper_parser = create_paper_parser_graph()
    return _paper_parser

async def run_paper_parser(paper_id: str, file_path: str, raw_text: str) -> dict:
    logger.info(f"🚀 [论文解析Agent] 开始解析论文: {paper_id}")
    initial_state: PaperParserState = {
        "paper_id": paper_id, "file_path": file_path, "raw_text": raw_text,
        "title": None, "authors": None, "abstract": None, "sections": [], "keywords": [],"parsed": False, "error": None
    }
    agent = get_paper_parser_agent()
    result = await agent.ainvoke(initial_state)
    logger.info(f"✅ [论文解析Agent] 解析完成")
    return {
        "title": result.get("title"), "authors": result.get("authors"), "abstract": result.get("abstract"),
        "sections": result.get("sections", []), "keywords": result.get("keywords", []), "parsed": result.get("parsed", False)
    }
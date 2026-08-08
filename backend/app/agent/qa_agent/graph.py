"""问答 Agent 工作流模块"""
from langgraph.graph import StateGraph, END
from app.agent.state import QAAgentState
from app.llm.client import get_llm_client
import json
import logging

logger = logging.getLogger(__name__)

async def recognize_intent(state: QAAgentState) -> QAAgentState:
    logger.info("🎯 [问答Agent] 识别问题意图")
    llm = get_llm_client()
    question = state.get('question', '')
    prompt = f"""分析以下关于论文的问题，判断其意图类型：
问题：{question}
意图类型：concept/method/experiment/code/general
返回 JSON 格式：{{"intent": "意图类型", "confidence": 0.9, "reason": "判断理由"}}"""
    try:
        response = await llm.generate([prompt])
        text = response.generations[0][0].text.strip()
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        result = json.loads(text.strip())
        state['intent'] = result.get('intent', 'general')
        state['confidence'] = result.get('confidence', 0.5)
        logger.info(f"✅ 意图识别完成：{state['intent']}")
    except Exception as e:
        logger.error(f"❌ 意图识别失败：{e}")
        state['intent'] = 'general'
        state['confidence'] = 0.5
    return state

async def generate_answer(state: QAAgentState) -> QAAgentState:
    logger.info("💬 [问答Agent] 生成答案")
    llm = get_llm_client()
    question = state.get('question', '')
    intent = state.get('intent', 'general')
    chunks = state.get('relevant_chunks', [])
    context = "\n\n".join([f"[片段{i+1}] {c.get('content', '')}" for i, c in enumerate(chunks[:3])]) if chunks else "未找到相关信息。"
    intent_prompts = {
        "concept": "请给出清晰、准确的概念解释。",
        "method": "请详细分析论文使用的方法，并解释其原理。",
        "experiment": "请分析实验结果并给出专业评价。",
        "code": "请给出简洁、可运行的实现代码。",
        "general": "请给出准确、全面的回答。"
    }
    prompt = f"""基于以下论文内容回答问题：
    问题：{question}
    参考内容：{context}
    {intent_prompts.get(intent, intent_prompts["general"])}"""
    try:
        response = await llm.generate([prompt])
        state['answer'] = response.generations[0][0].text.strip()
        state['sources'] = [c.get('source', '') for c in chunks[:3] if c.get('source')]
        logger.info(f"✅ 答案生成完成，长度：{len(state['answer'])}")
    except Exception as e:
        logger.error(f"❌ 答案生成失败：{e}")
        state['answer'] = "抱歉，无法生成答案。请稍后重试。"
    return state

def create_qa_agent_graph():
    graph = StateGraph(QAAgentState)
    graph.add_node("recognize_intent", recognize_intent)
    graph.add_node("generate_answer", generate_answer)
    graph.set_entry_point("recognize_intent")
    graph.add_edge("recognize_intent", "generate_answer")
    graph.add_edge("generate_answer", END)
    return graph.compile()

_qa_agent = None

def get_qa_agent():
    global _qa_agent
    if _qa_agent is None: _qa_agent = create_qa_agent_graph()
    return _qa_agent

async def run_qa_agent(paper_id: str, question: str, relevant_chunks: list) -> dict:
    logger.info(f"🚀 [问答Agent] 处理问题：{question[:50]}...")
    initial_state: QAAgentState = {
        "paper_id": paper_id, "question": question, "intent": None,
        "relevant_chunks": relevant_chunks, "answer": None, "sources": [], "confidence": 0.0,"error": None
    }
    agent = get_qa_agent()
    result = await agent.ainvoke(initial_state)
    logger.info(f"✅ [问答Agent] 处理完成")
    return {
        "answer": result.get("answer"), "intent": result.get("intent"),
        "sources": result.get("sources", []), "confidence": result.get("confidence", 0.0)
    }
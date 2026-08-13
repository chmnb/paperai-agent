"""问答 Agent 工作流模块 — 带自省循环（Agent Loop）的信息收集图

图结构:
  entry → recognize_intent
    ├─ 简单问题 → retrieve_once ──────────────→ END
    └─ 复杂问题 → planner → execute_tool ⇄ critic → END
                        (不足 & iter<max 时循环)

本图只负责"收集信息"，最终答案生成在 API 层（保持 SSE 流式）。
"""
from langgraph.graph import StateGraph, END
from app.agent.state import QAAgentState
from app.agent.qa_agent.tools import vector_search, full_text_search, get_paper_metadata
from app.llm.client import get_llm_client
from app.prompts import intent_recognition_prompt, planning_prompt, critic_review_prompt
import json
import logging

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3  # 循环硬上限，防止 Critic 无限要求重新检索


def _parse_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON"""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


# ── 节点 1: 意图识别（兼作简单/复杂问题路由器）──────────────────────
async def recognize_intent(state: QAAgentState) -> QAAgentState:
    logger.info("[AgentLoop] 意图识别")
    llm = get_llm_client()
    question = state.get("question", "")
    prompt = intent_recognition_prompt(question)
    try:
        response = await llm.generate([prompt])
        result = _parse_json(response.generations[0][0].text)
        state["intent"] = result.get("intent", "general")
        state["confidence"] = 0.8
        state["complexity"] = result.get("complexity", "simple")
        logger.info(f"[AgentLoop] 意图={state['intent']}, 复杂度={state['complexity']}")
    except Exception as e:
        logger.error(f"[AgentLoop] 意图识别失败: {e}")
        state["intent"] = "general"
        state["complexity"] = "simple"
    return state


# ── 节点 2: 快速路径 — 单次检索 ──────────────────────────────────────
async def retrieve_once(state: QAAgentState) -> QAAgentState:
    logger.info("[AgentLoop] 快速路径: 单次向量检索")
    paper_id = state["paper_id"]
    question = state["question"]
    chunks = await vector_search(paper_id, question, top_k=5)
    state["relevant_chunks"] = chunks
    state["ready_to_generate"] = True
    return state


# ── 节点 3: Planner — 复杂问题制定检索计划 ───────────────────────────
async def planner(state: QAAgentState) -> QAAgentState:
    logger.info("[AgentLoop] Planner 制定检索计划")
    llm = get_llm_client()
    question = state.get("question", "")
    intent = state.get("intent", "general")
    metadata = await get_paper_metadata(state["paper_id"])

    prompt = planning_prompt(question, intent, metadata)
    try:
        response = await llm.generate([prompt])
        result = _parse_json(response.generations[0][0].text)
        state["plan"] = result.get("plan", "")
        state["current_query"] = result.get("first_query", question)
        logger.info(f"[AgentLoop] 计划: {state['plan'][:60]}...")
        logger.info(f"[AgentLoop] 首轮 query: {state['current_query'][:60]}...")
    except Exception as e:
        logger.error(f"[AgentLoop] Planner 失败: {e}")
        state["plan"] = "直接检索与问题最相关的内容"
        state["current_query"] = question
    return state


# ── 节点 4: 工具执行 — 向量检索 / 全文检索 策略选择 ──────────────────
async def execute_tool(state: QAAgentState) -> QAAgentState:
    paper_id = state["paper_id"]
    query = state.get("current_query") or state["question"]
    iterations = state.get("iterations", 0)

    # 工具选择策略: 前两轮向量检索，第三轮全文精确检索兜底
    if iterations < 2:
        tool_name = "vector_search"
        logger.info(f"[AgentLoop] 第{iterations+1}轮: 向量检索 query='{query[:50]}'")
        new_chunks = await vector_search(paper_id, query, top_k=5)
    else:
        tool_name = "full_text_search"
        logger.info(f"[AgentLoop] 第{iterations+1}轮: 全文检索 query='{query[:50]}'")
        new_chunks = await full_text_search(paper_id, query, top_k=3)

    # 累积检索结果（按 content 去重）
    existing = state.get("relevant_chunks", [])
    seen = {c.get("content", "") for c in existing}
    for c in new_chunks:
        if c.get("content") and c["content"] not in seen:
            existing.append(c)
            seen.add(c["content"])

    state["relevant_chunks"] = existing
    state["tool_history"] = state.get("tool_history", []) + [tool_name]
    state["iterations"] = iterations + 1
    return state


# ── 节点 5: Critic — 自省：信息是否足够 ─────────────────────────────
async def critic(state: QAAgentState) -> QAAgentState:
    logger.info(f"[AgentLoop] Critic 第{state.get('iterations', 0)}轮自省")
    llm = get_llm_client()
    question = state.get("question", "")
    chunks = state.get("relevant_chunks", [])
    context = "\n\n".join([f"[片段{i+1}] {c.get('content', '')[:200]}" for i, c in enumerate(chunks[:6])]) or "（尚无检索结果）"

    prompt = critic_review_prompt(question, context)
    try:
        response = await llm.generate([prompt])
        result = _parse_json(response.generations[0][0].text)
        state["critic_feedback"] = result
        if result.get("sufficient"):
            logger.info("[AgentLoop] Critic: 信息足够")
            state["ready_to_generate"] = True
            state["info_quality"] = "sufficient"
        else:
            # 用 missing_info 改写下一轮检索 query（query rewriting）
            state["current_query"] = result.get("missing_info", question)
            logger.info(f"[AgentLoop] Critic: 信息不足, 下一轮 query='{state['current_query'][:50]}'")
    except Exception as e:
        logger.error(f"[AgentLoop] Critic 失败: {e}")
        state["critic_feedback"] = {"sufficient": True, "reason": "评判失败，尽力回答"}
        state["ready_to_generate"] = True
        state["info_quality"] = "sufficient"
    return state


# ── 路由函数 ────────────────────────────────────────────────────────
def route_by_intent(state: QAAgentState) -> str:
    """简单问题走快速路径，复杂问题进入 Agent Loop"""
    if state.get("complexity") == "complex":
        return "planner"
    return "retrieve_once"


def route_by_critic(state: QAAgentState) -> str:
    """Critic 判断后路由：足够→结束；不足且未超限→再检索；超限→质量分级后结束"""
    if state.get("ready_to_generate"):
        return END
    if state.get("iterations", 0) >= MAX_ITERATIONS:
        # 三轮仍不足 → 按检索质量分级降级（防幻觉的核心）
        chunks = state.get("relevant_chunks", [])
        if not chunks:
            state["info_quality"] = "none"       # 一无所获 → 诚实回答"找不到"
        else:
            best_score = max([c.get("score", 0.0) for c in chunks])
            if best_score < 0.3:                  # 相似度过低 → 视为垃圾检索
                state["info_quality"] = "none"
            else:
                state["info_quality"] = "partial"  # 有部分相关信息 → 加免责声明尽力回答
        logger.info(f"[AgentLoop] 达到最大迭代次数, 信息质量={state['info_quality']}")
        state["ready_to_generate"] = True
        return END
    return "execute_tool"


# ── 构图 ────────────────────────────────────────────────────────────
def create_qa_agent_graph():
    graph = StateGraph(QAAgentState)

    graph.add_node("recognize_intent", recognize_intent)
    graph.add_node("retrieve_once", retrieve_once)
    graph.add_node("planner", planner)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("critic", critic)

    graph.set_entry_point("recognize_intent")

    # 条件边：按复杂度路由
    graph.add_conditional_edges("recognize_intent", route_by_intent,
        {"planner": "planner", "retrieve_once": "retrieve_once"})

    # 快速路径直通 END
    graph.add_edge("retrieve_once", END)

    # Agent Loop 主干
    graph.add_edge("planner", "execute_tool")
    graph.add_edge("execute_tool", "critic")

    # 条件边：Critic 决定循环还是结束
    graph.add_conditional_edges("critic", route_by_critic,
        {"execute_tool": "execute_tool", END: END})

    return graph.compile()


_qa_agent = None


def get_qa_agent():
    global _qa_agent
    if _qa_agent is None:
        _qa_agent = create_qa_agent_graph()
    return _qa_agent


async def run_qa_agent(paper_id: str, question: str, relevant_chunks: list) -> dict:
    """运行信息收集循环，返回最终状态"""
    logger.info(f"[AgentLoop] 处理问题：{question[:50]}...")
    initial_state: QAAgentState = {
        "paper_id": paper_id, "question": question, "intent": None,
        "relevant_chunks": relevant_chunks, "answer": None, "sources": [],
        "confidence": 0.0, "error": None,
        "plan": None, "current_query": None, "tool_history": [],
        "iterations": 0, "max_iterations": MAX_ITERATIONS,
        "critic_feedback": None, "ready_to_generate": False,
        "complexity": "simple", "info_quality": "sufficient",
    }
    agent = get_qa_agent()
    result = await agent.ainvoke(initial_state)
    logger.info(f"[AgentLoop] 信息收集完成, 工具轨迹: {result.get('tool_history')}")
    return {
        "intent": result.get("intent"),
        "relevant_chunks": result.get("relevant_chunks", []),
        "plan": result.get("plan"),
        "tool_history": result.get("tool_history", []),
        "iterations": result.get("iterations", 0),
        "critic_feedback": result.get("critic_feedback"),
        "sources": [c.get("source", "") for c in result.get("relevant_chunks", [])[:3] if c.get("source")],
        "confidence": result.get("confidence", 0.0),
    }

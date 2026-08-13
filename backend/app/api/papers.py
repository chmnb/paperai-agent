"""论文 API 模块"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional
import os
import uuid
import json
import asyncio
import logging
import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.paper import Paper, Section, QAPair
from app.agent.paper_parser.graph import run_paper_parser
from app.agent.qa_agent.graph import run_qa_agent
from app.rag.knowledge_base import get_knowledge_base
from app.api.auth import decode_token
from app.config import settings
from app.prompts import answer_generation_prompt, NO_INFO_FALLBACK

router = APIRouter(prefix="/api/v1/papers")


async def get_current_user_id(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效")
    return payload.get("sub")


@router.get("")
async def list_papers(
    skip: int = Query(0), limit: int = Query(20),
    status: Optional[str] = None, search: Optional[str] = None,
    authorization: str = Header(None), db: AsyncSession = Depends(get_db)
):
    user_id = await get_current_user_id(authorization)
    query = select(Paper).where(Paper.user_id == user_id)
    if status:
        query = query.where(Paper.reading_status == status)
    if search:
        query = query.where(Paper.title.ilike(f"%{search}%"))
    query = query.order_by(Paper.uploaded_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    papers = result.scalars().all()
    return {"papers": [{"id": p.id, "title": p.title, "authors": p.authors,
            "abstract": p.abstract, "keywords": p.keywords,
            "reading_status": p.reading_status, "upload_at": str(p.uploaded_at)}
        for p in papers], "total": len(papers)}


@router.get("/{paper_id}")
async def get_paper(paper_id: str, authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    user_id = await get_current_user_id(authorization)
    result = await db.execute(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    return {"id": paper.id, "title": paper.title, "authors": paper.authors,
            "abstract": paper.abstract, "full_text": paper.full_text[:5000] if paper.full_text else "",
            "keywords": paper.keywords, "reading_status": paper.reading_status,
            "upload_at": str(paper.uploaded_at)}


@router.get("/{paper_id}/sections")
async def get_sections(paper_id: str, authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    user_id = await get_current_user_id(authorization)
    result = await db.execute(select(Section).where(Section.paper_id == paper_id).order_by(Section.order_index))
    sections = result.scalars().all()
    return {"sections": [{"section_title": s.section_title, "content": s.content,
            "order_index": s.order_index} for s in sections]}


@router.delete("/{paper_id}")
async def delete_paper(paper_id: str, authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    user_id = await get_current_user_id(authorization)
    paper = (await db.execute(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))).scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    await db.delete(paper)
    await db.commit()
    # 清理文件
    if paper.pdf_path and os.path.exists(paper.pdf_path):
        os.remove(paper.pdf_path)
    kb = get_knowledge_base()
    await kb.delete_paper(paper_id)
    return {"message": "删除成功"}


@router.patch("/{paper_id}/status")
async def update_status(paper_id: str, data: dict, authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    user_id = await get_current_user_id(authorization)
    paper = (await db.execute(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))).scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    if "status" in data: paper.reading_status = data["status"]
    if "progress" in data: paper.reading_progress = data["progress"]
    if "favorite" in data: paper.is_favorite = data["favorite"]
    await db.commit()
    return {"message": "更新成功"}


# ── 后台异步处理论文 ─────────────────────────────────────────────
async def _process_paper_bg(paper_id: str, raw_text: str, file_path: str, file_name: str):
    """后台任务：LLM 解析 + 章节入库 + 向量化，使用独立 DB 会话"""
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            # 1. LLM 解析
            try:
                parse_result = await run_paper_parser(paper_id, file_path, raw_text)
            except Exception:
                parse_result = {"title": file_name.replace(".pdf", ""), "authors": "",
                                "abstract": raw_text[:500], "sections": [], "keywords": []}

            # 2. 更新论文记录
            result = await db.execute(select(Paper).where(Paper.id == paper_id))
            paper = result.scalar_one_or_none()
            if paper:
                paper.title = parse_result.get("title", file_name)
                paper.authors = parse_result.get("authors", "")
                paper.abstract = parse_result.get("abstract", "")
                paper.keywords = parse_result.get("keywords", [])
                paper.reading_status = "ready"

                # 清除旧章节，写入新章节
                await db.execute(delete(Section).where(Section.paper_id == paper_id))
                for i, sec in enumerate(parse_result.get("sections", [])):
                    db.add(Section(paper_id=paper_id,
                        section_title=sec.get("title", f"第{i+1}节"),
                        order_index=i, content=sec.get("content", "")))
                await db.commit()

            # 3. 向量化
            text = raw_text[:100000]
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500, chunk_overlap=100,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            doc_chunks = splitter.create_documents([text])
            chunks = [{"content": c.page_content, "type": "text", "index": i, "section": ""}
                      for i, c in enumerate(doc_chunks)]

            sections = parse_result.get("sections", [])
            for chunk_data in chunks:
                for sec in sections:
                    if sec.get("title") and sec["title"][:10] in raw_text:
                        sec_start = raw_text.find(sec["title"])
                        chunk_start = raw_text.find(chunk_data["content"])
                        if chunk_start >= sec_start:
                            chunk_data["section"] = sec.get("title", "")
                            break

            kb = get_knowledge_base()
            await kb.add_paper_chunks(paper_id, chunks)
            logger.info(f"[BG] 论文 {paper_id} 后台处理完成")

        except Exception as e:
            logger.error(f"[BG] 论文 {paper_id} 后台处理失败: {e}")
            try:
                result = await db.execute(select(Paper).where(Paper.id == paper_id))
                paper = result.scalar_one_or_none()
                if paper:
                    paper.reading_status = "error"
                    await db.commit()
            except Exception:
                pass


# ── 上传端点（异步版）─────────────────────────────────────────────
@router.post("/upload")
async def upload_paper(file: UploadFile = File(...), authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    user_id = await get_current_user_id(authorization)
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小不能超过 {settings.MAX_UPLOAD_SIZE//1024//1024} MB")

    paper_id = str(uuid.uuid4())
    file_path = os.path.join(settings.FILE_STORAGE_PATH, f"{paper_id}.pdf")
    os.makedirs(settings.FILE_STORAGE_PATH, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)

    # 提取文本（快速，同步完成）
    raw_text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text: raw_text += text + "\n\n"
                if i >= 50: break
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 解析失败: {str(e)}")
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="无法从 PDF 中提取文本")

    # 先创建基础记录，状态标记为 processing
    paper = Paper(id=paper_id, user_id=user_id,
        title=file.filename, authors="解析中...",
        abstract="正在解析论文...", full_text=raw_text[:100000],
        pdf_path=file_path, keywords=[], reading_status="processing")
    db.add(paper)
    await db.commit()

    # 启动后台异步任务处理 LLM 解析 + 向量化
    asyncio.create_task(_process_paper_bg(paper_id, raw_text, file_path, file.filename))

    return {"paper_id": paper_id, "title": file.filename,
            "status": "processing", "message": "论文已上传，正在后台解析"}



@router.post("/{paper_id}/qa")
async def ask_question(paper_id: str, data: dict, authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    user_id = await get_current_user_id(authorization)
    question = data.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    result = await db.execute(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="论文不存在")

    # Agent Loop 收集信息
    loop_result = await run_qa_agent(paper_id, question, [])
    chunks = loop_result.get("relevant_chunks", [])
    intent = loop_result.get("intent", "general")

    # 生成答案
    from app.llm.client import get_llm_client
    llm = get_llm_client()
    context = "\n\n".join([f"[片段{i+1}] {c.get('content', '')}" for i, c in enumerate(chunks[:6])]) if chunks else "未找到相关信息。"
    prompt = answer_generation_prompt(question, context, intent)
    gen_result = await llm.generate([prompt])
    answer = gen_result.generations[0][0].text.strip()

    qa_pair = QAPair(paper_id=paper_id, order_index=1, question=question,
        answer=answer, chunk_context=context[:500],
        relevance_score=loop_result.get('confidence', 0.0))
    db.add(qa_pair)
    await db.commit()
    return {"answer": answer, "intent": intent,
            "sources": loop_result.get("sources", []), "confidence": loop_result.get("confidence"),
            "plan": loop_result.get("plan"), "tool_history": loop_result.get("tool_history"),
            "qa_id": str(qa_pair.id)}


@router.post("/{paper_id}/qa/stream")
async def ask_question_stream(paper_id: str, data: dict, authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    """流式问答端点 — Agent Loop 收集信息 + SSE 逐字返回答案"""
    user_id = await get_current_user_id(authorization)
    question = data.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    result = await db.execute(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="论文不存在")

    from app.llm.client import get_llm_client
    from app.agent.qa_agent.graph import get_qa_agent
    from app.agent.state import QAAgentState
    llm = get_llm_client()

    initial_state: QAAgentState = {
        "paper_id": paper_id, "question": question, "intent": None,
        "relevant_chunks": [], "answer": None, "sources": [],
        "confidence": 0.0, "error": None,
        "complexity": "simple", "plan": None, "current_query": None,
        "tool_history": [], "iterations": 0, "max_iterations": 3,
        "critic_feedback": None, "ready_to_generate": False,
        "info_quality": "sufficient",
    }

    async def generate_stream():
        full_answer = ""
        final_intent = "general"
        # ── 阶段 1: Agent Loop 收集信息（推送 thinking 事件）─────────
        agent = get_qa_agent()
        last_state = initial_state
        try:
            async for state in agent.astream(initial_state, stream_mode="values"):
                # 意图变化时推送（识别 + 路由判断）
                if state.get("intent") and state["intent"] != last_state.get("intent"):
                    final_intent = state["intent"]
                    complexity = state.get("complexity", "simple")
                    route_msg = "进入 Agent Loop" if complexity == "complex" else "快速路径（单次检索）"
                    yield f"data: {json.dumps({'thinking': '意图识别: ' + str(state['intent']) + ' → ' + route_msg})}\n\n"
                # 规划变化时推送
                if state.get("plan") and state["plan"] != last_state.get("plan"):
                    yield f"data: {json.dumps({'thinking': '规划: ' + str(state['plan'])[:100]})}\n\n"
                # 工具执行记录（仅新增时推送）
                th = state.get("tool_history", [])
                lth = last_state.get("tool_history", [])
                if len(th) > len(lth):
                    tool_msg = "第{}轮检索完成 ({})，累计 {} 个片段".format(
                        len(th), th[-1], len(state.get('relevant_chunks', [])))
                    yield f"data: {json.dumps({'thinking': tool_msg})}\n\n"
                # Critic 反馈（仅新增时推送）
                cf = state.get("critic_feedback")
                lcf = last_state.get("critic_feedback")
                if cf and cf != lcf and cf.get("reason"):
                    verdict = "信息足够" if cf.get("sufficient") else "信息不足，继续检索"
                    yield f"data: {json.dumps({'thinking': '自省: ' + verdict + ' - ' + str(cf['reason'])[:80]})}\n\n"
                last_state = state
        except Exception as e:
            logger.error(f"[Stream] Agent Loop 失败: {e}")

        chunks = last_state.get("relevant_chunks", [])
        info_quality = last_state.get("info_quality", "sufficient")
        context = "\n\n".join([f"[片段{i+1}] {c.get('content', '')}" for i, c in enumerate(chunks[:6])]) if chunks else "未找到相关信息。"

        # ── 三档质量分级降级策略（防幻觉）───────────────────────────
        if info_quality == "none":
            # 三轮检索一无所获 → 不调 LLM，诚实回答 + 给出重试建议
            fallback = NO_INFO_FALLBACK
            yield f"data: {json.dumps({'thinking': '三轮检索未找到相关内容，诚实降级（不调用 LLM 防编造）'})}\n\n"
            for i in range(0, len(fallback), 10):
                yield f"data: {json.dumps({'token': fallback[i:i+10]})}\n\n"
            full_answer = fallback
            try:
                qa_pair = QAPair(paper_id=paper_id, order_index=1, question=question,
                    answer=full_answer, chunk_context="",
                    relevance_score=0.0)
                db.add(qa_pair)
                await db.commit()
                yield f"data: {json.dumps({'done': True, 'intent': final_intent, 'qa_id': str(qa_pair.id)})}\n\n"
            except Exception:
                yield f"data: {json.dumps({'done': True, 'intent': final_intent})}\n\n"
            return

        if info_quality == "partial":
            # 有部分信息 → 正常生成，但强制加反幻觉指令
            prompt = answer_generation_prompt(question, context, final_intent, info_quality="partial")
            yield f"data: {json.dumps({'thinking': '检索信息不完整，已加入反幻觉约束'})}\n\n"
        else:
            prompt = answer_generation_prompt(question, context, final_intent)

        # ── 阶段 2: 流式生成答案 ────────────────────────────────────
        try:
            async for token in llm.astream(prompt):
                full_answer += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'token': '[生成出错]'})}\n\n"
        finally:
            # 保存问答记录
            if full_answer:
                try:
                    qa_pair = QAPair(paper_id=paper_id, order_index=1, question=question,
                        answer=full_answer, chunk_context=context[:500],
                        relevance_score=0.8)
                    db.add(qa_pair)
                    await db.commit()
                    yield f"data: {json.dumps({'done': True, 'intent': final_intent, 'qa_id': str(qa_pair.id)})}\n\n"
                except Exception:
                    yield f"data: {json.dumps({'done': True, 'intent': final_intent})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

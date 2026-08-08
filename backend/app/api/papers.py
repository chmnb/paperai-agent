"""论文 API 模块"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional
import os
import uuid
import pdfplumber

from app.database import get_db
from app.models.paper import Paper, Section, QAPair
from app.agent.paper_parser.graph import run_paper_parser
from app.agent.qa_agent.graph import run_qa_agent
from app.rag.knowledge_base import get_knowledge_base
from app.api.auth import decode_token
from app.config import settings

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
    # 提取文本 (不需要 LLM)
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
    # 尝试 LLM 解析，失败则用默认值
    try:
        parse_result = await run_paper_parser(paper_id, file_path, raw_text)
    except Exception:
        parse_result = {"title": file.filename.replace(".pdf", ""), "authors": "", "abstract": raw_text[:500], "sections": [], "keywords": []}
    paper = Paper(id=paper_id, user_id=user_id,
        title=parse_result.get('title', file.filename),
        authors=parse_result.get('authors'),
        abstract=parse_result.get('abstract'),
        full_text=raw_text[:100000], pdf_path=file_path,
        keywords=parse_result.get('keywords', []))
    db.add(paper)
    for i, section_data in enumerate(parse_result.get('sections', [])):
        section = Section(paper_id=paper_id, section_title=section_data.get('title', f'第{i+1}节'), order_index=i, content=section_data.get('content', ''))
        db.add(section)
    await db.commit()
    # 添加到向量库 (失败不影响上传)
    try:
        kb = get_knowledge_base()
        chunks = [{"content": raw_text[i:i+1000], "type": "text", "index": i // 1000, "section": ""} for i in range(0, min(len(raw_text), 100000), 1000)]
        await kb.add_paper_chunks(paper_id, chunks)
    except Exception:
        pass
    return {"paper_id": paper_id, "title": parse_result.get('title'), "authors": parse_result.get('authors'),
            "sections_count": len(parse_result.get('sections', [])), "message": "论文上传并解析成功"}


@router.post("/{paper_id}/qa")
async def ask_question(paper_id: str, data: dict, authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    user_id = await get_current_user_id(authorization)
    question = data.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    result = await db.execute(select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="论文不存在")
    kb = get_knowledge_base()
    chunks = await kb.query(paper_id, question, top_k=5)
    result = await run_qa_agent(paper_id, question, chunks)
    qa_pair = QAPair(paper_id=paper_id, order_index=1, question=question,
        answer=result.get('answer'), chunk_context="\n\n".join([c.get('content', '') for c in chunks[:3]]),
        relevance_score=result.get('confidence', 0.0))
    db.add(qa_pair)
    await db.commit()
    return {"answer": result.get("answer"), "intent": result.get("intent"),
            "sources": result.get("sources", []), "confidence": result.get("confidence"),
            "qa_id": str(qa_pair.id)}

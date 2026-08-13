"""问答 Agent 工具集 — 向量检索 / 全文检索 / 元数据查询"""
from typing import List, Dict, Any
from app.rag.knowledge_base import get_knowledge_base
from app.database import AsyncSessionLocal
from app.models.paper import Paper
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


async def vector_search(paper_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """向量语义检索（ChromaDB）"""
    kb = get_knowledge_base()
    chunks = await kb.query(paper_id, query, top_k=top_k)
    for c in chunks:
        c["tool"] = "vector_search"
    return chunks


async def full_text_search(paper_id: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """全文关键词检索（数据库 LIKE 匹配），用于找回向量检索漏掉的具体细节

    针对表格数字、专有名词、公式编号等 embedding 难以捕捉的精确内容。
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Paper.full_text).where(Paper.id == paper_id)
        )
        full_text = result.scalar_one_or_none()
        if not full_text:
            return []

        chunks = []
        keywords = [w.strip() for w in query.split() if len(w.strip()) >= 2]
        if not keywords:
            return []

        # 按句子切分后找包含关键词的句子及其上下文
        sentences = [s.strip() for s in full_text.replace("\n", " ").split(".") if s.strip()]
        for i, sent in enumerate(sentences):
            if any(k.lower() in sent.lower() for k in keywords):
                # 取上下文窗口：前后各 1 句
                start = max(0, i - 1)
                end = min(len(sentences), i + 2)
                context = ". ".join(sentences[start:end])
                chunks.append({
                    "content": context,
                    "source": "全文检索",
                    "chunk_type": "full_text",
                    "score": 0.0,
                    "tool": "full_text_search",
                })
                if len(chunks) >= top_k:
                    break
        return chunks


async def get_paper_metadata(paper_id: str) -> Dict[str, Any]:
    """获取论文元数据（标题、作者、摘要、关键词）"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Paper).where(Paper.id == paper_id))
        paper = result.scalar_one_or_none()
        if not paper:
            return {}
        return {
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "keywords": paper.keywords or [],
        }

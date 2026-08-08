"""RAG 论文知识库模块"""
from typing import List, Dict, Any, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.config import settings
import logging
import os

logger = logging.getLogger(__name__)


class PaperKnowledgeBase:
    _embeddings = None

    @staticmethod
    def _get_embeddings():
        if PaperKnowledgeBase._embeddings is None:
            logger.info("[KB] 加载本地 embedding 模型 (all-MiniLM-L6-v2)...")
            PaperKnowledgeBase._embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
            )
            logger.info("[KB] 本地 embedding 模型就绪")
        return PaperKnowledgeBase._embeddings

    @property
    def vectorstore(self):
        if not hasattr(self, "_vectorstore") or self._vectorstore is None:
            os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
            self._vectorstore = Chroma(
                collection_name="papers",
                embedding_function=self._get_embeddings(),
                persist_directory=settings.VECTOR_STORE_PATH,
            )
        return self._vectorstore

    async def add_paper_chunks(self, paper_id: str, chunks: List[Dict[str, Any]]) -> bool:
        try:
            docs = [Document(page_content=chunk.get("content", ""), metadata={
                "paper_id": paper_id, "chunk_type": chunk.get("type", "text"),
                "section": chunk.get("section", ""), "chunk_index": chunk.get("index", 0),
            }) for chunk in chunks]
            if docs:
                self.vectorstore.add_documents(docs)
                logger.info(f"[KB] 添加 {len(docs)} 个论文片段")
            return True
        except Exception as e:
            logger.error(f"[KB] 添加论文片段失败: {e}")
            return False

    async def query(self, paper_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            results = self.vectorstore.similarity_search_with_score(
                query=query, k=top_k, filter={"paper_id": paper_id}
            )
            chunks = [{
                "content": doc.page_content, "source": doc.metadata.get("section", ""),
                "chunk_type": doc.metadata.get("chunk_type", ""), "score": 1 - score,
            } for doc, score in results]
            logger.info(f"[KB] 查询完成, 返回 {len(chunks)} 个片段")
            return chunks
        except Exception as e:
            logger.error(f"[KB] 查询失败: {e}")
            return []

    async def delete_paper(self, paper_id: str) -> bool:
        try:
            self.vectorstore.delete(filter={"paper_id": paper_id})
            logger.info(f"[KB] 删除论文 {paper_id} 的向量")
            return True
        except Exception as e:
            logger.error(f"[KB] 删除论文向量失败: {e}")
            return False


_knowledge_base: Optional[PaperKnowledgeBase] = None


def get_knowledge_base() -> PaperKnowledgeBase:
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = PaperKnowledgeBase()
    return _knowledge_base

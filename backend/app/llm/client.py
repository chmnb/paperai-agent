"""LLM 大模型客户端模块"""
from typing import Optional, List, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Generation:
    def __init__(self, text: str):
        self.text = text
        self.message = None


class LLMResult:
    def __init__(self, texts: List[str]):
        self.generations = [[Generation(text=t)] for t in texts]
        self.llm_output = {}


class LLMClient:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.client = self._create_client()

    def _create_client(self) -> ChatOpenAI:
        if self.provider == "openai":
            return ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY,
                            base_url=settings.OPENAI_BASE_URL, temperature=0.7)
        elif self.provider == "deepseek":
            return ChatOpenAI(model=settings.DEEPSEEK_MODEL, api_key=settings.DEEPSEEK_API_KEY,
                            base_url=settings.DEEPSEEK_BASE_URL, temperature=0.7)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")

    async def generate(self, prompts: List[str]) -> LLMResult:
        try:
            results = []
            for prompt in prompts:
                response = await self.client.ainvoke([HumanMessage(content=prompt)])
                results.append(response.content)
            return LLMResult(results)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    async def astream(self, prompt: str) -> AsyncGenerator[str, None]:
        """流式生成，逐 token yield"""
        try:
            async for chunk in self.client.astream([HumanMessage(content=prompt)]):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise


_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

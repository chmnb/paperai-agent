"""Agent 状态定义模块"""
from typing import TypedDict, List, Optional, Dict, Any


class PaperParserState(TypedDict):
    paper_id: str
    file_path: str
    raw_text: str
    title: Optional[str]
    authors: Optional[str]
    abstract: Optional[str]
    sections: List[Dict[str, Any]]
    keywords: List[str]
    parsed: bool
    error: Optional[str]


class QAAgentState(TypedDict):
    paper_id: str
    question: str
    intent: Optional[str]
    relevant_chunks: List[Dict[str, Any]]
    answer: Optional[str]
    sources: List[str]
    confidence: float
    error: Optional[str]


class SummarizerState(TypedDict):
    paper_id: str
    summary_type: str
    sections: List[Dict[str, Any]]
    summary: Optional[str]
    key_findings: List[str]
    contributions: List[str]
    limitations: List[str]
    error: Optional[str]
"""论文相关模型"""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON, ARRAY, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base

class Paper(Base):
    __tablename__ = "papers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    authors = Column(Text)
    abstract = Column(Text)
    full_text = Column(Text)
    pdf_path = Column(String(500))
    source_url = Column(String(500))
    doi = Column(String(100))
    keywords = Column(ARRAY(String))
    research_area = Column(String(100))
    publication_year = Column(Integer)
    venue = Column(String(200))
    citation_count = Column(Integer, default=0)
    reading_status = Column(String(20), default='unread')
    reading_progress = Column(Float, default=0)
    is_favorite = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="papers")
    sections = relationship("Section", back_populates="paper", cascade="all, delete-orphan")
    qa_pairs = relationship("QAPair", back_populates="paper", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="paper")



class Section(Base):
    __tablename__ = "sections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    section_title = Column(String(200), nullable=False)
    order_index = Column(Integer, nullable=False)
    content = Column(Text)
    summary = Column(Text)
    tables = Column(JSON, default=list)
    figures = Column(JSON, default=list)
    formulas = Column(JSON, default=list)
    key_points = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)
    paper = relationship("Paper", back_populates="sections")


class QAPair(Base):
    __tablename__ = "qa_pairs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    chunk_context = Column(Text)
    relevance_score = Column(Float)
    is_bookmarked = Column(Boolean, default=False)
    tags = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)
    paper = relationship("Paper", back_populates="qa_pairs")


class Note(Base):
    __tablename__ = "notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"))
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id"))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(String(50))
    tags = Column(ARRAY(String))
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="notes")
    paper = relationship("Paper", back_populates="notes")


class Folder(Base):
    __tablename__ = "folders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("folders.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    color = Column(String(20))
    icon = Column(String(50))
    order_index = Column(Integer, default=0)
    paper_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="folders")
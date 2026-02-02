from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import create_engine, Column, String, Text, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

from app.config import get_settings

settings = get_settings()

Base = declarative_base()
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class ProjectStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    OUTDATED = "OUTDATED"


class AnswerStatus(str, Enum):
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    MANUAL = "MANUAL"


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    INDEXING = "INDEXING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


# SQLAlchemy Models

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default=ProjectStatus.DRAFT.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    questions = relationship("Question", back_populates="project", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    section = Column(String, default="General")
    question_text = Column(Text, nullable=False)
    order_index = Column(Integer, default=0)
    
    project = relationship("Project", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False, cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"
    
    id = Column(String, primary_key=True)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False)
    
    # AI-generated answer
    ai_answer = Column(Text, default="")
    
    # Parallel generation results (for debugging/comparison)
    answer_variant_a = Column(Text, default="")
    answer_variant_b = Column(Text, default="")
    
    # Human override
    manual_answer = Column(Text, default="")
    
    # Citations: [{doc_id, page, text, chunk_id}]
    citations = Column(JSON, default=list)
    
    # Confidence score 0.0 - 1.0
    confidence = Column(Float, default=0.0)
    
    # Is the question answerable from the documents?
    is_answerable = Column(String, default="unknown")  # yes, no, partial, unknown
    
    status = Column(String, default=AnswerStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    question = relationship("Question", back_populates="answer")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, default="")
    status = Column(String, default=DocumentStatus.PENDING.value)
    page_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, default="")
    indexed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

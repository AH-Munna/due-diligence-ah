from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# === Document Schemas ===

class DocumentUpload(BaseModel):
    filename: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    page_count: int
    chunk_count: int
    error_message: str = ""
    indexed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# === Citation Schema ===

class Citation(BaseModel):
    doc_id: str
    doc_name: str
    page: int
    text: str
    chunk_id: str = ""


# === Answer Schemas ===

class AnswerResponse(BaseModel):
    id: str
    question_id: str
    ai_answer: str
    manual_answer: str = ""
    citations: List[Citation] = []
    confidence: float
    is_answerable: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AnswerUpdate(BaseModel):
    """For human review updates."""
    status: str  # CONFIRMED, REJECTED, MANUAL
    manual_answer: Optional[str] = None


# === Question Schemas ===

class QuestionBase(BaseModel):
    section: str = "General"
    question_text: str
    order_index: int = 0


class QuestionResponse(BaseModel):
    id: str
    section: str
    question_text: str
    order_index: int
    answer: Optional[AnswerResponse] = None
    
    class Config:
        from_attributes = True


# === Project Schemas ===

class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    question_ids: List[str] = Field(default_factory=list, description="IDs of sample questions to include")


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    questions: List[QuestionResponse] = []
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    id: str
    name: str
    status: str
    question_count: int
    answered_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# === Sample Questions Schema ===

class SampleQuestion(BaseModel):
    id: str
    section: str
    text: str
    type: str = "factual"  # factual, analytical, procedural


class SampleQuestionsResponse(BaseModel):
    sections: List[dict]

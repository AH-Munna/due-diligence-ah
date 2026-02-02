"""Project management API routes."""
import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import uuid

from app.models.database import get_db, Project, Question, ProjectStatus
from app.models.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectListResponse,
    SampleQuestionsResponse,
)

router = APIRouter()

# Path to sample questions
SAMPLE_QUESTIONS_PATH = Path(__file__).parent.parent.parent / "data" / "sample_questions.json"


@router.get("/sample-questions", response_model=SampleQuestionsResponse)
def get_sample_questions():
    """Get available sample questions for project creation."""
    if not SAMPLE_QUESTIONS_PATH.exists():
        return {"sections": []}
    
    with open(SAMPLE_QUESTIONS_PATH) as f:
        data = json.load(f)
    return data


@router.get("", response_model=List[ProjectListResponse])
def list_projects(db: Session = Depends(get_db)):
    """List all projects with summary stats."""
    projects = db.query(Project).all()
    result = []
    
    for p in projects:
        answered = sum(1 for q in p.questions if q.answer and q.answer.status != "PENDING")
        result.append(ProjectListResponse(
            id=p.id,
            name=p.name,
            status=p.status,
            question_count=len(p.questions),
            answered_count=answered,
            created_at=p.created_at,
        ))
    
    return result


@router.post("", response_model=ProjectResponse)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project with selected questions."""
    project_id = str(uuid.uuid4())
    
    # Create project
    project = Project(
        id=project_id,
        name=data.name,
        description=data.description,
        status=ProjectStatus.DRAFT.value,
    )
    db.add(project)
    
    # Load sample questions and add selected ones
    if data.question_ids and SAMPLE_QUESTIONS_PATH.exists():
        with open(SAMPLE_QUESTIONS_PATH) as f:
            sample_data = json.load(f)
        
        # Flatten questions from sections
        all_questions = {}
        for section in sample_data.get("sections", []):
            for q in section.get("questions", []):
                all_questions[q["id"]] = {
                    "section": section["name"],
                    "text": q["text"],
                }
        
        # Add selected questions
        for idx, qid in enumerate(data.question_ids):
            if qid in all_questions:
                question = Question(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    section=all_questions[qid]["section"],
                    question_text=all_questions[qid]["text"],
                    order_index=idx,
                )
                db.add(question)
    
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get project details with all questions and answers."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project and all its questions/answers."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"status": "deleted", "id": project_id}


@router.post("/{project_id}/generate")
async def generate_all_answers(project_id: str, db: Session = Depends(get_db)):
    """Generate answers for all questions in the project."""
    from app.services.answer import generate_answers_for_project
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = await generate_answers_for_project(project, db)
    
    # Update project status
    project.status = ProjectStatus.READY.value
    db.commit()
    
    return result


@router.get("/{project_id}/generate-stream")
async def generate_answers_stream(project_id: str, db: Session = Depends(get_db)):
    """
    Generate answers with SSE streaming for real-time progress.
    Returns Server-Sent Events with progress updates.
    """
    from app.services.answer import generate_answers_for_project_with_progress
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    async def event_generator():
        async for progress in generate_answers_for_project_with_progress(project, db):
            yield f"data: {json.dumps(progress)}\n\n"
        
        # Update project status at the end
        project.status = ProjectStatus.READY.value
        db.commit()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


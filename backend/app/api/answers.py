"""Answer generation and review API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db, Answer, Question, AnswerStatus
from app.models.schemas import AnswerResponse, AnswerUpdate

router = APIRouter()


@router.get("/{answer_id}", response_model=AnswerResponse)
def get_answer(answer_id: str, db: Session = Depends(get_db)):
    """Get answer details by ID."""
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    return answer


@router.post("/{question_id}/generate", response_model=AnswerResponse)
async def generate_single_answer(question_id: str, db: Session = Depends(get_db)):
    """Generate answer for a single question."""
    from app.services.answer import generate_answer
    
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    answer = await generate_answer(question, db)
    return answer


@router.patch("/{answer_id}", response_model=AnswerResponse)
def update_answer(answer_id: str, data: AnswerUpdate, db: Session = Depends(get_db)):
    """Update answer status (review workflow)."""
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    # Validate status transition
    valid_statuses = [s.value for s in AnswerStatus]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    answer.status = data.status
    
    # If manual override, save the manual answer
    if data.status == AnswerStatus.MANUAL.value and data.manual_answer:
        answer.manual_answer = data.manual_answer
    
    db.commit()
    db.refresh(answer)
    return answer

"""Answer generation service with parallel generation + merge strategy."""
import asyncio
import uuid
from typing import List, Dict, Any, Optional
from openai import OpenAI
from sqlalchemy.orm import Session

from app.models.database import Question, Answer, AnswerStatus
from app.services.indexer import search_chunks
from app.config import get_settings

settings = get_settings()

# Initialize NVIDIA NIM client
client = OpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key,
)


def build_answer_prompt(question: str, context_chunks: List[Dict[str, Any]]) -> str:
    """Build the prompt for answer generation."""
    context = "\n\n---\n\n".join([
        f"[Source: {c['metadata'].get('doc_name', 'Unknown')}, Page {c['metadata'].get('page', '?')}]\n{c['text']}"
        for c in context_chunks
    ])
    
    return f"""You are a due diligence analyst helping answer questionnaire questions based on provided documents.

CONTEXT FROM DOCUMENTS:
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Answer the question based ONLY on the provided context
2. If the context doesn't contain enough information, say "INSUFFICIENT_DATA" and explain what's missing
3. Include specific citations in your answer using the format [Source: DocName, Page X]
4. Be concise but thorough
5. Provide a confidence score (0.0 to 1.0) at the end in the format: CONFIDENCE: X.X

ANSWER:"""


def build_merge_prompt(question: str, answer_a: str, answer_b: str) -> str:
    """Build the prompt for merging two answer variants."""
    return f"""You are reviewing two AI-generated answers to the same due diligence question.
Your task is to create the best possible final answer by:
1. Selecting the more accurate and complete information from each
2. Correcting any errors or inconsistencies
3. Improving clarity and formatting
4. Consolidating citations (remove duplicates, keep most specific)
5. Determining the final confidence score

QUESTION: {question}

ANSWER A:
{answer_a}

ANSWER B:
{answer_b}

Create the optimal merged answer. Keep the same format with citations and end with CONFIDENCE: X.X

FINAL ANSWER:"""


def call_llm(prompt: str, temperature: float) -> str:
    """Make a single LLM call."""
    try:
        completion = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=settings.max_tokens,
        )
        
        if completion.choices:
            return completion.choices[0].message.content or ""
        return ""
    except Exception as e:
        return f"ERROR: {str(e)}"


def parse_answer_response(response: str) -> Dict[str, Any]:
    """Parse the LLM response to extract answer, confidence, and answerability."""
    # Extract confidence score
    confidence = 0.5  # Default
    if "CONFIDENCE:" in response:
        try:
            conf_part = response.split("CONFIDENCE:")[-1].strip()
            confidence = float(conf_part.split()[0])
            confidence = max(0.0, min(1.0, confidence))  # Clamp
        except (ValueError, IndexError):
            pass
    
    # Check answerability
    is_answerable = "yes"
    if "INSUFFICIENT_DATA" in response:
        is_answerable = "partial"
    
    # Clean up response (remove confidence line for display)
    answer_text = response
    if "CONFIDENCE:" in answer_text:
        answer_text = answer_text.rsplit("CONFIDENCE:", 1)[0].strip()
    
    return {
        "text": answer_text,
        "confidence": confidence,
        "is_answerable": is_answerable,
    }


def extract_citations(answer_text: str, context_chunks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract citation references from the answer text."""
    citations = []
    seen = set()
    
    for chunk in context_chunks:
        doc_name = chunk["metadata"].get("doc_name", "")
        page = chunk["metadata"].get("page", 0)
        
        # Check if this source is mentioned in the answer
        citation_key = f"{doc_name}_p{page}"
        if citation_key not in seen:
            # Simple check: is the doc name mentioned?
            if doc_name.lower() in answer_text.lower() or f"page {page}" in answer_text.lower():
                citations.append({
                    "doc_id": chunk["metadata"].get("doc_id", ""),
                    "doc_name": doc_name,
                    "page": page,
                    "text": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                    "chunk_id": chunk["id"],
                })
                seen.add(citation_key)
    
    return citations


async def generate_answer(question: Question, db: Session) -> Answer:
    """
    Generate an answer using the parallel + merge strategy:
    1. Retrieve relevant chunks
    2. Generate two answers in parallel with different temperatures
    3. Merge the answers with a third LLM call
    """
    # Check if answer already exists
    existing = db.query(Answer).filter(Answer.question_id == question.id).first()
    if existing:
        return existing
    
    # Retrieve relevant chunks
    chunks = search_chunks(question.question_text, n_results=8)
    
    if not chunks:
        # No documents indexed yet
        answer = Answer(
            id=str(uuid.uuid4()),
            question_id=question.id,
            ai_answer="No documents have been indexed yet. Please upload and index documents first.",
            confidence=0.0,
            is_answerable="no",
            status=AnswerStatus.GENERATED.value,
        )
        db.add(answer)
        db.commit()
        db.refresh(answer)
        return answer
    
    # Build prompt
    prompt = build_answer_prompt(question.question_text, chunks)
    
    # Parallel generation (run both in parallel using asyncio)
    loop = asyncio.get_event_loop()
    
    # Run LLM calls in thread pool to not block
    answer_a_future = loop.run_in_executor(None, call_llm, prompt, settings.answer_temp_a)
    answer_b_future = loop.run_in_executor(None, call_llm, prompt, settings.answer_temp_b)
    
    answer_a, answer_b = await asyncio.gather(answer_a_future, answer_b_future)
    
    # Merge answers
    merge_prompt = build_merge_prompt(question.question_text, answer_a, answer_b)
    final_answer_raw = call_llm(merge_prompt, settings.merge_temp)
    
    # Parse the final answer
    parsed = parse_answer_response(final_answer_raw)
    
    # Extract citations
    citations = extract_citations(parsed["text"], chunks)
    
    # Create answer record
    answer = Answer(
        id=str(uuid.uuid4()),
        question_id=question.id,
        ai_answer=parsed["text"],
        answer_variant_a=answer_a,
        answer_variant_b=answer_b,
        citations=citations,
        confidence=parsed["confidence"],
        is_answerable=parsed["is_answerable"],
        status=AnswerStatus.GENERATED.value,
    )
    
    db.add(answer)
    db.commit()
    db.refresh(answer)
    
    return answer


async def generate_answers_for_project(project, db: Session) -> Dict[str, Any]:
    """Generate answers for all questions in a project."""
    results = {
        "project_id": project.id,
        "total": len(project.questions),
        "generated": 0,
        "errors": [],
    }
    
    for question in project.questions:
        try:
            await generate_answer(question, db)
            results["generated"] += 1
        except Exception as e:
            results["errors"].append({
                "question_id": question.id,
                "error": str(e),
            })
    
    return results

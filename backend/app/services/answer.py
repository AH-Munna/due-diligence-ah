"""Answer generation service with parallel generation + merge strategy."""
import asyncio
import uuid
import re
from typing import List, Dict, Any, Optional, Callable
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


def extract_and_format_citations(answer_text: str, context_chunks: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, str]]]:
    """
    Extract citation references from the answer text and replace them with numbered references.
    Returns the formatted text and the list of citations.
    """
    citations = []
    seen = set()
    citation_map = {}  # Maps "doc_name_pageX" to citation number
    
    # First pass: collect all citations from chunks that are mentioned
    for chunk in context_chunks:
        doc_name = chunk["metadata"].get("doc_name", "")
        page = chunk["metadata"].get("page", 0)
        citation_key = f"{doc_name}_p{page}"
        
        if citation_key not in seen:
            # Check if this source is mentioned in the answer
            if doc_name.lower() in answer_text.lower() or f"page {page}" in answer_text.lower():
                citation_num = len(citations) + 1
                citations.append({
                    "doc_id": chunk["metadata"].get("doc_id", ""),
                    "doc_name": doc_name,
                    "page": page,
                    "text": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                    "chunk_id": chunk["id"],
                    "num": citation_num,
                })
                citation_map[citation_key] = citation_num
                seen.add(citation_key)
    
    # Second pass: replace inline citations with numbered references
    formatted_text = answer_text
    
    # Pattern to match [Source: DocName, Page X] style citations
    citation_pattern = r'\[Source:\s*([^,\]]+),?\s*Page\s*(\d+)\]'
    
    def replace_citation(match):
        doc_name = match.group(1).strip()
        page = int(match.group(2))
        citation_key = f"{doc_name}_p{page}"
        
        if citation_key in citation_map:
            return f"[{citation_map[citation_key]}]"
        else:
            # Add new citation if not found
            citation_num = len(citations) + 1
            citations.append({
                "doc_id": "",
                "doc_name": doc_name,
                "page": page,
                "text": "",
                "chunk_id": "",
                "num": citation_num,
            })
            citation_map[citation_key] = citation_num
            return f"[{citation_num}]"
    
    formatted_text = re.sub(citation_pattern, replace_citation, formatted_text, flags=re.IGNORECASE)
    
    # Also handle simpler patterns like (Source: DocName, Page X) or just Page X references
    formatted_text = re.sub(r'\(Source:\s*[^,]+,?\s*Page\s*\d+\)', '', formatted_text)
    
    return formatted_text, citations


async def generate_answer(
    question: Question, 
    db: Session, 
    progress_callback: Optional[Callable[[str], None]] = None
) -> Answer:
    """
    Generate an answer using the parallel + merge strategy:
    1. Retrieve relevant chunks
    2. Generate two answers in parallel with different temperatures
    3. Merge the answers with a third LLM call
    """
    def emit_progress(msg: str):
        if progress_callback:
            progress_callback(msg)
    
    # Check if answer already exists
    existing = db.query(Answer).filter(Answer.question_id == question.id).first()
    if existing:
        return existing
    
    emit_progress("retrieving_context")
    
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
    
    emit_progress("parallel_generation")
    
    # Parallel generation (run both in parallel using asyncio)
    loop = asyncio.get_event_loop()
    
    # Run LLM calls in thread pool to not block
    answer_a_future = loop.run_in_executor(None, call_llm, prompt, settings.answer_temp_a)
    answer_b_future = loop.run_in_executor(None, call_llm, prompt, settings.answer_temp_b)
    
    answer_a, answer_b = await asyncio.gather(answer_a_future, answer_b_future)
    
    emit_progress("merging_answers")
    
    # Merge answers
    merge_prompt = build_merge_prompt(question.question_text, answer_a, answer_b)
    final_answer_raw = call_llm(merge_prompt, settings.merge_temp)
    
    emit_progress("formatting_citations")
    
    # Parse the final answer
    parsed = parse_answer_response(final_answer_raw)
    
    # Extract and format citations
    formatted_text, citations = extract_and_format_citations(parsed["text"], chunks)
    
    # Create answer record
    answer = Answer(
        id=str(uuid.uuid4()),
        question_id=question.id,
        ai_answer=formatted_text,
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


async def generate_answers_for_project_with_progress(project, db: Session):
    """
    Generator that yields progress updates while generating answers.
    Used for SSE streaming.
    """
    total = len(project.questions)
    generated = 0
    errors = []
    
    for i, question in enumerate(project.questions):
        q_num = i + 1
        
        def make_progress_callback(question_num):
            def callback(stage: str):
                pass  # Progress is tracked at question level for SSE
            return callback
        
        yield {
            "type": "progress",
            "question_num": q_num,
            "total": total,
            "stage": "starting",
            "question_preview": question.question_text[:50] + "..."
        }
        
        try:
            # Progress stages
            yield {
                "type": "progress",
                "question_num": q_num,
                "total": total,
                "stage": "retrieving_context",
                "question_preview": question.question_text[:50] + "..."
            }
            
            # Check for existing answer
            existing = db.query(Answer).filter(Answer.question_id == question.id).first()
            if existing:
                yield {
                    "type": "progress",
                    "question_num": q_num,
                    "total": total,
                    "stage": "cached",
                    "question_preview": question.question_text[:50] + "..."
                }
                generated += 1
                continue
            
            # Retrieve chunks
            chunks = search_chunks(question.question_text, n_results=8)
            
            if not chunks:
                answer = Answer(
                    id=str(uuid.uuid4()),
                    question_id=question.id,
                    ai_answer="No documents indexed.",
                    confidence=0.0,
                    is_answerable="no",
                    status=AnswerStatus.GENERATED.value,
                )
                db.add(answer)
                db.commit()
                generated += 1
                continue
            
            # Parallel generation
            yield {
                "type": "progress",
                "question_num": q_num,
                "total": total,
                "stage": "parallel_generation",
                "question_preview": question.question_text[:50] + "..."
            }
            
            prompt = build_answer_prompt(question.question_text, chunks)
            loop = asyncio.get_event_loop()
            
            answer_a_future = loop.run_in_executor(None, call_llm, prompt, settings.answer_temp_a)
            answer_b_future = loop.run_in_executor(None, call_llm, prompt, settings.answer_temp_b)
            
            answer_a, answer_b = await asyncio.gather(answer_a_future, answer_b_future)
            
            # Merging
            yield {
                "type": "progress",
                "question_num": q_num,
                "total": total,
                "stage": "merging",
                "question_preview": question.question_text[:50] + "..."
            }
            
            merge_prompt = build_merge_prompt(question.question_text, answer_a, answer_b)
            final_answer_raw = call_llm(merge_prompt, settings.merge_temp)
            
            # Parse and format
            parsed = parse_answer_response(final_answer_raw)
            formatted_text, citations = extract_and_format_citations(parsed["text"], chunks)
            
            # Save
            answer = Answer(
                id=str(uuid.uuid4()),
                question_id=question.id,
                ai_answer=formatted_text,
                answer_variant_a=answer_a,
                answer_variant_b=answer_b,
                citations=citations,
                confidence=parsed["confidence"],
                is_answerable=parsed["is_answerable"],
                status=AnswerStatus.GENERATED.value,
            )
            db.add(answer)
            db.commit()
            
            yield {
                "type": "progress",
                "question_num": q_num,
                "total": total,
                "stage": "complete",
                "question_preview": question.question_text[:50] + "..."
            }
            
            generated += 1
            
        except Exception as e:
            errors.append({
                "question_id": question.id,
                "error": str(e),
            })
            yield {
                "type": "error",
                "question_num": q_num,
                "total": total,
                "error": str(e)
            }
    
    # Final result
    yield {
        "type": "complete",
        "project_id": project.id,
        "total": total,
        "generated": generated,
        "errors": errors
    }


async def generate_answers_for_project(project, db: Session) -> Dict[str, Any]:
    """Generate answers for all questions in a project (non-streaming)."""
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

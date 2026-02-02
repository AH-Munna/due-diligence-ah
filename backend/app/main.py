from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import documents, projects, answers

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered questionnaire answering system",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(answers.router, prefix="/api/answers", tags=["Answers"])


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.on_event("startup")
async def startup():
    """Initialize database and vector store on startup."""
    from app.models.database import init_db
    init_db()

# Due Diligence AH

AI-powered questionnaire answering system with document indexing, citation tracking, and review workflow.

## Project Structure

```
due-diligence-ah/
├── backend/          # FastAPI + Python
│   ├── app/          # Application code
│   └── data/         # Sample questions
└── frontend/         # Next.js + Tailwind
```

## Quick Start

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Create `backend/.env`:
```
NVIDIA_API_KEY=your_key_here
DATABASE_URL=sqlite:///./due_diligence.db
```

## Tech Stack

- **Backend**: FastAPI, SQLite, ChromaDB, NVIDIA NIM API
- **Frontend**: Next.js 14, Tailwind CSS, TypeScript
- **LLM**: GLM4/Kimi-K2.5/DeepSeek via NVIDIA NIM

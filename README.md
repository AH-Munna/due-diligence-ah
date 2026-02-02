# Due Diligence AH 🔍

An AI-powered questionnaire answering system that automates due diligence by ingesting documents, generating answers with citations, and providing a human review workflow.

## 📹 Demo Video

**[Watch the Demo](https://docs.google.com/videos/d/11_X4iexdUSidM23EHlGBv7DLg570L9JiGrwJO0tm0d4/edit?usp=sharing)**

---

## 🎯 Project Overview

This system addresses the challenge of automating due diligence questionnaire responses by:

1. **Ingesting PDF documents** and extracting text with page-level metadata
2. **Indexing content** in a vector database for semantic search
3. **Generating answers** using an innovative 3-LLM parallel generation + merge strategy
4. **Extracting citations** with page references and source text
5. **Providing a review interface** for human oversight (confirm/reject/manual edit)

### Key Innovation: Parallel Answer Generation

Instead of a single LLM call, this system uses:

```
Question + Context
       ↓
  ┌────┴────┐
  ↓         ↓
LLM Call A  LLM Call B     (Different temperatures: 0.7 and 0.9)
(Temp 0.7)  (Temp 0.9)
  ↓         ↓
  └────┬────┘
       ↓
   Merge LLM              (Combines best of both, consolidates citations)
       ↓
   Final Answer
```

This approach improves answer quality by:
- Generating diverse perspectives with different temperature settings
- Merging the most accurate and complete information
- Consolidating and deduplicating citations

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                  (Next.js 16 + Tailwind)                     │
├─────────────────────────────────────────────────────────────┤
│  Dashboard  │  Documents  │  Projects  │  Q&A Review        │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST API
┌───────────────────────────┴─────────────────────────────────┐
│                        Backend                               │
│                        (FastAPI)                             │
├─────────────────────────────────────────────────────────────┤
│  Ingestion  │  Indexer   │  Answer Gen  │  Review Workflow  │
└───────┬────────────┬─────────────┬──────────────────────────┘
        │            │             │
   ┌────┴────┐  ┌────┴────┐  ┌─────┴─────┐
   │ SQLite  │  │ChromaDB │  │NVIDIA NIM │
   │Metadata │  │ Vectors │  │   API     │
   └─────────┘  └─────────┘  └───────────┘
```

---

## 💡 Technical Deep Dive

### Why CPU Usage Spikes During PDF Upload

When you upload a PDF document, several CPU-intensive operations occur:

1. **PDF Parsing (pdfplumber)**
   - Opens the PDF and extracts raw text with positional metadata
   - Processes each page to extract character-level positioning
   - Memory-intensive for large documents

2. **Text Chunking**
   - Splits extracted text into semantic chunks (~500 characters)
   - Preserves page boundaries and metadata for citation tracking
   - Overlapping windows ensure context preservation

3. **Embedding Generation (ChromaDB)**
   - ChromaDB's default embedding model generates dense vectors
   - Each chunk is converted to a 384-dimensional vector
   - This is the most CPU-intensive step (neural network inference)

4. **Vector Indexing**
   - HNSW (Hierarchical Navigable Small World) index construction
   - Enables fast approximate nearest neighbor search

For a 67-page PDF generating 328 chunks, this process takes ~60 seconds on a typical CPU.

### Database Design

**SQLite** stores relational metadata:
- Projects → Questions → Answers
- Document records with status tracking
- Review workflow state

**ChromaDB** stores:
- Document chunks as vectors (embedding representation)
- Metadata (doc_id, page, filename, chunk_index)
- Enables semantic similarity search for RAG

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- NVIDIA NIM API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your NVIDIA_API_KEY

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open http://localhost:3000

---

## 📁 Project Structure

```
due-diligence-ah/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── config.py         # Environment settings
│   │   ├── models/           # SQLAlchemy + Pydantic
│   │   ├── services/
│   │   │   ├── ingestion.py  # PDF processing
│   │   │   ├── indexer.py    # ChromaDB operations
│   │   │   └── answer.py     # 3-LLM generation logic
│   │   └── api/              # REST endpoints
│   ├── data/
│   │   └── sample_questions.json
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages
│   │   ├── lib/api.ts        # API client
│   │   └── components/
│   └── package.json
└── README.md
```

---

## ✅ Requirements Checklist

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Document ingestion | ✅ | pdfplumber + custom chunking |
| Vector indexing | ✅ | ChromaDB with persistent storage |
| Question parsing | ✅ | Pre-extracted sample questions |
| Answer generation | ✅ | 3-LLM parallel + merge strategy |
| Citation tracking | ✅ | Page-level refs with numbered citations |
| Confidence scores | ✅ | 0.0-1.0 extracted from LLM response |
| Review workflow | ✅ | Confirm/Reject/Manual edit |
| Frontend UI | ✅ | Next.js with SSE progress display |
| Real-time progress | ✅ | Server-Sent Events during generation |
| Markdown rendering | ✅ | react-markdown for rich text |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, Tailwind CSS, React Markdown |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Vector DB | ChromaDB (persistent mode) |
| Relational DB | SQLite |
| LLM | NVIDIA NIM API (glm4.7) |
| PDF Parsing | pdfplumber |

---

## 👤 About the Developer

**Ahsanul Haque Munna**  
Fullstack Developer | AI/LLM Enthusiast

- 📧 ahmunna.developer@gmail.com
- 🌐 [ah-munna.github.io](https://ah-munna.github.io)
- 💻 [github.com/ah-munna](https://github.com/ah-munna)

### Experience Highlights

- **Independent Software Developer** (2024-Present)
  - Developed custom automation suites using Python and Playwright
  - R&D on Large Language Models for self-conversational AI systems
  - Reduced client workflow time by 80% through process optimization

- **Fullstack Web Developer @ Nexis Limited** (2023-2024)
  - Built scalable SaaS applications with Django, React, Next.js
  - Optimized database schemas for high-traffic products
  - Integrated secure SSO solutions

### Technical Skills

- **Languages**: Python, TypeScript, JavaScript, SQL
- **Frameworks**: React, Next.js, Django, FastAPI, Tailwind CSS
- **LLM/AI**: OpenAI API, NVIDIA NIM, RAG systems, Vector databases
- **Competitive Programming**: ICPC Asia Regional, Codeforces

---

## 📝 License

MIT License - Built as a technical demonstration project.

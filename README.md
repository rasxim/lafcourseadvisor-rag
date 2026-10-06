# Lafayette Course Advisor

An AI academic advisor for Lafayette College students. Ask it about prerequisites, majors, minors, academic policies, or your own degree progress. It answers using the official 2025–26 course catalog, personalized with your degree audit.

---

## Origin

Lafayette College doesn't have a conversational tool for degree planning. The registrar's catalog is a 213-page PDF. Academic advisors are busy. Students planning four years of coursework are left manually cross-referencing dense tables of requirements.

I built this for myself. As a CS student (Class of 2029), I wanted to ask plain-English questions like *"What CS courses do I still need to graduate?"* and get answers grounded in the actual catalog, not made up by a general-purpose LLM.

The project became an exercise in building a production-quality RAG pipeline from scratch. That meant parsing a complex, structured PDF, designing retrieval that actually works on real academic questions, and evaluating it with automated metrics.

---

## What It Does

- Answers questions about course prerequisites, major and minor requirements, and academic policies
- Personalizes answers from an uploaded degree audit PDF (completed and in-progress courses, GPA, credits)
- Plans coursework: compares requirements against what you've taken and recommends only courses whose prerequisites you've met
- Picks the right requirement variant for your class year and degree (e.g. "Class of 2028 and Beyond", B.S. vs A.B.)
- Cites its sources inline, with page numbers you can open in the UI
- Declines off-topic questions

**Example queries:**
- *"What are the prerequisites for CS 203?"*
- *"What CS courses do I still need to graduate?"*
- *"Can I double major in CS and Economics? What would I need?"*
- *"What courses count toward the Documentary Storymaking minor?"*

---

## Architecture

```
PDF Catalog
    │
    ▼
LlamaParse (agentic tier)                         ingest.py  (one-time)
    │  213-page PDF → per-page markdown with headings and tables
    ▼
Heading-aware chunking → ChromaDB  (backend/chroma_db, ~2,500 chunks)
    │
    ▼
Unit builder                                      build_index.py
    │  Stitches chunks back into whole catalog units:
    │  1,448 courses · 125 programs · 101 policies · 44 departments
    │  Extracts course codes, prerequisites, department, program kind,
    │  degree (B.S./A.B.) and class-year window
    │  Re-embeds the chunks with ONNX MiniLM (no PyTorch) for semantic fallback
    ▼
backend/index/  (units.json + chroma/)
    │
    ▼
Rule-based router                                 retriever.py
    │  1. Course codes   → exact course lookup ("CS 203", "A&S 202")
    │  2. Program names  → the whole program, right class-year / degree variant
    │                      (handles shorthand: "cs", "econ", "math-econ")
    │  3. Planning       → student's major + target programs + relevant policies
    │                      + a prerequisite digest for every course they list
    │  4. Otherwise      → semantic search over chunks, expanded to parent units
    ▼
Gemini 3.6 Flash                                  rag.py
    │  Catalog sources are the only authority; profile is used only to personalize
    │  Inline [n] citations; refuses off-topic questions
    ▼
FastAPI  (main.py)  ──►  Next.js frontend  (frontend/)
```

---

## Key Design Decisions

### Why LlamaParse over a simple PDF parser?
The catalog mixes narrative prose, requirement tables, and course entries on the same pages. Libraries like `pdfplumber` or `PyMuPDF` lose the heading structure entirely. LlamaParse's agentic tier keeps the markdown hierarchy (`## CS 301 - Principles of Programming Languages`), and everything downstream is built on that hierarchy.

### Why whole units instead of fixed-size chunks?
The first version retrieved 800-character chunks with a bi-encoder and CrossEncoder reranker. It worked for single-course lookups but failed on the questions students actually ask. A major's requirements span several chunks, so the retriever returned fragments, the model missed requirements, and the class-year variants (*"Class of 2026 and 2027"* vs *"Class of 2028 and Beyond"*) got mixed together.

The catalog is already organized into natural units: one course, one program, one policy section. Indexing those whole units means the model always sees a complete requirement list or course entry, never a fragment.

### Why a rule-based router?
Most questions name something precise: a course code, a program, or "my major". A deterministic router resolves those exactly. It is faster and more reliable than embedding similarity, and you can debug it: each hit records *why* it was retrieved. Semantic search is only the fallback for questions that don't name anything.

### Why the prerequisite digest?
For planning questions, the model needs to know the prerequisites of every course in a program, not just the requirement list. The retriever attaches a compact one-line-per-course prerequisite reference, so the model can check eligibility without pulling in hundreds of full course descriptions.

### Why ONNX MiniLM instead of sentence-transformers?
Semantic search is now only a fallback, so a small model is enough. ChromaDB's bundled ONNX embedder removes PyTorch from the backend, which shrinks the deploy and speeds up cold starts.

### Why Gemini 3.6 Flash?
It's fast, and the free tier is enough for development and demo traffic. The system prompt is strict: every claim must come from the numbered catalog sources, and the student profile is never treated as evidence of what the requirements are.

---

## Evaluation

The pipeline is evaluated with [DeepEval](https://github.com/confident-ai/deepeval) across four metrics:

| Metric | What it measures |
|---|---|
| **Faithfulness** | Are all claims in the answer supported by the retrieved context? |
| **Answer Relevancy** | Does the answer actually address the question asked? |
| **Contextual Precision** | Is the retrieved context relevant to the question? |
| **Contextual Recall** | Does the retrieved context contain the information needed to answer? |

A golden dataset of 20 test cases covers exact course lookups, broad requirement queries, student-specific degree-gap queries, off-topic rejection, and edge cases (excluded courses, GPA calculation).

```bash
cd backend
pip install deepeval
python eval/quick_eval.py          # one query, all four metrics
python eval/run_eval.py            # full golden dataset (or pass test ids)
```

The judge is the app's own Gemini model. A full run makes 100+ requests, which is more than Gemini's free tier allows in a day.

---

## Stack

| Component | Technology |
|---|---|
| PDF parsing | LlamaParse (agentic tier) |
| Retrieval | Unit index + rule-based router (`units.json`) |
| Semantic fallback | ChromaDB with ONNX `all-MiniLM-L6-v2` |
| LLM | Gemini 3.6 Flash (`google-genai`) |
| Transcript parsing | LlamaParse + Gemini (structured JSON extraction) |
| Backend | FastAPI + Uvicorn |
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Evaluation | DeepEval |

---

## API

| Endpoint | Description |
|---|---|
| `GET /` | Health check |
| `POST /ask` | `{ query, student_profile }` → `{ answer, sources }` |
| `POST /upload-transcript` | Degree audit PDF (multipart) → student profile JSON |

---

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt

# backend/.env
GEMINI_API_KEY=your_key_here
LLAMA_CLOUD_API_KEY=your_key_here

uvicorn main:app --reload        # http://127.0.0.1:8000
```

The built index (`backend/index/`) is committed, so a fresh clone can run the API right away.

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` if the backend isn't at `http://127.0.0.1:8000`.

### Rebuilding the index

Only needed if you change how units are built:

```bash
cd backend
python build_index.py            # reads chroma_db/, writes index/
```

Re-parsing the catalog from the PDF (`python ingest.py`) needs the source PDF plus the ingestion dependencies in the root `requirements.txt` (sentence-transformers, langchain-text-splitters). The deployed backend doesn't need these.

---

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app: /ask, /upload-transcript
│   ├── rag.py               # Context assembly, system prompt, Gemini call
│   ├── retriever.py         # Unit index loading + rule-based router
│   ├── build_index.py       # Builds units.json and the chunk index
│   ├── ingest.py            # One-time PDF → LlamaParse → ChromaDB ingestion
│   ├── index/               # Built index used at runtime (committed)
│   ├── chroma_db/           # Original parsed chunks; source for build_index.py
│   ├── eval/
│   │   ├── common.py             # Gemini judge, metrics, pipeline runner
│   │   ├── golden_dataset.json   # 20 hand-written test cases
│   │   ├── quick_eval.py         # Single-query eval
│   │   └── run_eval.py           # Full eval suite
│   ├── requirements.txt
│   └── Procfile             # uvicorn main:app for deployment
└── frontend/
    └── app/
        ├── page.tsx
        └── components/      # Chat shell, sidebar, sources drawer, transcript upload
```

---

## About

Built by **Mohammad Rasim Omer**, CS BS, Lafayette College, Class of 2029.

> This project solves a real problem I have as a student. Every design decision was made to improve answer quality on actual academic queries, not to add complexity.

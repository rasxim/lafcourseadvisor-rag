# Lafayette Course Advisor

An AI-powered academic advisor that answers degree planning questions for Lafayette College students. Ask it anything — prerequisites, remaining requirements, major policies, course descriptions — and it reasons over the official 2025–26 course catalog combined with your personal degree audit.

---

## Origin

Lafayette College doesn't have a conversational tool for degree planning. The registrar's catalog is a 213-page PDF. Academic advisors are busy. Students planning four years of coursework are left manually cross-referencing dense tables of requirements.

I built this for myself. As a CS student (Class of 2029), I needed a way to ask plain-English questions like *"What CS courses do I still need to graduate?"* and get answers grounded in the actual catalog — not hallucinated by a general-purpose LLM.

The project became an exercise in building a production-quality RAG pipeline from scratch: parsing a complex structured PDF, designing a retrieval system that actually works on real academic queries, and evaluating it rigorously with automated metrics.

---

## What It Does

- Answers questions about course prerequisites, major requirements, graduation policies, and minors
- Personalizes answers using the student's degree audit (completed courses, GPA, credits, in-progress courses)
- Cites exact page numbers from the catalog for every factual claim
- Rejects off-topic questions cleanly
- Runs as a full-stack Streamlit web app

**Example queries:**
- *"What are the prerequisites for CS 301?"*
- *"What CS courses do I still need to graduate?"*
- *"What courses count toward the Documentary Storymaking minor?"*
- *"What are the prerequisites for MATH 182?"*

---

## Architecture

```
PDF Catalog
    │
    ▼
LlamaParse (Agentic Tier)
    │  Converts 213-page PDF to structured per-page markdown
    │  Preserves headings, tables, and course entries
    ▼
Chunking Pipeline (LangChain)
    │  MarkdownHeaderTextSplitter → splits on H1/H2/H3 boundaries
    │  RecursiveCharacterTextSplitter → max 800 chars, 150 overlap
    │  Page markers embedded for accurate page-number citation
    │  Heading context prepended to each chunk for richer embeddings
    ▼
ChromaDB (Local Vector Store)
    │  ~1,500 chunks, cosine similarity space
    │  Each chunk stores: text, heading path, page range, section type
    ▼
Retriever
    │  Query classification → routes to course_description / major_requirements / academic_policy
    │  Keyword search ($contains) for exact course codes — guarantees correct course is found
    │  Bi-encoder (BAAI/bge-small-en-v1.5) → semantic candidate retrieval
    │  CrossEncoder (BAAI/bge-reranker-base) → reranks candidates for precision
    │  Course code boost → +0.5 score for chunks containing the exact queried course
    ▼
Gemini 3.6 Flash (LLM)
    │  System prompt enforces: catalog-only sourcing, page citations, no hallucination
    │  Student profile injected only for student-specific queries
    ▼
Streamlit Frontend
```

---

## Key Design Decisions

### Why LlamaParse over a simple PDF parser?
The Lafayette catalog mixes narrative prose, requirement tables, and course entries on the same pages. Libraries like `pdfplumber` or `PyMuPDF` lose heading structure entirely. LlamaParse's agentic tier preserves the markdown hierarchy (`## CS 301 - Principles of Programming Languages`) which is what makes heading-boundary chunking possible.

### Why heading-boundary chunking?
Splitting by character count alone would cut a course entry mid-sentence, separating the prerequisite line from the course description. Splitting first on H2/H3 headings keeps each course entry intact as one logical unit, then the character splitter handles long sections.

### Why BAAI/bge-small-en-v1.5 + CrossEncoder reranking?
Single-stage dense retrieval (one embedding model) struggles with academic queries where the query mentions a course code but the chunk body doesn't repeat it — the heading carries the course code, not the paragraph. The two-stage approach fixes this: the bi-encoder casts a wide net, the CrossEncoder reads both query and chunk jointly to accurately score relevance.

### Why keyword search for course codes?
`"What are the prerequisites for CS 303?"` — the semantically similar chunk is titled `## CS 303 - Theory of Computation` but its body starts with `"An introduction to formal models..."`. Cosine similarity between the query and this chunk is low. A `$contains: "CS 303"` search on document text directly finds the right chunk regardless of semantic drift. Course code queries now always return the correct course entry.

### Why Gemini 3.6 Flash?
Fast, free tier, 1,500 requests/day — sufficient for a development and demo workload. The system prompt is strict: the model must base every claim on the retrieved catalog excerpts, cite page numbers, and refuse to infer policies not present in context.

---

## Evaluation

The pipeline is evaluated with [DeepEval](https://github.com/confident-ai/deepeval) across four metrics:

| Metric | What it measures |
|---|---|
| **Faithfulness** | Are all claims in the answer supported by the retrieved context? |
| **Answer Relevancy** | Does the answer actually address the question asked? |
| **Contextual Precision** | Are the retrieved chunks relevant to the question? |
| **Contextual Recall** | Does the retrieved context contain the information needed to answer? |

A golden dataset of 18 test cases covers: exact course lookups, broad requirement queries, student-specific degree gap queries, off-topic rejection, and edge cases (excluded courses, GPA calculation).

---

## Stack

| Component | Technology |
|---|---|
| PDF Parsing | LlamaParse (Agentic Tier) |
| Chunking | LangChain `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter` |
| Vector Store | ChromaDB (local persistent) |
| Bi-Encoder | `BAAI/bge-small-en-v1.5` (Sentence Transformers) |
| Cross-Encoder | `BAAI/bge-reranker-base` |
| LLM | Gemini 3.6 Flash (`google-genai`) |
| Frontend | Streamlit |
| Evaluation | DeepEval |

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Add your API keys to .env
GEMINI_API_KEY=your_key_here
LLAMA_CLOUD_API_KEY=your_key_here

# Ingest the catalog (builds ChromaDB)
python ingest.py

# Run the app
streamlit run app.py
```

The `chroma_db/` directory is committed to the repo — you can skip `ingest.py` and run the app directly if you clone the repo.

---

## Project Structure

```
├── ingest.py          # PDF parsing, chunking, embedding, ChromaDB ingestion
├── retriever.py       # Query classification, bi-encoder + CrossEncoder retrieval
├── rag.py             # Prompt assembly, Gemini LLM call, public ask() interface
├── app.py             # Streamlit frontend
├── student_profile.json   # Degree audit (completed courses, requirements, GPA)
├── eval/
│   ├── golden_dataset.json    # 18 hand-written test cases
│   ├── quick_eval.py          # Single-query eval (~5 API calls)
│   └── run_eval.py            # Full eval suite
└── chroma_db/         # Pre-built vector store (committed for convenience)
```

---

## About

Built by **Mohammad Rasim Omer** — CS BS, Lafayette College, Class of 2029.

> This project solves a real problem I have as a student. Every design decision was made to improve answer quality on actual academic queries, not to add complexity.

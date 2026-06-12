"""
ingest.py — PDF -> LlamaParse (agentic, items) -> chunks -> ChromaDB

LlamaParse returns structured page items (HeadingItem, TextItem, TableItem...).
We group items under each course-header heading into one chunk per course entry.
Non-course pages (policy, requirements) are kept as whole-page chunks.
"""

import re
import os
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer
from llama_cloud import LlamaCloud
from llama_cloud.types import HeadingItem, TableItem

load_dotenv()
_embedder     = SentenceTransformer("all-MiniLM-L6-v2")
_llama_client = LlamaCloud(api_key=os.environ["LLAMA_CLOUD_API_KEY"])

PDF_PATH        = "Lafayette-College_25-26-VA.pdf"
ITEMS_CACHE     = "output_items.json"   # cached so re-runs skip re-parsing
CHROMA_DIR      = "./chroma_db"
COLLECTION_NAME = "lafayette_catalog"

# ---------------------------------------------------------------------------
# TOC page ranges -> section_type
# ---------------------------------------------------------------------------
TOC_RANGES = [
    (1,   30,  "academic_policy",    None),
    (31,  76,  "major_requirements", None),
    (77, 213,  "course_description", None),
]

# Course code pattern for metadata tagging: "CS 301 - Computer Systems (1)"
COURSE_HEADING_RE = re.compile(
    r'^([A-Z]{2,4})\s(\d{3}[A-Z]?)\s[-–]?\s*.+\(\d\)'
)

PREREQ_RE = re.compile(r'[Pp]rerequisites?[:\s]+([A-Z]{2,4}\s\d{3}[A-Z]?)')
COREQ_RE  = re.compile(r'[Cc]orequisites?[:\s]+([A-Z]{2,4}\s\d{3}[A-Z]?)')
PERM_RE   = re.compile(r'[Ii]nstructor\s+permission', re.IGNORECASE)


def section_type_for_page(page_num: int) -> tuple[str, str | None]:
    for start, end, stype, dept in TOC_RANGES:
        if start <= page_num <= end:
            return stype, dept
    return "course_description", None


def is_toc_text(text: str) -> bool:
    return text.count("...") >= 5


def extract_metadata(text: str, section_type: str, department: str | None, page: int) -> dict:
    course_code = None
    # Strip markdown heading markers (##, **, etc.) before matching
    first_line = re.sub(r'^#+\s*', '', text.split('\n')[0].strip())
    first_line = re.sub(r'\*+', '', first_line).strip()
    m = COURSE_HEADING_RE.match(first_line)
    if m:
        dept_code    = m.group(1)
        num          = m.group(2)
        course_code  = f"{dept_code} {num}"
        department   = dept_code
        section_type = "course_description"

    prereq = (PREREQ_RE.search(text) or None) and PREREQ_RE.search(text).group(1)
    coreq  = (COREQ_RE.search(text)  or None) and COREQ_RE.search(text).group(1)

    return {
        "section_type":          section_type,
        "department":            department or "",
        "course_code":           course_code or "",
        "prereq":                prereq or "",
        "coreq":                 coreq or "",
        "instructor_permission": bool(PERM_RE.search(text)),
        "page":                  page,
    }


# ---------------------------------------------------------------------------
# Step 1 — Parse PDF with LlamaParse (cached as JSON)
# ---------------------------------------------------------------------------

def parse_pdf_to_items() -> list[dict]:
    """
    Returns a list of page dicts:
      { "page_number": int, "items": [ {"type": str, "md": str, ...}, ... ] }
    Cached to ITEMS_CACHE after first call.
    """
    import json

    cache = Path(ITEMS_CACHE)
    if cache.exists():
        print(f"Using cached items: {ITEMS_CACHE}")
        return json.loads(cache.read_text(encoding="utf-8"))

    print("Uploading PDF to LlamaParse...")
    with open(PDF_PATH, "rb") as f:
        file_obj = _llama_client.files.create(
            file=(Path(PDF_PATH).name, f), purpose="parse"
        )

    print("Parsing (tier=agentic) — this takes a few minutes...")
    result = _llama_client.parsing.parse(
        file_id=file_obj.id,
        tier="agentic",
        version="latest",
        expand=["items"],
    )

    # Serialise to plain dicts for caching
    pages_data = []
    for page in result.items.pages:
        if not page.success:
            print(f"  Warning: page {page.page_number} failed: {page.error}")
            continue
        page_items = []
        for item in page.items:
            entry = {"type": item.type, "md": item.md}
            if isinstance(item, HeadingItem):
                entry["level"] = item.level
                entry["value"] = item.value
            if isinstance(item, TableItem):
                entry["csv"] = item.csv
            page_items.append(entry)
        pages_data.append({"page_number": page.page_number, "items": page_items})

    cache.write_text(
        json.dumps(pages_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Parsed {len(pages_data)} pages -> cached to {ITEMS_CACHE}")
    return pages_data


# ---------------------------------------------------------------------------
# Step 2 — Build chunks from structured items
# ---------------------------------------------------------------------------

def build_chunks(pages_data: list[dict]) -> list[dict]:
    """
    For course-description pages: group all items that belong to a course entry
    (from its ## heading to just before the next ## heading) into one chunk.

    For all other pages: emit one chunk per page (policy / requirements prose).
    """
    all_chunks = []

    for page in pages_data:
        page_num     = page["page_number"]
        items        = page["items"]
        section_type, department = section_type_for_page(page_num)

        # Flatten page to plain text for TOC detection
        page_text = "\n".join(i["md"] for i in items).strip()
        if not page_text or is_toc_text(page_text):
            continue

        if section_type == "course_description":
            # Each H2 heading starts a new chunk — trust LlamaParse agentic structure
            current_lines: list[str] = []

            def flush(lines: list[str]):
                text = "\n".join(lines).strip()
                if not text:
                    return
                meta = extract_metadata(text, section_type, department, page_num)
                all_chunks.append({"text": text, "metadata": meta})

            for item in items:
                if item["type"] == "heading" and item.get("level") == 2:
                    flush(current_lines)
                    current_lines = [item["md"]]
                else:
                    current_lines.append(item["md"])

            flush(current_lines)

        else:
            # Policy / requirements page — one chunk for the whole page
            meta = extract_metadata(page_text, section_type, department, page_num)
            all_chunks.append({"text": page_text, "metadata": meta})

    # Deduplicate by exact text
    seen    = set()
    deduped = []
    for chunk in all_chunks:
        if chunk["text"] not in seen:
            seen.add(chunk["text"])
            deduped.append(chunk)

    print(f"Total chunks: {len(all_chunks)} -> {len(deduped)} after dedup")
    return deduped


# ---------------------------------------------------------------------------
# Step 3 — Embed and store in ChromaDB
# ---------------------------------------------------------------------------

def ingest():
    pages_data = parse_pdf_to_items()
    chunks     = build_chunks(pages_data)

    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    print("Embedding and storing chunks...")
    batch_size = 64

    for i in range(0, len(chunks), batch_size):
        batch      = chunks[i : i + batch_size]
        texts      = [c["text"]     for c in batch]
        metas      = [c["metadata"] for c in batch]
        ids        = [f"chunk_{i + j}" for j in range(len(batch))]
        embeddings = _embedder.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metas,
        )
        stored = i + len(batch)
        if stored % 200 == 0 or stored == len(chunks):
            print(f"  Stored {stored}/{len(chunks)} chunks")

    print(f"Ingest complete. {collection.count()} chunks in ChromaDB.")


if __name__ == "__main__":
    ingest()

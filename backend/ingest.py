import re
import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import chromadb
from llama_cloud import LlamaCloud
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

load_dotenv()

PDF_PATH        = "Lafayette-College_25-26-VA.pdf"
CHROMA_DIR      = "./chroma_db"
COLLECTION_NAME = "lafayette_catalog"

TOC_RANGES = [
    (1,   31,  "academic_policy"),
    (32,  76,  "major_requirements"),
    (77, 213,  "course_description"),
]

_PAGE_MARKER_RE = re.compile(r"<!-- PAGE (\d+) -->")

# Prefer headings → blank lines → list boundaries → sentences → spaces.
# Operates within a header section, so h4/h5 are the deepest headings seen here.
_MD_SEPARATORS = [
    "\n## ", "\n### ", "\n#### ", "\n##### ",
    "\n\n",
    "\n- ", "\n* ", "\n1. ",
    ". ",
    " ",
    "",
]


def section_for_page(page_num: int) -> str:
    for start, end, section in TOC_RANGES:
        if start <= page_num <= end:
            return section
    return "other"


def parse_pdf() -> list[dict]:
    """Send PDF to LlamaParse (agentic tier) and return per-page markdown."""
    client   = LlamaCloud()
    uploaded = client.files.create(file=PDF_PATH, purpose="parse")
    result   = client.parsing.parse(
        file_id=uploaded.id,
        tier="agentic",
        version="latest",
        expand=["markdown"],
    )
    return [
        {"page_number": i + 1, "markdown": p.markdown}
        for i, p in enumerate(result.markdown.pages)
    ]


def _merge_pages(pages: list[dict]) -> str:
    """Combine all pages into one markdown string with embedded page markers."""
    parts = []
    for p in pages:
        parts.append(f"<!-- PAGE {p['page_number']} -->")
        parts.append(p["markdown"])
    return "\n\n".join(parts)


def _page_breaks_in(text: str) -> list[tuple[int, int]]:
    """Return sorted (char_offset, page_num) pairs for every marker in text."""
    return [(m.start(), int(m.group(1))) for m in _PAGE_MARKER_RE.finditer(text)]


def _page_at_offset(breaks: list[tuple[int, int]], offset: int, default: int) -> int:
    """Page number active at `offset` — the last marker at or before the offset."""
    page = default
    for pos, num in breaks:
        if pos <= offset:
            page = num
        else:
            break
    return page


def _remove_markers(text: str) -> str:
    return _PAGE_MARKER_RE.sub("", text).strip()


def _heading_in_text(heading: str, text: str) -> bool:
    """True if the first line of text is already this heading (with any # prefix)."""
    first_line = text.lstrip().split("\n")[0]
    return re.sub(r"^#+\s*", "", first_line).strip() == heading


def _enrich_text(chunk_text: str, meta: dict) -> str:
    """Build embedding text with labeled headings prepended, skipping any already
    present in the chunk to avoid duplication."""
    h1 = meta.get("parent_h1", "")
    h2 = meta.get("parent_h2", "")
    h3 = meta.get("parent_h3", "")
    parts = []
    if h1 and not _heading_in_text(h1, chunk_text):
        parts.append(f"Section: {h1}")
    if h2 and not _heading_in_text(h2, chunk_text):
        parts.append(f"Subsection: {h2}")
    if h3 and not _heading_in_text(h3, chunk_text):
        parts.append(f"Topic: {h3}")
    parts.append(chunk_text)
    return "\n".join(parts)


def _heading_path(meta: dict) -> str:
    return " > ".join(
        h for h in (meta.get("parent_h1", ""), meta.get("parent_h2", ""), meta.get("parent_h3", ""))
        if h
    )


def build_chunks(pages: list[dict]) -> list[dict]:
    merged = _merge_pages(pages)

    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[
        ("#",   "parent_h1"),
        ("##",  "parent_h2"),
        ("###", "parent_h3"),
    ])
    header_docs = header_splitter.split_text(merged)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        add_start_index=True,
        separators=_MD_SEPARATORS,
    )

    chunks = []
    # Tracks the page active at the START of each header section.
    # Updated once per header section (not per fine chunk) — far less fragile.
    current_entry_page = 1

    for header_doc in header_docs:
        text   = header_doc.page_content
        breaks = _page_breaks_in(text)
        entry  = current_entry_page

        # split_documents propagates header metadata and adds start_index per chunk
        fine_docs = char_splitter.create_documents(
            [text],
            metadatas=[dict(header_doc.metadata)],
        )

        for fine_doc in fine_docs:
            # start_index is the byte offset of this chunk within the header section
            start_idx  = fine_doc.metadata.pop("start_index", 0)
            end_idx    = start_idx + len(fine_doc.page_content)
            start_page = _page_at_offset(breaks, start_idx, entry)
            end_page   = _page_at_offset(breaks, end_idx,   start_page)

            clean_text = _remove_markers(fine_doc.page_content)
            if not clean_text:
                continue

            heading_meta = {
                "parent_h1": fine_doc.metadata.get("parent_h1", ""),
                "parent_h2": fine_doc.metadata.get("parent_h2", ""),
                "parent_h3": fine_doc.metadata.get("parent_h3", ""),
            }
            meta = {
                **heading_meta,
                "heading_path": _heading_path(heading_meta),
                "start_page":   start_page,
                "end_page":     end_page,
                "section":      section_for_page(start_page),
            }
            chunks.append({
                "text":     clean_text,
                "embed":    _enrich_text(clean_text, meta),
                "metadata": meta,
            })

        # Advance entry page to the last page seen in this header section
        if breaks:
            current_entry_page = breaks[-1][1]

    return chunks


def ingest():
    print("Parsing PDF with LlamaParse (agentic)...")
    pages = parse_pdf()
    print(f"  {len(pages)} pages")

    chunks = build_chunks(pages)
    print(f"  {len(chunks)} chunks")

    db = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        db.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = db.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch  = chunks[i : i + batch_size]
        texts  = [c["embed"]    for c in batch]
        embeds = [c["embed"]    for c in batch]
        metas  = [c["metadata"] for c in batch]
        ids    = [f"chunk_{i + j}" for j in range(len(batch))]
        vecs   = model.encode(embeds, normalize_embeddings=True).tolist()
        collection.add(ids=ids, documents=texts, metadatas=metas, embeddings=vecs)
        print(f"  Stored {min(i + len(batch), len(chunks))}/{len(chunks)}")

    print(f"Done — {collection.count()} chunks in ChromaDB.")


if __name__ == "__main__":
    ingest()

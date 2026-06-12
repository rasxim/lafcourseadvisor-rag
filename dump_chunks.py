"""
dump_chunks.py — Export all ChromaDB chunks to a readable markdown file.
Usage: python dump_chunks.py [section_type]
       python dump_chunks.py major_requirements
       python dump_chunks.py  (dumps all)
"""

import sys
import chromadb

CHROMA_DIR      = "./chroma_db"
COLLECTION_NAME = "lafayette_catalog"
OUTPUT_FILE     = "chunks_dump.md"

def dump(filter_section: str | None = None):
    client     = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    total = collection.count()
    print(f"Collection has {total} chunks total.")

    results = collection.get(include=["documents", "metadatas"])
    docs    = results["documents"]
    metas   = results["metadatas"]
    ids     = results["ids"]

    pairs = list(zip(ids, docs, metas))

    if filter_section:
        pairs = [(i, d, m) for i, d, m in pairs if m.get("section_type") == filter_section]
        print(f"Filtered to {len(pairs)} chunks with section_type='{filter_section}'.")

    # Sort by page number then chunk id
    pairs.sort(key=lambda x: (x[2].get("page", 0), x[0]))

    lines = []
    lines.append(f"# Chunks Dump\n")
    lines.append(f"Total shown: {len(pairs)} / {total}\n")
    if filter_section:
        lines.append(f"Filter: `section_type = {filter_section}`\n")
    lines.append("---\n")

    for chunk_id, doc, meta in pairs:
        section  = meta.get("section_type", "")
        dept     = meta.get("department", "")
        course   = meta.get("course_code", "")
        page     = meta.get("page", "?")
        prereq   = meta.get("prereq", "")
        coreq    = meta.get("coreq", "")

        header_parts = [f"**{chunk_id}**", f"page {page}", f"`{section}`"]
        if course:
            header_parts.append(f"course: `{course}`")
        elif dept:
            header_parts.append(f"dept: `{dept}`")
        if prereq:
            header_parts.append(f"prereq: {prereq}")
        if coreq:
            header_parts.append(f"coreq: {coreq}")

        lines.append(" | ".join(header_parts))
        lines.append("\n")
        lines.append(doc.strip())
        lines.append("\n\n---\n")

    output = "\n".join(lines)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Written to {OUTPUT_FILE}")

if __name__ == "__main__":
    section_filter = sys.argv[1] if len(sys.argv) > 1 else None
    dump(section_filter)

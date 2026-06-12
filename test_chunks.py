from ingest import build_chunks

chunks = build_chunks("Lafayette-College_25-26-VA.pdf")
print(f"Total chunks: {len(chunks)}")
print("--- Sample chunks ---")
for c in chunks[:10]:
    code = c["metadata"]["course_code"] or "(none)"
    stype = c["metadata"]["section_type"]
    page = c["metadata"]["page"]
    print(f"[{stype}] page={page} course={code}")
    print(c["text"][:200])
    print()

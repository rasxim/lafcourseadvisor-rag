from ingest import build_chunks

chunks = build_chunks("Lafayette-College_25-26-VA.pdf")

cs_req = [
    c for c in chunks
    if (
        c["metadata"]["department"] == "CS"
        or "computer science" in c["text"].lower()
        or "cs major" in c["text"].lower()
    )
    and c["metadata"]["section_type"] in ("major_requirements", "academic_policy", "ccs_policy")
]

print(f"Found {len(cs_req)} CS requirement chunks\n")
for c in cs_req[:10]:
    print(f"[page {c['metadata']['page']}] [{c['metadata']['section_type']}]")
    print(c["text"][:500])
    print("-" * 60)

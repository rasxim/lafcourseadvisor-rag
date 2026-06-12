import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path="./chroma_db")
col    = client.get_collection("lafayette_catalog")
embed  = SentenceTransformer("all-MiniLM-L6-v2")

print(f"Total chunks in DB: {col.count()}")
print()

# 1. How many chunks have department=CS?
cs_chunks = col.get(where={"department": {"$eq": "CS"}}, include=["metadatas", "documents"])
print(f"Chunks with department=CS: {len(cs_chunks['ids'])}")
for meta, doc in zip(cs_chunks["metadatas"][:5], cs_chunks["documents"][:5]):
    print(f"  {meta}")
    print(f"  {doc[:120]}")
    print()

# 2. How many chunks have section_type=course_description AND department=CS?
cs_course_chunks = col.get(
    where={"$and": [{"department": {"$eq": "CS"}}, {"section_type": {"$eq": "course_description"}}]},
    include=["metadatas", "documents"]
)
print(f"Chunks with department=CS AND section_type=course_description: {len(cs_course_chunks['ids'])}")
for meta, doc in zip(cs_course_chunks["metadatas"][:3], cs_course_chunks["documents"][:3]):
    print(f"  {meta}")
    print(f"  {doc[:120]}")
    print()

# 3. Raw similarity search for "prerequisites for CS 301" with NO filter
query = "What are the prerequisites for CS 301?"
qvec  = embed.encode(query).tolist()
raw   = col.query(query_embeddings=[qvec], n_results=5, include=["documents", "metadatas", "distances"])
print(f"Top 5 raw results for: '{query}'")
for doc, meta, dist in zip(raw["documents"][0], raw["metadatas"][0], raw["distances"][0]):
    print(f"  score={1-dist:.3f} | {meta}")
    print(f"  {doc[:150]}")
    print()

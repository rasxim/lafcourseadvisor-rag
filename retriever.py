"""
retriever.py — Query classification + filtered ChromaDB retrieval.
Test this in isolation before wiring up rag.py.
"""

import re
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()
_embedder = SentenceTransformer("all-MiniLM-L6-v2")
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "lafayette_catalog"
SIMILARITY_THRESHOLD = 0.25

# ---------------------------------------------------------------------------
# Query classifier
# ---------------------------------------------------------------------------
COURSE_CODE_RE = re.compile(r'\b([A-Z]{2,4})\s(\d{3})\b')
BROAD_KEYWORDS = re.compile(
    r'\b(require|need|still|major|graduate|how many|credit|fulfill|satisfy|'
    r'complete|remaining|left|policy|policies|writing|distribution|CCS|core)\b',
    re.IGNORECASE,
)


def classify_query(query: str) -> tuple[str, int]:
    """Return (query_type, k): 'narrow' k=3 or 'broad' k=10."""
    if COURSE_CODE_RE.search(query):
        return "narrow", 3
    if BROAD_KEYWORDS.search(query):
        return "broad", 10
    return "broad", 10  # safe default


def extract_intent(query: str) -> dict:
    """Pull department hint and section_type hint from query text."""
    dept = None
    m = COURSE_CODE_RE.search(query)
    if m:
        dept = m.group(1)

    section_type = None
    q_lower = query.lower()
    if any(w in q_lower for w in ("prereq", "prerequisite", "coreq")):
        section_type = "course_description"
    elif any(w in q_lower for w in ("major require", "degree require", "what does the", "what courses")):
        section_type = "major_requirements"
    elif any(w in q_lower for w in ("writing requirement", "ccs", "distribution", "core curriculum")):
        section_type = "ccs_policy"
    elif dept and not section_type:
        section_type = "course_description"

    return {"department": dept, "section_type": section_type}


def build_where_filter(intent: dict) -> dict | None:
    """Build a ChromaDB $and/$eq metadata filter from intent hints."""
    conditions = []
    if intent.get("department"):
        conditions.append({"department": {"$eq": intent["department"]}})
    if intent.get("section_type"):
        conditions.append({"section_type": {"$eq": intent["section_type"]}})

    if len(conditions) == 0:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------
class Retriever:
    def __init__(self):
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = client.get_collection(COLLECTION_NAME)

    def retrieve(self, query: str) -> list[dict]:
        """
        Returns list of {text, metadata, score} dicts.
        Returns [] if top similarity < SIMILARITY_THRESHOLD (similarity gate).
        """
        query_type, k = classify_query(query)
        intent = extract_intent(query)
        where = build_where_filter(intent)

        query_embedding = _embedder.encode(query).tolist()

        kwargs = dict(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        if where:
            kwargs["where"] = where

        try:
            results = self.collection.query(**kwargs)
        except Exception:
            # If filtered query returns nothing, fall back to unfiltered
            kwargs.pop("where", None)
            results = self.collection.query(**kwargs)

        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]

        if not docs:
            return []

        # ChromaDB cosine distance → similarity: similarity = 1 - distance
        top_similarity = 1 - distances[0]
        if top_similarity < SIMILARITY_THRESHOLD:
            return []

        return [
            {"text": doc, "metadata": meta, "score": round(1 - dist, 4)}
            for doc, meta, dist in zip(docs, metas, distances)
        ]


# ---------------------------------------------------------------------------
# Quick manual test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    r = Retriever()
    test_queries = [
        "What courses do i need for the Documentary StoryMaking minor?",
        "What courses does the CS major require to graduate?",
        "What counts toward the writing requirement?",
        "What is the weather today?",  # should be rejected by similarity gate
    ]
    for q in test_queries:
        print(f"\nQ: {q}")
        chunks = r.retrieve(q)
        if not chunks:
            print("  [No relevant results — below similarity threshold]")
        else:
            for c in chunks:
                print(f"  [{c['score']:.3f}] ({c['metadata'].get('course_code') or c['metadata'].get('section_type')}) {c['text'][:120]}...")

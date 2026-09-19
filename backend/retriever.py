import re
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, CrossEncoder

load_dotenv()

CHROMA_DIR      = "./chroma_db"
COLLECTION_NAME = "lafayette_catalog"

# Bi-encoder similarity (cosine) below this is dropped before reranking
BI_ENCODER_THRESHOLD = 0.10
# CrossEncoder score below this is dropped after reranking
RERANK_THRESHOLD = 0.0
# Small bonus added to rerank score when chunk contains the exact queried course code
COURSE_BOOST = 0.5

COURSE_CODE_RE = re.compile(r"\b[A-Z]{2,5}\s\d{3}\b", re.IGNORECASE)

def _load_bi_encoder():
    return SentenceTransformer("BAAI/bge-small-en-v1.5")

def _load_cross_encoder():
    return CrossEncoder("BAAI/bge-reranker-base")

try:
    import streamlit as st
    _bi_encoder    = st.cache_resource(_load_bi_encoder)()
    _cross_encoder = st.cache_resource(_load_cross_encoder)()
except ImportError:
    _bi_encoder    = _load_bi_encoder()
    _cross_encoder = _load_cross_encoder()

# Keywords used to classify query intent and decide whether to apply a section filter.
# Deliberately specific so a single hit is meaningful.
_SECTION_KEYWORDS: dict[str, frozenset] = {
    "academic_policy": frozenset({
        "probation", "suspension", "dismissal", "withdrawal", "incomplete",
        "pass/fail", "attendance", "absence", "academic integrity",
        "honor code", "academic standing", "academic warning",
        "gpa", "grade appeal", "satisfactory progress", "unsatisfactory",
    }),
    "major_requirements": frozenset({
        "major", "minor", "concentration", "graduation", "elective",
        "declare", "degree requirement", "plan of study",
        "common course of study", "core curriculum", "credits to graduate",
    }),
    "course_description": frozenset({
        "prerequisite", "prereq", "credit hours", "instructor permission",
        "cross-listed", "offered", "course description",
    }),
}

# How many candidates to pull from Chroma per query type
_CANDIDATE_K: dict[str, int] = {
    "academic_policy":    15,
    "major_requirements": 20,
    "course_description": 10,
}

# How many chunks to return after reranking per query type
_RETURN_K: dict[str, int] = {
    "academic_policy":    5,
    "major_requirements": 8,
    "course_description": 5,
}


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def _embed(text: str) -> list[float]:
    return _bi_encoder.encode(text, normalize_embeddings=True).tolist()


# ---------------------------------------------------------------------------
# Query classification
# ---------------------------------------------------------------------------

def classify_query(query: str) -> tuple[int, str | None]:
    """Return (n_candidates, section_filter).

    A metadata filter is only applied when one section clearly dominates;
    otherwise the full collection is searched.
    """
    q = query.lower()

    # Course code is an unambiguous signal — always filter
    if COURSE_CODE_RE.search(query):
        return _CANDIDATE_K["course_description"], "course_description"

    scores: dict[str, int] = {
        section: sum(1 for kw in kws if kw in q)
        for section, kws in _SECTION_KEYWORDS.items()
    }

    top_section = max(scores, key=scores.get)
    top_score   = scores[top_section]

    if top_score == 0:
        return 20, None  # no signal — search everything

    # Apply filter only when the winning section is unambiguous
    second_best = sorted(scores.values(), reverse=True)[1]
    if top_score <= second_best:
        return 20, None  # tied — don't narrow the search

    return _CANDIDATE_K[top_section], top_section


# ---------------------------------------------------------------------------
# Reranking
# ---------------------------------------------------------------------------

def _rerank(query: str, candidates: list[dict]) -> list[dict]:
    """Score all candidates with the CrossEncoder and sort descending."""
    pairs  = [(query, c["text"]) for c in candidates]
    scores = _cross_encoder.predict(pairs)
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)


def _boost_course_codes(query: str, candidates: list[dict]) -> list[dict]:
    """Add COURSE_BOOST to any chunk that contains the exact course code from the query."""
    codes = {m.upper() for m in COURSE_CODE_RE.findall(query)}
    if not codes:
        return candidates
    for c in candidates:
        if any(code in c["text"].upper() for code in codes):
            c["rerank_score"] += COURSE_BOOST
    return candidates


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def _deduplicate(chunks: list[dict]) -> list[dict]:
    """Keep only the highest-scoring chunk per (heading_path, start_page, end_page).

    Chunks arrive sorted by score, so the first occurrence of each key is kept.
    Falls back to page range alone when heading_path is absent.
    """
    seen:   set = set()
    result: list[dict] = []
    for c in chunks:
        meta = c["metadata"]
        hp   = meta.get("heading_path", "")
        sp   = meta.get("start_page",   0)
        ep   = meta.get("end_page",     0)
        key  = (hp, sp, ep) if hp else (sp, ep)
        if key not in seen:
            seen.add(key)
            result.append(c)
    return result


def _format_result(c: dict) -> dict:
    """Flatten frequently-accessed metadata fields to the top level."""
    meta = c["metadata"]
    return {
        "text":         c["text"],
        "score":        round(c["rerank_score"], 4),
        "start_page":   meta.get("start_page",   0),
        "end_page":     meta.get("end_page",     0),
        "heading_path": meta.get("heading_path", ""),
        "section":      meta.get("section",      ""),
        "metadata":     meta,
    }


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class Retriever:
    def __init__(self):
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = client.get_collection(COLLECTION_NAME)

    def _keyword_fetch(self, course_code: str) -> list[dict]:
        """Fetch chunks that literally contain the course code string."""
        try:
            results = self.collection.query(
                query_embeddings=[_embed(course_code)],
                n_results=20,
                where_document={"$contains": course_code},
                include=["documents", "metadatas", "distances"],
            )
            docs      = results["documents"][0]
            metas     = results["metadatas"][0]
            distances = results["distances"][0]
            return [{"text": doc, "metadata": meta} for doc, meta, dist in zip(docs, metas, distances)]
        except Exception:
            return []

    def retrieve(self, query: str) -> list[dict]:
        n_candidates, section = classify_query(query)
        vec = _embed(query)

        # For exact course code queries, combine keyword hits with semantic hits
        course_codes = COURSE_CODE_RE.findall(query)
        keyword_candidates: list[dict] = []
        if course_codes:
            for code in course_codes:
                normalized = re.sub(r"\s+", " ", code.upper().strip())
                keyword_candidates.extend(self._keyword_fetch(normalized))

        kwargs: dict = dict(
            query_embeddings=[vec],
            n_results=n_candidates,
            include=["documents", "metadatas", "distances"],
        )
        if section:
            kwargs["where"] = {"section": section}

        results   = self.collection.query(**kwargs)
        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]

        # Merge keyword hits with semantic hits (keyword hits bypass bi-encoder threshold)
        seen_texts: set[str] = set()
        candidates: list[dict] = []
        for c in keyword_candidates:
            if c["text"] not in seen_texts:
                seen_texts.add(c["text"])
                candidates.append(c)

        if not docs:
            if not candidates:
                return []
        else:
            # 1. Pre-filter semantic hits by bi-encoder threshold
            for doc, meta, dist in zip(docs, metas, distances):
                if (1 - dist) >= BI_ENCODER_THRESHOLD and doc not in seen_texts:
                    seen_texts.add(doc)
                    candidates.append({"text": doc, "metadata": meta})

        if not candidates:
            return []

        # 2. Rerank with CrossEncoder
        candidates = _rerank(query, candidates)

        # 3. Boost exact course code matches, then re-sort by updated score
        candidates = _boost_course_codes(query, candidates)
        if section == "course_description" or COURSE_CODE_RE.search(query):
            candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

        # 4. Discard clearly irrelevant chunks
        candidates = [c for c in candidates if c["rerank_score"] >= RERANK_THRESHOLD]
        if not candidates:
            return []

        # 5. Return top-k, then deduplicate
        return_k   = _RETURN_K.get(section, 8)
        candidates = _deduplicate(candidates[:return_k])

        return [_format_result(c) for c in candidates]

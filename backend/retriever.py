"""Unit-based retrieval for the Lafayette catalog.

The catalog is indexed as whole units (one course, one program, one policy
section) instead of fixed-size fragments. A rule-based router reads the query
and decides which units to fetch:

  course codes  ->  exact course lookup ("prereq of CS 203")
  program names ->  the whole program, right degree / class-year variant
  planning      ->  student's major + target programs + relevant policies
                    + a prerequisite digest for every course those programs list
  no match      ->  semantic search over small chunks, expanded to parent units

Build the index first with `python build_index.py`.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

INDEX_DIR = Path(__file__).parent / "index"
CHUNK_COLLECTION = "catalog_chunks"

SEMANTIC_MIN_SIM = 0.25
MAX_DIGEST_LINES = 70
MAX_SEMANTIC_CHARS = 5000

COURSE_CODE_RE = re.compile(r"\b([A-Za-z]{2,5})\s?-?(\d{3})\b")

_STOPWORDS = {"and", "of", "the", "in", "a", "an", "s", "for", "to", "with"}

# Student shorthand -> catalog vocabulary
_ALIASES = {
    "cs": ["computer", "science"],
    "compsci": ["computer", "science"],
    "econ": ["economics"],
    "econs": ["economics"],
    "math": ["mathematics"],
    "maths": ["mathematics"],
    "bio": ["biology"],
    "chem": ["chemistry"],
    "biochem": ["biochemistry"],
    "psych": ["psychology"],
    "neuro": ["neuroscience"],
    "ece": ["electrical", "computer", "engineering"],
    "cheme": ["chemical", "engineering"],
    "mech": ["mechanical"],
    "wgss": ["women", "gender", "sexuality", "studies"],
    "gov": ["government", "law"],
    "govt": ["government", "law"],
    "phil": ["philosophy"],
    "philo": ["philosophy"],
    "env": ["environmental"],
    "enviro": ["environmental"],
    "stats": ["statistics"],
    "ir": ["international", "affairs"],
    "anthro": ["anthropology"],
    "soc": ["sociology"],
    "poli": ["government"],
}

_KIND_PREFERENCE = ["major", "program", "concentration", "certificate", "minor"]

_PLANNING_RE = re.compile(
    r"\b(should i|plan|planning|next semester|next year|schedule|double major|"
    r"second major|two majors|another major|add (?:a |an )?(?:major|minor)|"
    r"switch|on track|still need|remaining|left to take|graduate|graduation|"
    r"can i take|eligible|what (?:classes|courses) (?:do|should|can) i)\b",
    re.IGNORECASE,
)

_STUDENT_RE = re.compile(
    r"\b(my|i|i'm|i've|me|am i|do i|have i|will i|can i)\b", re.IGNORECASE
)

# Policy sections pulled in when a planning question touches them
_POLICY_TRIGGERS = [
    (re.compile(r"double major|second major|two majors|another major|add (?:a |an )?major", re.I), "THE MAJOR"),
    (re.compile(r"\bminor|certificate", re.I), "THE MINOR/CERTIFICATE"),
    (re.compile(r"graduat", re.I), "GRADUATION REQUIREMENTS"),
    (re.compile(r"overload|how many courses|course load|too many courses", re.I), "Course Overloads"),
    (re.compile(r"pass/fail|pass fail", re.I), "Pass/Fail Option"),
]


# ---------------------------------------------------------------------------
# Index loading
# ---------------------------------------------------------------------------

def _tokens(text: str) -> list[str]:
    text = text.lower().replace("’", "'").replace("'", " ")
    out: list[str] = []
    for t in re.split(r"[^a-z0-9]+", text):
        if not t:
            continue
        out.extend(_ALIASES.get(t, [t]))
    return out


def _content_tokens(text: str) -> list[str]:
    return [t for t in _tokens(text) if t not in _STOPWORDS]


@dataclass
class Index:
    units: dict[str, dict]
    by_code: dict[str, list[str]]
    programs_by_base: dict[str, list[dict]]
    base_tokens: dict[str, list[str]]
    depts_by_base: dict[str, dict]
    policies_by_name: dict[str, list[dict]]
    dept_codes: set[str] = field(default_factory=set)


def _load_index() -> Index:
    raw = json.loads((INDEX_DIR / "units.json").read_text(encoding="utf-8"))
    units = {u["id"]: u for u in raw}

    by_code: dict[str, list[str]] = {}
    dept_codes: set[str] = set()
    programs_by_base: dict[str, list[dict]] = {}
    policies_by_name: dict[str, list[dict]] = {}
    depts: dict[str, dict] = {}

    for u in raw:
        if u["type"] == "course":
            for code in u["codes"]:
                by_code.setdefault(code, []).append(u["id"])
                dept_codes.add(code.split()[0])
        elif u["type"] == "program":
            programs_by_base.setdefault(u["base"], []).append(u)
        elif u["type"] == "policy":
            policies_by_name.setdefault(u["name"], []).append(u)
        elif u["type"] == "department":
            depts[" ".join(_content_tokens(u["name"]))] = u

    base_tokens = {b: _content_tokens(b) for b in programs_by_base}
    depts_by_base = {
        b: depts[" ".join(toks)] for b, toks in base_tokens.items() if " ".join(toks) in depts
    }
    return Index(units, by_code, programs_by_base, base_tokens, depts_by_base, policies_by_name, dept_codes)


# ---------------------------------------------------------------------------
# Query understanding
# ---------------------------------------------------------------------------

def extract_course_codes(query: str, dept_codes: set[str]) -> list[str]:
    codes = []
    for dept, num in COURSE_CODE_RE.findall(query):
        code = f"{dept.upper()} {num}"
        if dept.upper() in dept_codes and code not in codes:
            codes.append(code)
    return codes


def match_program_bases(text: str, idx: Index) -> list[tuple[str, int]]:
    """Return (base, end_position) for programs mentioned in the text.

    Longest names win: "math-econ" matches Mathematics and Economics, and the
    words it consumes don't also match Mathematics or Economics on their own.
    """
    toks = _content_tokens(text)
    positions: dict[str, list[int]] = {}
    for i, t in enumerate(toks):
        positions.setdefault(t, []).append(i)

    candidates = []
    for base, btoks in idx.base_tokens.items():
        if not btoks or any(t not in positions for t in btoks):
            continue
        firsts = [positions[t][0] for t in btoks]
        if max(firsts) - min(firsts) + 1 > len(btoks) + 2:
            continue
        candidates.append((len(btoks), base, set(firsts), max(firsts)))

    candidates.sort(key=lambda c: -c[0])
    consumed: set[int] = set()
    matched = []
    for _, base, pos, end in candidates:
        if pos <= consumed:
            continue
        consumed |= pos
        matched.append((base, end))
    return matched


def _wanted_degree(text: str) -> str:
    if re.search(r"\bb\.?\s?s\.?\b|bachelor of science", text, re.I):
        return "BS"
    if re.search(r"\ba\.?\s?b\.?\b|bachelor of arts", text, re.I):
        return "AB"
    return ""


def _wanted_kind(text: str, end_pos: int) -> str:
    toks = _content_tokens(text)
    near = toks[end_pos + 1 : end_pos + 4]
    for kind in ("minor", "major", "certificate", "concentration"):
        if kind in near:
            return kind
    has_minor, has_major = "minor" in toks, "major" in toks
    if has_minor and not has_major:
        return "minor"
    if has_major and not has_minor:
        return "major"
    return ""


def select_variants(variants: list[dict], kind: str, degree: str, year: int | None) -> list[dict]:
    """Pick the program variants that fit what the student asked for."""
    pool = [v for v in variants if v["kind"] == kind] if kind else []
    if not pool:
        for k in _KIND_PREFERENCE:
            pool = [v for v in variants if v["kind"] == k]
            if pool:
                break

    if degree:
        pool = [v for v in pool if v["degree"] == degree] or pool

    def fits(v: dict) -> bool:
        lo, hi = v["years_min"], v["years_max"]
        if lo is None:
            return True
        return lo <= year and (hi is None or year <= hi)

    if year:
        pool = [v for v in pool if fits(v)] or pool
    elif any(v["years_min"] is not None for v in pool):
        # No year known: prefer the current requirements (open-ended "and Beyond")
        pool = [v for v in pool if v["years_min"] is None or v["years_max"] is None] or pool
    return pool[:2]


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

@dataclass
class Hit:
    unit: dict
    reason: str
    score: float = 1.0


@dataclass
class Retrieval:
    intent: str
    hits: list[Hit]
    digest: str = ""
    digest_pages: tuple[int, int] = (0, 0)


class Retriever:
    def __init__(self):
        self.idx = _load_index()
        client = chromadb.PersistentClient(path=str(INDEX_DIR / "chroma"))
        self.chunks = client.get_collection(
            CHUNK_COLLECTION, embedding_function=embedding_functions.ONNXMiniLM_L6_V2()
        )

    # -- building blocks ---------------------------------------------------

    def _programs(self, text: str, year: int | None, degree: str, reason: str) -> list[Hit]:
        hits = []
        for base, end in match_program_bases(text, self.idx):
            chosen = select_variants(
                self.idx.programs_by_base[base], _wanted_kind(text, end), degree, year
            )
            hits.extend(Hit(v, reason) for v in chosen)
        return hits

    def _semantic(self, query: str, n: int, exclude: set[str]) -> list[Hit]:
        if n <= 0:
            return []
        res = self.chunks.query(query_texts=[query], n_results=15, include=["metadatas", "distances"])
        best: dict[str, float] = {}
        for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
            uid, sim = meta["unit_id"], 1 - dist
            if uid in exclude or sim < SEMANTIC_MIN_SIM:
                continue
            best[uid] = max(best.get(uid, 0.0), sim)
        ranked = sorted(best.items(), key=lambda kv: -kv[1])[:n]
        return [Hit(self.idx.units[uid], "semantic match", round(sim, 3)) for uid, sim in ranked]

    def _digest(self, hits: list[Hit], skip_codes: set[str]) -> tuple[str, tuple[int, int]]:
        """One line per course referenced by the included programs, with prereqs."""
        codes: list[str] = []
        for h in hits:
            if h.unit["type"] != "program":
                continue
            for code in extract_course_codes(h.unit["text"], self.idx.dept_codes):
                if code not in codes and code not in skip_codes:
                    codes.append(code)

        lines, pages = [], []
        for code in codes[:MAX_DIGEST_LINES]:
            for uid in self.idx.by_code.get(code, [])[:1]:
                u = self.idx.units[uid]
                line = f"{code} – {u['title']}"
                line += f". {u['prereq']}" if u["prereq"] else ". No prerequisite listed."
                lines.append(line)
                pages.append(u["start_page"])
        if not lines:
            return "", (0, 0)
        return "\n".join(lines), (min(pages), max(pages))

    # -- entry point -------------------------------------------------------

    def retrieve(self, query: str, profile: dict | None = None) -> Retrieval:
        profile = profile or {}
        year = profile.get("class_year") if isinstance(profile.get("class_year"), int) else None
        has_profile = bool(profile.get("major") or profile.get("completed_courses"))
        personal = has_profile and bool(_STUDENT_RE.search(query))
        planning = bool(_PLANNING_RE.search(query)) or personal
        intent = "planning" if planning else "lookup"

        hits: list[Hit] = []
        seen: set[str] = set()

        def add(new: list[Hit]) -> None:
            for h in new:
                if h.unit["id"] not in seen:
                    seen.add(h.unit["id"])
                    hits.append(h)

        # 1. Exact course lookups
        codes = extract_course_codes(query, self.idx.dept_codes)
        for code in codes:
            add([Hit(self.idx.units[uid], f"course code {code}") for uid in self.idx.by_code.get(code, [])])

        # 2. Programs named in the question. Course codes are blanked out first so
        # that "CS 203" doesn't also match the Computer Science program.
        def _blank(m: re.Match) -> str:
            return " " if m.group(1).upper() in self.idx.dept_codes else m.group(0)

        program_query = COURSE_CODE_RE.sub(_blank, query)
        add(self._programs(program_query, year, _wanted_degree(program_query), "program named in question"))

        # 3. Planning: the student's own major and the rules that govern combining programs
        if planning:
            if has_profile and profile.get("major"):
                major = str(profile["major"])
                own = self._programs(major, year, _wanted_degree(major), "student's current major")
                add([h for h in own if h.unit["kind"] == "major"] or own)

            for pattern, policy_name in _POLICY_TRIGGERS:
                if pattern.search(query):
                    add([Hit(u, "governing policy") for u in self.idx.policies_by_name.get(policy_name, [])])

            for h in list(hits):
                dept = self.idx.depts_by_base.get(h.unit.get("base", ""))
                if dept and len(dept["text"]) < 3500:
                    add([Hit(dept, "department overview")])

        # 4. Semantic fallback — none for a precise lookup that already hit exactly
        exact = bool(hits)
        n_sem = 0 if (exact and intent == "lookup") else (2 if exact else 4)
        add(self._semantic(query, n_sem, seen))

        retrieval = Retrieval(intent=intent, hits=hits)
        if planning:
            retrieval.digest, retrieval.digest_pages = self._digest(hits, set(codes))
        return retrieval

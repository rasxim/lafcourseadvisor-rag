"""Build the retrieval index from the chunks already stored in ChromaDB.

Produces, under backend/index/:
  units.json  - whole catalog units (one per course, program, policy section),
                reassembled from the original overlapping chunks.
  chroma/     - the original small chunks re-embedded with ChromaDB's bundled
                ONNX MiniLM model (no PyTorch), each tagged with its unit_id so a
                semantic hit can be expanded to its full parent unit.

Reads from the original `lafayette_catalog` collection. Nothing is re-parsed,
no API calls are made, and the source collection is not modified.

Run from backend/:  python build_index.py
"""

import html
import json
import re
import shutil
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

HERE = Path(__file__).parent
SOURCE_DIR = HERE / "chroma_db"
SOURCE_COLLECTION = "lafayette_catalog"
INDEX_DIR = HERE / "index"
CHUNK_COLLECTION = "catalog_chunks"

COURSE_HEADING_RE = re.compile(
    r"^(?P<dept>[A-Z][A-Z&]{1,4})\s+(?P<num>\d{3})(?:\s*-\s*(?P<num2>\d{3}))?\s*[-–]\s*(?P<title>.+?)\s*(?:\((?P<credits>[^)]*)\))?\s*$"
)
# Department header in the Courses section, e.g. "CS - COMPUTER SCIENCE". The
# parser sometimes fused it onto the first course ("CHEM - CHEMISTRY CHEM 101 - ...").
DEPT_HEADING_RE = re.compile(
    r"^(?P<code>[A-Z][A-Z&]{1,4})\s+-\s+(?P<name>[^a-z0-9]+?)\s*(?:$|(?=(?P=code)\s+\d{3}))"
)
PREFIX_RE = re.compile(r"^(Section|Subsection|Topic): ")


# ---------------------------------------------------------------------------
# Text reassembly
# ---------------------------------------------------------------------------

def strip_prefix(doc: str) -> str:
    lines = doc.split("\n")
    i = 0
    while i < len(lines) and PREFIX_RE.match(lines[i]):
        i += 1
    return "\n".join(lines[i:])


def stitch(a: str, b: str) -> str:
    """Join consecutive chunks, removing the splitter's overlap."""
    max_k = min(400, len(a), len(b))
    for k in range(max_k, 19, -1):
        if a.endswith(b[:k]):
            return a + b[k:]
    return a + "\n" + b


def clean_text(text: str) -> str:
    """Flatten HTML tables into pipe-separated rows and tidy whitespace."""
    t = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    t = re.sub(r"</t[dh]>\s*", " | ", t, flags=re.I)
    t = re.sub(r"</tr>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]*\|[ \t]*\n", "\n", t)          # trailing pipe on a row
    t = re.sub(r"^[ \t]*\|[ \t]*", "", t, flags=re.M)  # leading pipe
    t = re.sub(r"(\|\s*){2,}", "| ", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# ---------------------------------------------------------------------------
# Unit classification
# ---------------------------------------------------------------------------

def is_dept_header(h2: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", h2)
    return bool(letters) and h2 == h2.upper()


def parse_program(name: str, dept_context: str) -> dict:
    """Pull base name, kind, degree and class-year window out of a program heading."""
    kind = "program"
    low = name.lower()
    if "minor" in low:
        kind = "minor"
    elif "certificate" in low:
        kind = "certificate"
    elif "concentration" in low and "major" not in low:
        kind = "concentration"
    elif "major" in low:
        kind = "major"

    degree = ""
    if re.search(r"\bB\.\s?S\.", name):
        degree = "BS"
    elif re.search(r"\bA\.\s?B\.", name):
        degree = "AB"

    # Class-year window, e.g. "(Class of 2026 and 2027)", "(Class of 2028 and Beyond)"
    years_min, years_max = None, None
    m = re.search(r"Class(?:es)? of ([^)]*)", name)
    if m:
        years = [int(y) for y in re.findall(r"20\d\d", m.group(1))]
        if years:
            years_min = min(years)
            years_max = None if re.search(r"beyond", m.group(1), re.I) else max(years)

    base = re.sub(r"\(.*?\)", "", name)
    base = re.split(r",| Minor| Major| Joint| Certificate| Concentration| Requirements", base)[0]
    base = base.replace("Certificate in ", "").strip()
    if base.lower() in {"requirements", "course credit", ""} and dept_context:
        base = dept_context.title()

    return {
        "base": base,
        "kind": kind,
        "degree": degree,
        "years_min": years_min,
        "years_max": years_max,
    }


def unit_key(meta: dict) -> tuple[str, str]:
    """(type, name) identifying the unit a chunk belongs to."""
    h1 = meta.get("parent_h1", "")
    h2 = meta.get("parent_h2", "")
    h3 = meta.get("parent_h3", "")

    if h1 == "Courses":
        deepest = h3 or h2
        m = DEPT_HEADING_RE.match(deepest)
        if m and m.end() < len(deepest):
            deepest = deepest[m.end():]
        if COURSE_HEADING_RE.match(deepest):
            return "course", deepest
        return "other", f"Courses > {deepest}" if deepest else "Courses"
    if h1 == "Majors":
        if not h2:
            return "other", "Majors"
        if is_dept_header(h2):
            return "department", h2
        return "program", h2
    if h1 == "Academic Programs" and h2:
        return "policy", h2
    return "other", " > ".join(p for p in (h1, h2) if p) or "Catalog"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def main() -> None:
    src = chromadb.PersistentClient(path=str(SOURCE_DIR)).get_collection(SOURCE_COLLECTION)
    data = src.get(include=["documents", "metadatas"])
    rows = sorted(
        zip(data["ids"], data["documents"], data["metadatas"]),
        key=lambda r: int(r[0].split("_")[1]),
    )
    print(f"Read {len(rows)} chunks from '{SOURCE_COLLECTION}'")

    # Course code prefix -> department name, from the Courses section headers.
    # The parser dropped the MUS and PHYS headers entirely, so seed those.
    course_depts: dict[str, str] = {"MUS": "MUSIC", "PHYS": "PHYSICS"}
    for _, _, meta in rows:
        if meta.get("parent_h1") == "Courses":
            for h in (meta.get("parent_h2", ""), meta.get("parent_h3", "")):
                m = DEPT_HEADING_RE.match(h or "")
                if m:
                    course_depts[m.group("code")] = m.group("name")

    units: list[dict] = []
    chunk_unit: dict[str, str] = {}
    current = None
    seen_names: dict[str, int] = {}
    dept_context = ""

    for cid, doc, meta in rows:
        utype, name = unit_key(meta)
        if utype == "department":
            dept_context = name

        # A new unit starts whenever the key changes; a key that reappears later
        # (e.g. a generic "Requirements" heading) becomes a separate unit.
        if current is None or (current["type"], current["name"]) != (utype, name):
            n = seen_names.get(f"{utype}:{name}", 0)
            seen_names[f"{utype}:{name}"] = n + 1
            uid = f"{utype}:{name}" + (f"#{n + 1}" if n else "")
            current = {
                "id": uid,
                "type": utype,
                "name": name,
                "h1": meta.get("parent_h1", ""),
                "dept_context": dept_context,
                "start_page": meta.get("start_page", 0),
                "end_page": meta.get("end_page", 0),
                "raw": strip_prefix(doc),
            }
            units.append(current)
        else:
            current["raw"] = stitch(current["raw"], strip_prefix(doc))
            current["start_page"] = min(current["start_page"], meta.get("start_page", 0))
            current["end_page"] = max(current["end_page"], meta.get("end_page", 0))
        chunk_unit[cid] = current["id"]

    for u in units:
        u["text"] = clean_text(u.pop("raw"))
        if u["type"] == "course":
            m = COURSE_HEADING_RE.match(u["name"])
            # Keep numbers as zero-padded strings: "FYS 011" must stay "FYS 011".
            dept, num, num2 = m.group("dept"), m.group("num"), m.group("num2")
            codes = [f"{dept} {num}"]
            if num2 and 0 < int(num2) - int(num) <= 10:
                codes = [f"{dept} {n:03d}" for n in range(int(num), int(num2) + 1)]
            elif num2:
                codes.append(f"{dept} {num2}")
            u["codes"] = codes
            u["dept_context"] = course_depts.get(dept, "")
            u["title"] = m.group("title").strip()
            prereq = re.findall(r"((?:Prerequisites?|Corequisites?|Pre-?requisites?)[^.]*\.)", u["text"], re.I)
            u["prereq"] = " ".join(p.strip() for p in prereq)
        elif u["type"] == "program":
            u.update(parse_program(u["name"], u["dept_context"]))
            if u["kind"] == "program":
                head = u["text"][:400]
                if re.search(r"\bthe minor\b", head, re.I):
                    u["kind"] = "minor"
                elif re.search(r"\bthe (joint )?major\b", head, re.I):
                    u["kind"] = "major"

    by_type: dict[str, int] = {}
    for u in units:
        by_type[u["type"]] = by_type.get(u["type"], 0) + 1
    print("Units:", by_type)

    INDEX_DIR.mkdir(exist_ok=True)
    (INDEX_DIR / "units.json").write_text(json.dumps(units, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {INDEX_DIR / 'units.json'}")

    # Re-embed the small chunks with ONNX MiniLM for semantic fallback
    chroma_dir = INDEX_DIR / "chroma"
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    dst = chromadb.PersistentClient(path=str(chroma_dir))
    col = dst.create_collection(
        name=CHUNK_COLLECTION,
        embedding_function=embedding_functions.ONNXMiniLM_L6_V2(),
        metadata={"hnsw:space": "cosine"},
    )
    batch = 200
    for i in range(0, len(rows), batch):
        part = rows[i : i + batch]
        col.add(
            ids=[r[0] for r in part],
            documents=[clean_text(r[1]) for r in part],
            metadatas=[{"unit_id": chunk_unit[r[0]]} for r in part],
        )
        print(f"  embedded {min(i + batch, len(rows))}/{len(rows)}", flush=True)
    print(f"Done. '{CHUNK_COLLECTION}' holds {col.count()} chunks.")


if __name__ == "__main__":
    main()

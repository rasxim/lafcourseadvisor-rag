"""Parse an Ellucian Degree Works audit PDF into a student profile.

Degree Works audits are machine-generated with a clean text layer and the same
layout for every student, so this reads them directly with pypdf: no OCR, no
LLM calls, and the transcript never leaves the server.

The profile keeps the fields the frontend reads (name, major, class_year,
overall_gpa, completed_courses, in_progress_courses, credits) and adds the
audit's own "Still needed" lines under `requirements`, which is what makes
planning answers personal.
"""

import io
import re
from datetime import datetime

from pypdf import PdfReader


class AuditParseError(ValueError):
    """The file isn't a readable Degree Works audit."""


GRADE = r"(?:[A-D][+-]?|F|P|S|U|W|WF|WP|I|IP|TR|CR|NC|AU|NR)"
TERM = r"(?:Fall|Spring|Sum I{1,2}|Summer|Interim|Winter|J-?Term)\s+\d{4}"

COURSE_RE = re.compile(
    rf"^(?P<dept>[A-Z]{{2,5}})\s+(?P<num>\d{{3}}[A-Z]?)\s+(?P<title>.+?)\s+"
    rf"(?P<grade>{GRADE})\s+(?P<credits>\(?\d+(?:\.\d+)?\)?)\s+(?P<term>{TERM})"
    rf"(?:\s+\(?R\)?)?\s*$"
)
STATUS_BLOCK_RE = re.compile(r"^(?P<name>.+?)\s+(?P<status>INCOMPLETE|COMPLETE|IN-PROGRESS)$")
# Sections without a status badge, e.g. "Electives Credits applied: 1 Classes applied: 1"
PLAIN_BLOCK_RE = re.compile(r"^(?P<name>[A-Z][A-Za-z -]+?)\s+Credits applied:")
REQUIRED_RE = re.compile(
    r"^(?P<unit>Credits|Classes) required:\s*(?P<req>[\d.]+)\s+(?:Credits|Classes) applied:\s*(?P<app>[\d.]+)"
)
GPA_RE = re.compile(r"\bGPA:\s*([\d.]+)")
CATALOG_RE = re.compile(r"Catalog year:\s*(\d{4}-\d{4})")
HEADER_LABELS = ("Level", "Major", "Minor", "Concentration", "Class Year", "Expected Graduation Date", "Advisor")
HEADER_FIELD_RE = re.compile(
    rf"\b({'|'.join(HEADER_LABELS)})\s+(.+?)(?=\s{{2,}}(?:{'|'.join(HEADER_LABELS)})\b|\s*$)"
)

# Sections whose courses don't count toward the degree
UNCOUNTED_SECTIONS = ("insufficient", "not counted")


def _num(s: str) -> float | int:
    v = float(s.strip("()"))
    return int(v) if v.is_integer() else v


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _extract_lines(pdf_bytes: bytes) -> list[str]:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = [p.extract_text() or "" for p in reader.pages]
    except Exception as e:
        raise AuditParseError("Couldn't read that PDF.") from e

    lines = []
    for page in pages:
        for line in page.splitlines():
            # Running header repeated on every page
            if line.startswith("Lafayette College"):
                continue
            lines.append(line.rstrip())
    return lines


def _parse_header(lines: list[str]) -> dict:
    out: dict = {}
    for i, line in enumerate(lines):
        if m := re.match(r"^Student name\s+(.+)$", line):
            last, _, first = m.group(1).partition(",")
            out["name"] = _clean(f"{first} {last}")
        elif m := re.match(r"^Degree\s+(?!progress\b|in\b)(.+)$", line):
            out.setdefault("degree", _clean(m.group(1)))
        elif m := re.match(r"^Audit date\s+(\d{2}/\d{2}/\d{4})", line):
            out["audit_date"] = datetime.strptime(m.group(1), "%m/%d/%Y").date().isoformat()
        elif line.strip() == "Overall GPA" and i + 1 < len(lines):
            if re.fullmatch(r"\s*[\d.]+\s*", lines[i + 1]):
                out["overall_gpa"] = float(lines[i + 1])
        elif line.lstrip().startswith("Level "):
            for label, value in HEADER_FIELD_RE.findall(line):
                out[label] = _clean(value)
    return out


def _new_block(name: str, status: str | None) -> dict:
    return {"name": name, "status": status, "still_needed": [], "unmet": "", "notes": [], "courses": []}


def _parse_blocks(lines: list[str]) -> list[dict]:
    blocks: list[dict] = []
    block = None
    collector = None  # ("still", index) or ("unmet", None) while text may wrap onto the next line
    last_course = None

    for raw in lines:
        line = _clean(raw)
        if not line:
            collector = None
            continue

        if m := STATUS_BLOCK_RE.match(line):
            block = _new_block(m.group("name"), m.group("status"))
            blocks.append(block)
            collector = last_course = None
            continue
        if (m := PLAIN_BLOCK_RE.match(line)) and not REQUIRED_RE.match(line):
            block = _new_block(m.group("name"), None)
            blocks.append(block)
            collector = last_course = None
            continue
        if block is None:
            continue

        if m := REQUIRED_RE.match(line):
            unit = m.group("unit").lower()
            block[f"{unit}_required"] = _num(m.group("req"))
            block[f"{unit}_applied"] = _num(m.group("app"))
        if line.startswith(("Credits required", "Classes required", "Catalog year")):
            if m := GPA_RE.search(line):
                block["gpa"] = float(m.group(1))
            if m := CATALOG_RE.search(line):
                block["catalog_year"] = m.group(1)
            collector = None
            continue

        if line.startswith("Course Title Grade Credits"):
            collector = None
            continue

        if m := COURSE_RE.match(line):
            last_course = {
                "code": f"{m.group('dept')} {m.group('num')}",
                "title": _clean(m.group("title")),
                "grade": m.group("grade"),
                "credits": _num(m.group("credits")),
                "term": _clean(m.group("term")),
            }
            block["courses"].append(last_course)
            collector = None
            continue

        if line.startswith("Satisfied by:"):
            if last_course:
                last_course["note"] = "Satisfied by " + line.removeprefix("Satisfied by:").strip()
            collector = None
            continue

        if line.startswith("Still needed:"):
            block["still_needed"].append(line.removeprefix("Still needed:").strip())
            collector = ("still", len(block["still_needed"]) - 1)
            continue

        if line.startswith("Unmet conditions for this set of requirements:"):
            block["unmet"] = line.split(":", 1)[1].strip()
            collector = ("unmet", None)
            continue

        # Continuation of wrapped text. "Still needed" items always wrap until the
        # next structural line; the unmet-conditions sentence only continues when the
        # next line is clearly mid-sentence (starts lowercase).
        if collector and collector[0] == "still":
            idx = collector[1]
            block["still_needed"][idx] = _clean(f"{block['still_needed'][idx]} {line}")
            continue
        if collector and collector[0] == "unmet" and line[0].islower():
            block["unmet"] = _clean(f"{block['unmet']} {line}")
            continue

        collector = None
        if line.startswith(("Legend", "Disclaimer", "Blocks included")):
            block = None
            continue
        if block["notes"] and not block["notes"][-1].endswith((".", ":")):
            block["notes"][-1] += " " + line
        else:
            block["notes"].append(line)

    return blocks


def _requirement_text(item: str) -> str:
    """Make Degree Works shorthand readable: '@' means any course number."""
    item = re.sub(r"\b([A-Z]{2,5}) (\d{3}):(\d{3})", r"\1 \2-\3", item)
    item = item.replace("@ @", "any course").replace("@", "any")
    return _clean(item)


def parse_audit(pdf_bytes: bytes) -> dict:
    lines = _extract_lines(pdf_bytes)
    if not any("Degree Works" in l for l in lines) and not any(l.startswith("Student name") for l in lines):
        raise AuditParseError("This doesn't look like a Degree Works audit.")

    header = _parse_header(lines)
    blocks = _parse_blocks(lines)

    completed: dict[str, dict] = {}
    in_progress: dict[str, dict] = {}
    for b in blocks:
        if b["name"].lower().startswith(UNCOUNTED_SECTIONS):
            continue
        for c in b["courses"]:
            if c["grade"] == "IP":
                in_progress.setdefault(c["code"], {k: v for k, v in c.items() if k != "grade"})
            else:
                completed.setdefault(c["code"], c)

    if not completed and not in_progress:
        raise AuditParseError("No courses found in that audit.")

    degree_block = next((b for b in blocks if b["name"].startswith("Degree in")), None)
    major_gpa_block = next((b for b in blocks if re.search(r"Major.*GPA", b["name"])), None)

    requirements = []
    for b in blocks:
        if b["status"] in (None, "COMPLETE") or b is major_gpa_block:
            continue
        needed = [
            _requirement_text(s) for s in b["still_needed"]
            if s and not re.fullmatch(r"See .+ section", s)
        ]
        req = {"block": b["name"], "status": b["status"], "still_needed": needed}
        for key in ("credits_required", "credits_applied", "classes_required", "classes_applied"):
            if key in b:
                req[key] = b[key]
        if b["unmet"]:
            req["unmet_conditions"] = b["unmet"]
        if b["notes"]:
            req["notes"] = b["notes"]
        requirements.append(req)

    credits = {}
    if degree_block and "credits_required" in degree_block:
        credits = {
            "required": degree_block["credits_required"],
            "applied": degree_block["credits_applied"],
            "still_needed": max(0, degree_block["credits_required"] - degree_block["credits_applied"]),
        }

    grad = header.get("Expected Graduation Date")
    if grad:
        try:
            grad = datetime.strptime(grad, "%d-%b-%Y").date().isoformat()
        except ValueError:
            pass

    profile = {
        "name": header.get("name", ""),
        "degree": header.get("degree", ""),
        "major": header.get("Major", ""),
        "class_year": int(header["Class Year"]) if header.get("Class Year", "").isdigit() else None,
        "expected_graduation": grad,
        "advisor": header.get("Advisor", ""),
        "catalog_year": degree_block.get("catalog_year") if degree_block else None,
        "audit_date": header.get("audit_date"),
        "overall_gpa": header.get("overall_gpa"),
        "major_gpa": major_gpa_block.get("gpa") if major_gpa_block else None,
        "credits": credits,
        "completed_courses": list(completed.values()),
        "in_progress_courses": list(in_progress.values()),
        "requirements": requirements,
    }
    for label in ("Minor", "Concentration"):
        if header.get(label):
            profile[label.lower()] = header[label]
    return profile

"""
eval/audit_check.py — Check the Degree Works parser against a hand-verified answer key.

Scores every header field, every course (code, title, grade, credits, term) and
every "Still needed" line, and prints field-level accuracy.

Run from backend/:
    python eval/audit_check.py path/to/audit.pdf eval/audit_expected.json
    python eval/audit_check.py path/to/audit.pdf --save eval/audit_expected.json

--save writes the parser's current output as the key. Check it against the PDF by
hand before relying on it. Audits contain personal data, so keys are gitignored.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from audit_parser import parse_audit

HEADER_FIELDS = (
    "name", "degree", "major", "class_year", "expected_graduation", "advisor",
    "catalog_year", "audit_date", "overall_gpa", "major_gpa", "credits",
)


def _course_items(profile: dict) -> dict[str, dict]:
    items = {}
    for kind in ("completed_courses", "in_progress_courses"):
        for c in profile.get(kind, []):
            items[f"{kind}:{c['code']}"] = c
    return items


def _needed_items(profile: dict) -> set[str]:
    return {f"{r['block']}: {s}" for r in profile.get("requirements", []) for s in r["still_needed"]}


def compare(got: dict, want: dict) -> tuple[int, int, list[str]]:
    ok, total, misses = 0, 0, []

    def check(label: str, g, w) -> None:
        nonlocal ok, total
        total += 1
        if g == w:
            ok += 1
        else:
            misses.append(f"  {label}: got {g!r}, want {w!r}")

    for f in HEADER_FIELDS:
        check(f, got.get(f), want.get(f))

    got_courses, want_courses = _course_items(got), _course_items(want)
    for key, wc in want_courses.items():
        gc = got_courses.get(key)
        if gc is None:
            check(key, None, "present")
            continue
        for f in ("title", "grade", "credits", "term"):
            if f in wc:
                check(f"{key}.{f}", gc.get(f), wc[f])
    for key in got_courses.keys() - want_courses.keys():
        check(key, "present", None)  # extra course = a wrong extraction

    got_needed, want_needed = _needed_items(got), _needed_items(want)
    for item in want_needed:
        check(f"still needed: {item[:70]}", item in got_needed, True)
    for item in got_needed - want_needed:
        check(f"unexpected still needed: {item[:70]}", True, False)

    return ok, total, misses


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    profile = parse_audit(Path(args[0]).read_bytes())

    if args[1] == "--save":
        Path(args[2]).write_text(json.dumps(profile, indent=2), encoding="utf-8")
        print(f"Wrote {args[2]}. Verify it against the PDF before using it as a key.")
        sys.exit(0)

    want = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    ok, total, misses = compare(profile, want)
    print(f"Courses: {len(profile['completed_courses'])} completed, {len(profile['in_progress_courses'])} in progress")
    print(f"Still-needed items: {len(_needed_items(profile))}")
    print(f"Field accuracy: {ok}/{total} ({ok / total:.1%})")
    if misses:
        print("Mismatches:")
        print("\n".join(misses))
        sys.exit(1)

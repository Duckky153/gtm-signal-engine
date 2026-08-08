"""Detect E-Verify participation from the job postings themselves.

The government's employer-search tool blocks automated access, so this reads the
signal at its source instead: employers that use E-Verify almost always say so in
the legal boilerplate at the bottom of a posting ("This employer participates in
E-Verify"). A stated participation is strong evidence. Silence is not evidence of
absence — it goes in the "unknown, verify manually" bucket, never in "no".

Why it matters: with an EAD, no sponsorship is needed today. E-Verify enrolment is
what makes the 24-month STEM extension possible later.

    python3 -m hunt.everify
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .hunt import read_board, HERE

EVERIFY = re.compile(r"e-?verify", re.I)
US_LEGAL = re.compile(r"equal opportunity employer|EEO|FLSA|ADA|401\(k\)|W-?2", re.I)


def main() -> int:
    entries = []
    for line in (HERE / "candidates.txt").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "," in line:
            ats, token = line.split(",", 1)
            entries.append((ats.strip(), token.strip()))

    print(f"Reading {len(entries)} boards for E-Verify language...")
    rows = []
    with ThreadPoolExecutor(max_workers=14) as pool:
        for company, jobs, err in pool.map(lambda e: read_board(*e), entries):
            if err or not jobs:
                continue
            hits = sum(1 for j in jobs if EVERIFY.search(j["desc"] or ""))
            us_legal = sum(1 for j in jobs if US_LEGAL.search(j["desc"] or ""))
            rows.append({
                "company": company,
                "jobs": len(jobs),
                "everify_mentions": hits,
                "us_legal_mentions": us_legal,
                "status": "STATED" if hits else ("US-EMPLOYER" if us_legal else "UNKNOWN"),
            })

    rows.sort(key=lambda r: (r["status"] != "STATED", -r["everify_mentions"], r["company"]))
    (HERE / "everify.json").write_text(json.dumps(rows, indent=2))

    stated = [r for r in rows if r["status"] == "STATED"]
    print(f"\n{len(stated)} of {len(rows)} companies state E-Verify participation in postings\n")
    for r in stated:
        print(f"  CONFIRMED  {r['company'][:24]:<24} {r['everify_mentions']:>3}/{r['jobs']:<4} postings say E-Verify")
    print(f"\nWrote hunt/everify.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

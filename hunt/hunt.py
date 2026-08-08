"""Job hunt scanner.

Reads every candidate company's public job board, pulls FULL job descriptions,
and keeps only the roles that fit one specific person:

  - go-to-market / ops / growth / automation work (not software engineering)
  - United States, full-time, W-2 (contract roles are excluded, not ranked down)
  - a hiring process that screens on communication or portfolio, not live coding

The last one is the whole point. There is no data field for "we won't make you
LeetCode." But companies describe their process in the job description, so we
read the description and look for what they actually say.

    python3 -m hunt.hunt

Writes hunt/results.json and hunt/results.md
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = {"User-Agent": "gtm-signal-engine/1.0 (public job board reader)"}
TIMEOUT = 25

# --- what job is this -------------------------------------------------------

ROLE_PATTERNS = (
    r"\bgtm engineer", r"go[- ]to[- ]market engineer", r"\bgrowth engineer",
    r"gtm (systems|automation|operations|engineering)",
    r"revenue operations", r"\brevops\b", r"sales operations", r"marketing operations",
    r"\bmarketing ops\b", r"business operations", r"\bbizops\b",
    r"growth (marketer|marketing|manager|associate|analyst|operations)",
    r"demand generation", r"lifecycle marketing", r"marketing automation",
    r"automation (specialist|engineer|consultant|manager)",
    r"solutions (engineer|consultant|architect|specialist)",
    r"implementation (specialist|consultant|manager|engineer)",
    r"onboarding (specialist|manager)", r"customer success (engineer|operations)",
    r"sales engineer", r"forward deployed", r"technical account manager",
    r"data operations", r"list building", r"outbound (specialist|manager|strategist)",
)

# Roles that would drag him into a software-engineering loop. Hard exclude.
ROLE_EXCLUDE = (
    r"\b(software|backend|front[- ]?end|fullstack|full[- ]stack|platform|infrastructure|"
    r"security|mobile|ios|android|ml|machine learning|data|research|qa|firmware|embedded)\s+engineer",
    r"\bengineering manager\b", r"\bsoftware developer\b", r"\bdevops\b", r"\bsre\b",
    r"\bdata scientist\b", r"\bresearch scientist\b", r"\bproduct manager\b",
    r"\bdesigner\b", r"\brecruiter\b", r"\baccountant\b", r"\bcontroller\b",
    r"\bintern\b", r"\bvp\b", r"vice president", r"\bhead of\b", r"\bdirector\b",
    r"\bprincipal\b", r"\bstaff\b", r"\bsenior manager\b",
)

# --- how do they interview --------------------------------------------------

GREEN = {
    "loom": r"\bloom\b",
    "video intro": r"video (intro|introduction|submission|application)|record a (short )?video",
    "portfolio": r"\bportfolio\b|share (a|some) (work|examples)|something you'?ve built",
    "written/async": r"\basync(hronous)? (interview|process)|written (exercise|application)",
    "work sample": r"work sample|take[- ]home|paid (trial|project)",
    "no whiteboard": r"no whiteboard|no leetcode|without leetcode|no algorithm",
}
RED = {
    "live coding": r"live[- ]coding|coding (interview|screen|challenge|assessment|exercise)",
    "algorithms": r"\bleetcode\b|\balgorithms?\b.{0,24}\binterview|data structures",
    "system design": r"system design (interview|round)",
    "technical screen": r"technical (screen|assessment|interview loop)",
    "pair programming": r"pair[- ]programming",
}
SPONSOR_BLOCK = (
    r"(cannot|unable to|do not|will not|won'?t)\s+(offer|provide|sponsor)[^.]{0,60}"
    r"(sponsor|visa|immigration)",
    r"not\s+(able|eligible)\s+to\s+sponsor",
    r"no\s+visa\s+sponsorship",
)
EVERIFY = r"e-?verify"
CONTRACT = r"\b(1099|independent contractor|contract(or)? (role|position|basis)|freelance)\b"

US_HINT = re.compile(
    r"United States|USA|U\.S\.|Remote\s*[-–,]?\s*US|"
    r"\b(NY|CA|TX|MA|WA|IL|CO|GA|FL|NC|VA|PA|OH|MI|AZ|UT|OR|MN|TN|MD|NJ|DC)\b|"
    r"New York|San Francisco|Austin|Boston|Seattle|Chicago|Denver|Atlanta|Los Angeles|"
    r"Miami|Portland|Nashville|Philadelphia|Washington|Remote US|US Remote",
    re.I,
)
NON_US = re.compile(
    r"\b(India|Philippines|Poland|Ukraine|Brazil|Argentina|Mexico|Colombia|Germany|France|"
    r"Spain|Portugal|Netherlands|Ireland|London|United Kingdom|UK|Singapore|Australia|"
    r"Canada|Toronto|Vancouver|Israel|Tel Aviv|Japan|Korea|EMEA|APAC|LATAM|Dublin|Berlin|"
    r"Amsterdam|Paris|Bangalore|Hyderabad|Manila|Sydney|Copenhagen|Stockholm)\b",
    re.I,
)


def strip_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def get_json(url: str):
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def matches(patterns, text: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def find_flags(mapping: dict, text: str) -> list[str]:
    return [name for name, pattern in mapping.items() if re.search(pattern, text, re.I)]


def read_board(ats: str, token: str) -> tuple[str, list[dict], str | None]:
    """Return (company, jobs, error). Errors are returned, never swallowed."""
    try:
        if ats == "greenhouse":
            payload = get_json(
                f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
            )
            jobs = payload.get("jobs", [])
            company = (jobs[0].get("company_name") if jobs else None) or token
            return company, [
                {
                    "title": j.get("title", ""),
                    "location": (j.get("location") or {}).get("name", ""),
                    "url": j.get("absolute_url", ""),
                    "desc": strip_html(j.get("content", "")),
                    "employment": "",
                    "remote": None,
                }
                for j in jobs
            ], None
        payload = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}")
        jobs = payload.get("jobs", [])
        return token, [
            {
                "title": j.get("title", ""),
                "location": j.get("location", "") or "",
                "url": j.get("jobUrl", ""),
                "desc": j.get("descriptionPlain", "") or "",
                "employment": j.get("employmentType", "") or "",
                "remote": j.get("isRemote"),
            }
            for j in jobs
        ], None
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return token, [], str(exc)


def score(job: dict, green: list[str], red: list[str], board_size: int) -> int:
    """Higher = better fit for someone who must avoid a coding interview."""
    points = 0
    points += 26 * len(green)
    points -= 22 * len(red)
    if board_size <= 15:
        points += 26          # small company: the founder is the whole process
    elif board_size <= 45:
        points += 13
    if re.search(r"\bgtm engineer|go[- ]to[- ]market engineer|revenue operations|"
                 r"\brevops\b|automation|growth", job["title"], re.I):
        points += 14
    if job.get("remote"):
        points += 6
    return points


def main() -> int:
    entries = []
    for line in (HERE / "candidates.txt").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "," in line:
            ats, token = line.split(",", 1)
            entries.append((ats.strip(), token.strip()))

    print(f"Scanning {len(entries)} candidate job boards...")
    boards, failures = {}, []
    with ThreadPoolExecutor(max_workers=14) as pool:
        for company, jobs, err in pool.map(lambda e: read_board(*e), entries):
            if err:
                failures.append((company, err))
            elif jobs:
                boards[company] = jobs

    total_jobs = sum(len(v) for v in boards.values())
    print(f"  {len(boards)} live boards, {total_jobs} jobs, {len(failures)} dead tokens")

    hits, rejected = [], {"role": 0, "non_us": 0, "contract": 0, "sponsor": 0}
    for company, jobs in boards.items():
        size = len(jobs)
        for job in jobs:
            title = job["title"]
            if not matches(ROLE_PATTERNS, title) or matches(ROLE_EXCLUDE, title):
                rejected["role"] += 1
                continue
            where = f"{job['location']}"
            if NON_US.search(where) or not (US_HINT.search(where) or job.get("remote")):
                rejected["non_us"] += 1
                continue
            body = job["desc"]
            if job["employment"] and job["employment"].lower() not in ("fulltime", "full_time", "full time"):
                rejected["contract"] += 1
                continue
            if re.search(CONTRACT, body, re.I) and not re.search(r"full[- ]time employee|W-?2", body, re.I):
                rejected["contract"] += 1
                continue
            if matches(SPONSOR_BLOCK, body):
                rejected["sponsor"] += 1
                continue

            green = find_flags(GREEN, body)
            red = find_flags(RED, body)
            hits.append({
                "company": company,
                "title": title,
                "location": job["location"],
                "url": job["url"],
                "board_size": size,
                "remote": bool(job.get("remote")),
                "green_flags": green,
                "red_flags": red,
                "e_verify": bool(re.search(EVERIFY, body, re.I)),
                "score": score(job, green, red, size),
            })

    hits.sort(key=lambda h: (-h["score"], h["company"]))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "boards_live": len(boards),
        "boards_dead": len(failures),
        "jobs_scanned": total_jobs,
        "rejected": rejected,
        "matches": len(hits),
        "results": hits,
    }
    (HERE / "results.json").write_text(json.dumps(payload, indent=2))

    lines = ["# Job hunt results", "",
             f"Scanned **{total_jobs} jobs** across **{len(boards)} live boards**. "
             f"**{len(hits)}** survived every filter.", "",
             "Filters applied: go-to-market/ops role · United States · full-time W-2 · "
             "no blocking sponsorship language.", "",
             "| # | Company | Role | Where | Process signals | Board size | Score |",
             "|---|---------|------|-------|-----------------|-----------|-------|"]
    for i, h in enumerate(hits[:60], 1):
        sig = ", ".join(h["green_flags"]) or "—"
        if h["red_flags"]:
            sig += f" / RED: {', '.join(h['red_flags'])}"
        lines.append(f"| {i} | {h['company']} | [{h['title']}]({h['url']}) | "
                     f"{h['location'] or 'Remote'} | {sig} | {h['board_size']} | {h['score']} |")
    (HERE / "results.md").write_text("\n".join(lines) + "\n")

    clean = [h for h in hits if not h["red_flags"]]
    print(f"\n  {len(hits)} matching roles, {len(clean)} with NO coding-interview language")
    print(f"  rejected: {rejected}")
    print("\nTop 15:\n")
    for h in hits[:15]:
        flags = ",".join(h["green_flags"]) or "-"
        warn = " [RED]" if h["red_flags"] else ""
        print(f"  {h['score']:>3}  {h['company'][:20]:<20} {h['title'][:44]:<44} "
              f"{flags[:26]:<26}{warn}")
    print("\nWrote hunt/results.json and hunt/results.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

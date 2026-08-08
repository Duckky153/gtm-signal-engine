"""Public ATS job-board readers.

Every source here is a public, unauthenticated endpoint. No API keys, no paid
data vendor, no scraping of logged-in pages. That is deliberate: the engine has
to be reproducible by anyone who clones it, including a prospect checking our
work.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Iterable

USER_AGENT = "gtm-signal-engine/1.0 (public job board reader)"
TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Posting:
    """One job posting, normalised across ATS vendors."""

    company: str
    title: str
    location: str
    url: str
    posted_at: str = ""
    department: str = ""


@dataclass(frozen=True)
class Target:
    """A company we watch, and where its board lives."""

    name: str
    ats: str  # greenhouse | ashby | lever
    token: str
    segment: str = ""
    note: str = ""


class SourceError(RuntimeError):
    """Raised when a board cannot be read. Never swallowed silently."""


def _get_json(url: str) -> dict | list:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SourceError(f"{url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SourceError(f"{url} unreachable: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise SourceError(f"{url} did not return JSON") from exc


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def fetch_greenhouse(target: Target) -> list[Posting]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{target.token}/jobs"
    payload = _get_json(url)
    if not isinstance(payload, dict):
        raise SourceError(f"{url} returned an unexpected shape")
    postings = []
    for job in payload.get("jobs", []):
        location = job.get("location") or {}
        postings.append(
            Posting(
                company=target.name,
                title=_text(job.get("title")),
                location=_text(location.get("name")) if isinstance(location, dict) else "",
                url=_text(job.get("absolute_url")),
                posted_at=_text(job.get("updated_at")),
            )
        )
    return postings


def fetch_ashby(target: Target) -> list[Posting]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{target.token}"
    payload = _get_json(url)
    if not isinstance(payload, dict):
        raise SourceError(f"{url} returned an unexpected shape")
    postings = []
    for job in payload.get("jobs", []):
        postings.append(
            Posting(
                company=target.name,
                title=_text(job.get("title")),
                location=_text(job.get("location")),
                url=_text(job.get("jobUrl")),
                posted_at=_text(job.get("publishedAt")),
                department=_text(job.get("department")),
            )
        )
    return postings


def fetch_lever(target: Target) -> list[Posting]:
    url = f"https://api.lever.co/v0/postings/{target.token}?mode=json"
    payload = _get_json(url)
    if not isinstance(payload, list):
        raise SourceError(f"{url} returned an unexpected shape")
    postings = []
    for job in payload:
        categories = job.get("categories") or {}
        postings.append(
            Posting(
                company=target.name,
                title=_text(job.get("text")),
                location=_text(categories.get("location")),
                url=_text(job.get("hostedUrl")),
                department=_text(categories.get("team")),
            )
        )
    return postings


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "ashby": fetch_ashby,
    "lever": fetch_lever,
}


@dataclass
class FetchReport:
    """What we read, and what we failed to read. Failures are reported, never hidden."""

    postings: list[Posting] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)

    @property
    def companies_read(self) -> int:
        return len({posting.company for posting in self.postings})


def fetch_all(targets: Iterable[Target]) -> FetchReport:
    report = FetchReport()
    for target in targets:
        fetcher = FETCHERS.get(target.ats)
        if fetcher is None:
            report.failures.append((target.name, f"unknown ATS '{target.ats}'"))
            continue
        try:
            report.postings.extend(fetcher(target))
        except SourceError as exc:
            report.failures.append((target.name, str(exc)))
    return report

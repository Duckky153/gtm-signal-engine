"""Signal detection and scoring.

A job board is a public statement of where a company is about to spend money.
This module turns that statement into a ranked buying signal.

The rules below are deliberately readable. A prospect should be able to disagree
with a weight and change it, rather than be asked to trust a black box.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .sources import Posting


@dataclass(frozen=True)
class Rule:
    """One buying signal, and what it means commercially."""

    key: str
    label: str
    phrase: str  # reads naturally inside "N open ___ roles"
    why_it_matters: str
    patterns: tuple[str, ...]
    weight: int
    cap: int
    excludes: tuple[str, ...] = ()

    def matches(self, title: str) -> bool:
        haystack = title.lower()
        if any(re.search(pattern, haystack) for pattern in self.excludes):
            return False
        return any(re.search(pattern, haystack) for pattern in self.patterns)


RULES: tuple[Rule, ...] = (
    Rule(
        key="gtm_function_forming",
        phrase="go-to-market engineering",
        label="GTM function being built",
        why_it_matters=(
            "They are standing up go-to-market engineering right now. Budget is "
            "approved, the process is not yet fixed, and outside help is cheapest "
            "to adopt at this exact moment."
        ),
        patterns=(
            r"\bgtm engineer",
            r"go[- ]to[- ]market engineer",
            r"\bgrowth engineer",
            r"gtm (systems|automation|operations)",
        ),
        weight=20,
        cap=3,
    ),
    Rule(
        key="revops_investment",
        phrase="revenue operations",
        label="RevOps investment",
        why_it_matters=(
            "Revenue operations hires signal that pipeline data and routing are "
            "already painful enough to staff against."
        ),
        patterns=(
            r"revenue operations",
            r"\brevops\b",
            r"sales operations",
            r"marketing operations",
            r"\bmarketing ops\b",
            r"deal desk",
        ),
        weight=12,
        cap=3,
    ),
    Rule(
        key="outbound_scaling",
        phrase="outbound sales",
        label="Outbound being scaled",
        why_it_matters=(
            "SDR and BDR headcount is the clearest tell that a company is betting "
            "on outbound. Every new rep multiplies the need for lists, enrichment "
            "and routing."
        ),
        patterns=(
            r"\bsdr\b",
            r"\bbdr\b",
            r"sales development",
            r"business development representative",
            r"outbound",
        ),
        weight=12,
        cap=5,
    ),
    Rule(
        key="demand_leadership",
        phrase="demand-generation leadership",
        label="New demand leadership",
        why_it_matters=(
            "A new growth or demand-gen leader arrives with a mandate and a budget, "
            "and replaces incumbent vendors early in their tenure."
        ),
        patterns=(
            r"(head|vp|vice president|director) of (growth|demand|marketing)",
            r"demand generation",
            r"growth marketing (lead|manager|director)",
        ),
        weight=10,
        cap=2,
    ),
    Rule(
        key="sales_capacity",
        phrase="sales capacity",
        label="Sales capacity growth",
        why_it_matters=(
            "Account executives and sales engineers hired in volume create pipeline "
            "pressure roughly one quarter later."
        ),
        patterns=(
            r"account executive",
            r"sales engineer",
            r"solutions engineer",
            r"solutions consultant",
            r"solutions architect",
        ),
        weight=4,
        cap=6,
        excludes=(r"\bintern\b",),
    ),
)

MAX_RAW_SCORE = sum(rule.weight * rule.cap for rule in RULES)


@dataclass
class SignalHit:
    """One rule firing at one company, with the evidence that fired it."""

    rule: Rule
    postings: list[Posting] = field(default_factory=list)

    @property
    def distinct_roles(self) -> int:
        """Same req posted in five cities is one role, not five.

        Scoring on raw posting count is the single easiest way to look
        unserious to anyone who knows how an ATS works.
        """
        return len({posting.title.strip().lower() for posting in self.postings})

    @property
    def counted(self) -> int:
        return min(self.distinct_roles, self.rule.cap)

    @property
    def points(self) -> int:
        return self.rule.weight * self.counted


@dataclass
class CompanySignal:
    """A scored company, with every posting that justified the score."""

    company: str
    hits: list[SignalHit] = field(default_factory=list)
    total_postings: int = 0

    @property
    def raw_score(self) -> int:
        return sum(hit.points for hit in self.hits)

    @property
    def score(self) -> int:
        """0-100. Normalised so the number means the same thing across runs."""
        if MAX_RAW_SCORE == 0:
            return 0
        return round(100 * self.raw_score / MAX_RAW_SCORE)

    @property
    def tier(self) -> str:
        if self.score >= 40:
            return "A"
        if self.score >= 20:
            return "B"
        return "C"

    @property
    def evidence_count(self) -> int:
        return sum(len(hit.postings) for hit in self.hits)

    def why_now(self) -> str:
        """The one line a rep would actually open with."""
        if not self.hits:
            return "No active go-to-market hiring signal."
        lead = max(self.hits, key=lambda hit: hit.points)
        count = lead.distinct_roles
        plural = "roles" if count != 1 else "role"
        spread = len(lead.postings)
        tail = f" across {spread} postings" if spread > count else ""
        return f"{self.company} has {count} open {lead.rule.phrase} {plural}{tail}."


def detect(postings: list[Posting]) -> list[CompanySignal]:
    """Score every company represented in `postings`, best first."""
    by_company: dict[str, list[Posting]] = {}
    for posting in postings:
        by_company.setdefault(posting.company, []).append(posting)

    signals: list[CompanySignal] = []
    for company, company_postings in by_company.items():
        signal = CompanySignal(company=company, total_postings=len(company_postings))
        for rule in RULES:
            matched = [p for p in company_postings if rule.matches(p.title)]
            if matched:
                signal.hits.append(SignalHit(rule=rule, postings=matched))
        signals.append(signal)

    signals.sort(key=lambda s: (-s.score, -s.evidence_count, s.company))
    return signals

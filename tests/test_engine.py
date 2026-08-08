"""Tests for the scoring logic.

Network calls are not tested here; parsing is tested against captured payload
shapes so the suite runs offline and deterministically.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.signals import MAX_RAW_SCORE, RULES, detect  # noqa: E402
from engine.sources import Posting, Target, fetch_all  # noqa: E402


def posting(company: str, title: str, location: str = "Remote") -> Posting:
    return Posting(company=company, title=title, location=location, url="https://example.test/1")


class RuleMatchingTests(unittest.TestCase):
    def rule(self, key: str):
        return next(rule for rule in RULES if rule.key == key)

    def test_gtm_titles_match_across_phrasings(self):
        rule = self.rule("gtm_function_forming")
        for title in (
            "GTM Engineer",
            "Go-To-Market Engineer",
            "Senior Growth Engineer",
            "Manager, GTM Systems",
        ):
            self.assertTrue(rule.matches(title), title)

    def test_unrelated_titles_do_not_match(self):
        rule = self.rule("gtm_function_forming")
        for title in ("Backend Engineer", "Staff Product Designer", "Recruiter"):
            self.assertFalse(rule.matches(title), title)

    def test_sdr_matches_but_not_as_substring_of_another_word(self):
        rule = self.rule("outbound_scaling")
        self.assertTrue(rule.matches("SDR Manager"))
        self.assertFalse(rule.matches("Adsdrive Engineer"))

    def test_excludes_suppress_a_match(self):
        rule = self.rule("sales_capacity")
        self.assertTrue(rule.matches("Account Executive"))
        self.assertFalse(rule.matches("Account Executive Intern"))


class ScoringTests(unittest.TestCase):
    def test_same_req_in_many_cities_counts_once(self):
        spread = [
            posting("Acme", "GTM Engineer", "New York"),
            posting("Acme", "GTM Engineer", "Seattle"),
            posting("Acme", "GTM Engineer", "Vancouver"),
        ]
        single = [posting("Acme", "GTM Engineer", "New York")]
        self.assertEqual(detect(spread)[0].score, detect(single)[0].score)

    def test_distinct_roles_do_increase_the_score(self):
        one = detect([posting("Acme", "GTM Engineer")])[0].score
        two = detect(
            [posting("Acme", "GTM Engineer"), posting("Acme", "Growth Engineer")]
        )[0].score
        self.assertGreater(two, one)

    def test_cap_limits_runaway_counts(self):
        rule = next(r for r in RULES if r.key == "outbound_scaling")
        many = [posting("Acme", f"SDR {index}") for index in range(rule.cap + 8)]
        hit = detect(many)[0].hits[0]
        self.assertEqual(hit.counted, rule.cap)

    def test_score_is_bounded_to_one_hundred(self):
        everything = []
        for rule in RULES:
            for index in range(rule.cap + 3):
                title = {
                    "gtm_function_forming": f"GTM Engineer {index}",
                    "revops_investment": f"Revenue Operations Analyst {index}",
                    "outbound_scaling": f"SDR {index}",
                    "demand_leadership": f"Head of Growth {index}",
                    "sales_capacity": f"Account Executive {index}",
                }[rule.key]
                everything.append(posting("Acme", title))
        score = detect(everything)[0].score
        self.assertLessEqual(score, 100)
        self.assertEqual(score, 100)

    def test_company_with_no_signal_scores_zero(self):
        signal = detect([posting("Quiet", "Backend Engineer")])[0]
        self.assertEqual(signal.score, 0)
        self.assertEqual(signal.tier, "C")
        self.assertIn("No active", signal.why_now())

    def test_results_are_ranked_best_first(self):
        signals = detect(
            [
                posting("Quiet", "Backend Engineer"),
                posting("Loud", "GTM Engineer"),
                posting("Loud", "Head of Growth"),
            ]
        )
        self.assertEqual(signals[0].company, "Loud")
        self.assertEqual(signals[-1].company, "Quiet")

    def test_why_now_reports_role_count_not_posting_count(self):
        signal = detect(
            [
                posting("Acme", "GTM Engineer", "New York"),
                posting("Acme", "GTM Engineer", "Seattle"),
            ]
        )[0]
        self.assertIn("1 open go-to-market engineering role", signal.why_now())
        self.assertIn("across 2 postings", signal.why_now())

    def test_max_raw_score_matches_rule_definitions(self):
        self.assertEqual(MAX_RAW_SCORE, sum(rule.weight * rule.cap for rule in RULES))


class SourceFailureTests(unittest.TestCase):
    def test_unknown_ats_is_reported_not_swallowed(self):
        report = fetch_all([Target(name="Acme", ats="carrier-pigeon", token="x")])
        self.assertEqual(report.postings, [])
        self.assertEqual(len(report.failures), 1)
        self.assertIn("unknown ATS", report.failures[0][1])


class OutputTests(unittest.TestCase):
    """The shipped output must stay loadable and self-consistent."""

    def test_generated_signals_json_is_consistent(self):
        path = Path(__file__).resolve().parent.parent / "out" / "signals.json"
        if not path.exists():
            self.skipTest("run `python3 -m engine.run` first")
        payload = json.loads(path.read_text())
        self.assertGreater(payload["postings_scanned"], 0)
        scores = [row["score"] for row in payload["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for row in payload["results"]:
            self.assertLessEqual(row["score"], 100)
            self.assertGreaterEqual(row["score"], 0)
            for signal in row["signals"]:
                self.assertLessEqual(signal["distinct_roles"], signal["postings"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

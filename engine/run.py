"""Run the engine: read public boards, score buying signals, write the outputs.

    python3 -m engine.run

Outputs land in out/:
    signals.json  full result, including every posting used as evidence
    signals.csv   flat rows for a CRM or a Clay table import
    report.md     the human-readable version
"""

from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .signals import CompanySignal, detect
from .sources import FETCHERS, FetchReport, Posting, SourceError, Target

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


def load_targets(path: Path | None = None) -> list[Target]:
    source = path or (Path(__file__).resolve().parent / "targets.json")
    payload = json.loads(source.read_text())
    return [
        Target(
            name=item["name"],
            ats=item["ats"],
            token=item["token"],
            segment=item.get("segment", ""),
            note=item.get("note", ""),
        )
        for item in payload["targets"]
    ]


def fetch_all_parallel(targets: list[Target], workers: int = 10) -> FetchReport:
    """Same contract as sources.fetch_all, but boards are read concurrently."""
    report = FetchReport()

    def read(target: Target) -> tuple[Target, list[Posting] | str]:
        fetcher = FETCHERS.get(target.ats)
        if fetcher is None:
            return target, f"unknown ATS '{target.ats}'"
        try:
            return target, fetcher(target)
        except SourceError as exc:
            return target, str(exc)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for target, result in pool.map(read, targets):
            if isinstance(result, str):
                report.failures.append((target.name, result))
            else:
                report.postings.extend(result)
    return report


def to_payload(
    signals: list[CompanySignal],
    report: FetchReport,
    targets: list[Target],
) -> dict:
    segments = {target.name: target.segment for target in targets}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "companies_scanned": len(targets),
        "companies_read": report.companies_read,
        "postings_scanned": len(report.postings),
        "failures": [{"company": name, "reason": reason} for name, reason in report.failures],
        "results": [
            {
                "company": signal.company,
                "segment": segments.get(signal.company, ""),
                "score": signal.score,
                "tier": signal.tier,
                "why_now": signal.why_now(),
                "open_roles_total": signal.total_postings,
                "signals": [
                    {
                        "key": hit.rule.key,
                        "label": hit.rule.label,
                        "why_it_matters": hit.rule.why_it_matters,
                        "distinct_roles": hit.distinct_roles,
                        "postings": len(hit.postings),
                        "counted": hit.counted,
                        "points": hit.points,
                        "evidence": [
                            {"title": p.title, "location": p.location, "url": p.url}
                            for p in hit.postings[:8]
                        ],
                    }
                    for hit in sorted(signal.hits, key=lambda h: -h.points)
                ],
            }
            for signal in signals
        ],
    }


def write_csv(payload: dict, path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["company", "segment", "score", "tier", "why_now", "top_signal", "open_roles_total"]
        )
        for row in payload["results"]:
            top = row["signals"][0]["label"] if row["signals"] else ""
            writer.writerow(
                [
                    row["company"],
                    row["segment"],
                    row["score"],
                    row["tier"],
                    row["why_now"],
                    top,
                    row["open_roles_total"],
                ]
            )


def write_report(payload: dict, path: Path) -> None:
    lines = [
        "# GTM buying-signal report",
        "",
        f"Generated {payload['generated_at']} from public job boards.",
        "",
        f"- Companies scanned: **{payload['companies_scanned']}**",
        f"- Postings read: **{payload['postings_scanned']}**",
        f"- Boards that failed: **{len(payload['failures'])}**",
        "",
        "| # | Company | Score | Tier | Why now |",
        "|---|---------|-------|------|---------|",
    ]
    for index, row in enumerate(payload["results"], start=1):
        lines.append(
            f"| {index} | {row['company']} | {row['score']} | {row['tier']} | {row['why_now']} |"
        )

    if payload["failures"]:
        lines += ["", "## Boards that could not be read", ""]
        lines += [f"- {f['company']}: {f['reason']}" for f in payload["failures"]]

    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    targets = load_targets()
    print(f"Reading {len(targets)} public job boards...")
    report = fetch_all_parallel(targets)
    print(f"  {len(report.postings)} postings from {report.companies_read} companies")
    for name, reason in report.failures:
        print(f"  FAILED {name}: {reason}")

    signals = detect(report.postings)
    payload = to_payload(signals, report, targets)

    OUT.mkdir(exist_ok=True)
    (OUT / "signals.json").write_text(json.dumps(payload, indent=2))
    write_csv(payload, OUT / "signals.csv")
    write_report(payload, OUT / "report.md")

    ranked = [r for r in payload["results"] if r["score"] > 0]
    print(f"\nTop accounts by buying signal ({len(ranked)} scored above zero):\n")
    for row in ranked[:10]:
        print(f"  {row['score']:>3}  [{row['tier']}]  {row['company']:<14} {row['why_now']}")
    print(f"\nWrote out/signals.json, out/signals.csv, out/report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

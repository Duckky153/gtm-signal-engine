# GTM Signal Engine

**Live demo → https://duckky153.github.io/gtm-signal-engine/**

A job board is a public statement of where a company is about to spend money.

This reads 30 public ATS boards, finds the hiring patterns that mean a company is
building or scaling go-to-market, and ranks every account by how ready it is to buy —
with the exact requisition behind every score.

**No API keys. No paid data vendor.** Clone it and you get the same numbers.

```bash
git clone https://github.com/Duckky153/gtm-signal-engine
cd gtm-signal-engine
python3 -m engine.run                   # writes out/signals.{json,csv} and out/report.md
python3 -m unittest discover -s tests   # 14 tests
```

Python 3.9+, standard library only. No install step, no credentials. A full run over
30 boards and ~5,600 postings takes about 3 seconds.

## The five signals

| Signal | Weight | Why it matters commercially |
|---|---|---|
| GTM function being built | 20 × up to 3 | Budget approved, process not yet fixed — cheapest moment to adopt outside help |
| RevOps investment | 12 × up to 3 | Pipeline data and routing already painful enough to staff against |
| Outbound being scaled | 12 × up to 5 | Every new rep multiplies the need for lists, enrichment and routing |
| New demand leadership | 10 × up to 2 | New leader, new mandate, incumbent vendors replaced early |
| Sales capacity growth | 4 × up to 6 | Pipeline pressure follows roughly one quarter later |

Weights live in `engine/signals.py` and are meant to be argued with, not trusted.

## What it does that a keyword search does not

- **Counts roles, not postings.** One requisition listed in five cities is one role.
- **Caps each signal.** Forty open AE seats do not out-rank a first GTM engineering team.
- **Carries its evidence.** Every score expands to the requisitions behind it.
- **Reports failures out loud.** An unreadable board is a failure, not a silent zero.

## Honest limits

- Signals come from **job titles**, not descriptions. A posting naming Clay or Apollo in
  its body is a strong signal this version does not yet read.
- It sees **public ATS boards only**. A company hiring privately is invisible to it.
- Hiring intent is **correlated with** buying intent, not identical to it. This ranks who
  to research first; it does not close anyone.
- The 30-company target list exists to prove the mechanism. Pointing it at a real ICP is
  a change to one JSON file.

## Output

`out/signals.json` — full result including every posting used as evidence
`out/signals.csv` — flat rows for a CRM or Clay table import
`out/report.md` — the human-readable ranking

Built by Dakshit Raj.

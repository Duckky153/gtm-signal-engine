# gtm-signal-engine

Proof-of-work artifact for the GTM Engineer job path. Reads public ATS job boards,
detects go-to-market buying signals, ranks accounts, and carries the evidence for
every score.

**Spawned from:** `~/Vaults/fetch/100 Research/Sessions/2026-08-07 GTM Engineer Proof-of-Work Job Path.md`

## What it is

A demo link to send to hiring managers and GTM agency founders instead of a resume
claim. It shows the exact skill the role hires for: wiring public data into a ranked,
auditable commercial output.

## Hard rules

- **No paid API keys, ever.** Public unauthenticated endpoints only. The whole point is
  that a prospect can clone it and reproduce the numbers. A credential in this repo
  breaks the pitch.
- **No fabricated data.** Every row on the demo page traces to a live requisition URL.
  If a board cannot be read it is reported as a failure, never silently zeroed.
- **Count roles, not postings.** One req in five cities is one role. Regressing this is
  the fastest way to look unserious to a GTM buyer.
- **Honest limits stay on the page.** The "Honest limits" section is not marketing
  filler — it is the reason the rest is believable. Do not remove it.

## Layout

| Path | What |
|---|---|
| `engine/sources.py` | Public ATS readers (Greenhouse, Ashby, Lever) |
| `engine/signals.py` | The five scoring rules, weights, caps, dedupe |
| `engine/run.py` | CLI entry point, writes `out/` |
| `engine/targets.json` | Watched companies. Every token validated live. |
| `docs/` | GitHub Pages demo (`index.html` + `data/signals.json`) |
| `tests/` | 14 tests, stdlib unittest, offline |

## Commands

```bash
python3 -m engine.run                      # refresh signals
python3 -m unittest discover -s tests      # must stay green
cp out/signals.json docs/data/signals.json # publish new data to the demo
```

## State

Shipped and live. Demo publishes from `docs/` on the `main` branch.
Not yet built: n8n workflow export (deliberately omitted rather than shipped untested),
and job-description parsing for stack mentions such as Clay or Apollo.

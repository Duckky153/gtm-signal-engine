# Session Context — Job Search via Proof-of-Work Artifact
Session: 2026-08-07 → 2026-08-08

## The goal, in his own words

> "I'm simply looking for people, maybe startups, that I can give them something
> and they will hire me. It cannot be more simple than that."

> "I literally just need a job to stay in the United States."

**Do not drift from this.** He restated it four separate times because I kept
complicating it.

## Hard constraints

| Constraint | Detail |
|---|---|
| No technical interview | Cannot pass LeetCode/whiteboard/live coding. Comms and demo only. |
| **No resume applications** | Never had a paid job. Loses in any resume pile. Sponsorship checkbox filters him out before a human reads it. **Never tell him to "apply to the role."** He called this out directly. |
| Artifact replaces resume | It is NOT a supplement to an application. |
| W-2 only | 1099/contract collides with his no-self-employment rule and his OPT record. Don't ask him about this again — the answer is W-2. |
| LinkedIn is the channel | He sends manually. Never drive his LinkedIn account with automation — restriction risk. |
| International student | F-1, OPT pending, EAD processing. With EAD: no sponsorship needed for ~12 months (36 with STEM). |

## What the correct sequence is

find a person who can say yes → build them something they actually want →
send it on LinkedIn → conversation → job

A job posting is **evidence** that budget and need exist. It is never an
application target. This also means the company doesn't need an open role at all.

## What got built

**`gtm-signal-engine`** — reads public ATS boards (Greenhouse/Ashby/Lever, all
free and unauthenticated), scores five go-to-market buying signals, carries the
requisition evidence behind every score.

- Live: https://duckky153.github.io/gtm-signal-engine/
- Repo: https://github.com/Duckky153/gtm-signal-engine (**Duckky153** account, not fetchrn —
  `gh auth switch --user Duckky153` to push, switch back to fetchrn after)
- 14 tests, stdlib only, ~3 second full run
- `hunt/` — 457 candidate boards, 152 live, ~7,600 jobs scanned, filters for
  GTM/ops roles + US + full-time + no coding-interview language in the description

**Design history (important — do not repeat):** he rejected the page THREE times.
Root cause was that I kept shipping the same dark background + teal accent +
rounded-card template and calling it a redesign. He picked, explicitly:
**bright white SaaS look (indigo accent, modern sans, rounded cards) + confident
sales-pitch copy.** Dark mode is deliberately deleted. Do not bring it back.

**Data lesson:** the first demo listed Stripe, Cloudflare, OpenAI. He rejected
that — a small agency cannot sell to Stripe, so those names prove nothing. Target
list is now mid-market only.

## Verified people (all opened live on LinkedIn 2026-08-08)

| Person | Role | LinkedIn | Note |
|---|---|---|---|
| **Nikko Georgantonis** | Head of GTM AI & Systems, Hightouch | /in/nikko-georgantonis-b53651ab/ | **PRIMARY.** Owns the exact function. Virginia Beach — Dakshit is Ashburn VA. Real hook. |
| Austin Cook Kiessig | VP Revenue Operations, Hightouch | /in/austin-cook-kiessig-91a05b4/ | Role embeds in his team |
| Victoria Molina | Sr Mgr, AI Growth Ops, Hightouch | /in/victoria-molina-a63414159/ | |
| **Omar Shorbaji** | Sr Mgr, Forward Deployed Engineering, Anyscale | /in/omarshorbaji/ | Unambiguously runs the hiring team |
| Ian D. Jordan | Field/FDE, Anyscale | /in/ian-d-jordan-phd-6aa67a22a/ | Peer, warm intro path |

**Stytch removed** — verified Twilio completed the acquisition 2025-11-14. Not a
small startup.

**Still missing:** PagerDuty, Column, Carta. The Column search failed because
"Column bank" returns Polish banking architects — use "Column N.A." or "Column Tax".

## The best lead source found — and I surfaced it too late

**community.clay.com/x/share-jobs** — 18,900 members. Real founders and operators
posting "DM me," not job applications. Board rules force salary + location +
company name in every post. Needs a free account to DM.

People there who are **actively asking to be given something**:

- **Sally Z.** — wants Shopify/e-commerce lead enrichment built (Store Leads → Clay
  → waterfall → HubSpot/Instantly). Wrote: *"send me a DM with relevant portfolio
  and suggested plan."* Budget flexible. This is the single closest match to what
  he described wanting.
- **Matt K. at Raptive** — $25/hr, up to 40 hrs/month, remote, **must be US based**,
  "DM me if interested." Salesforce data loading. Low bar.
- **James D.** — scaling past $20K/month ad spend across Meta/LinkedIn/Reddit,
  asking for recommendations.
- **Andrej Simunovic** (EagleRev), **Amaan N.** (ToplineX) — founders hiring
  directly; EagleRev's application is a 60-second Loom.

Also: a member publishes **"The Shortlist"**, a recurring roundup of newly-live
GTM engineering roles (Edition 001 = 32 roles, 002 = 43).

## Key strategic finding

**E-Verify should be a tiebreaker, not a gate.** Only 8 of 152 companies state
E-Verify in their postings — most enrolled employers simply never mention it. My
filter produced massive false negatives and cut the list from ~340 matching roles
to 6 companies. E-Verify only matters for the STEM extension *later*; with his EAD
he can work anywhere *now*.

## Drafted message (Nikko, connection note, <300 chars)

> Nikko — I built a GTM signal engine (reads public job boards, ranks buying
> intent, open source) and pointed it at Hightouch's market before applying to
> the GTM Engineer role. Would like to send it over. Also a fellow Virginian, up
> in Ashburn. — Dakshit

## Open questions

- Whether any of these companies run a technical round — unverified. Pre-screen
  the format before he invests.
- Whether he can handle a live *scoping conversation* (no tools, reasoning about
  ICP and signals out loud) vs. only async/demo. Asked, never answered.
- He must be able to explain the engine himself — hiring guides explicitly say
  "a project they built themselves, not something someone else built." A
  defensibility walkthrough was proposed and never built.

## Environment notes

- Chrome renders black screenshots when its GPU process dies. Workaround that
  worked: headless screenshot via
  `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new
  --disable-gpu --screenshot=out.png <url>`. Restarting Chrome also fixes it:
  `open -na "Google Chrome" --args --profile-directory="Profile 10"`
- Profile 10 = "Unizel" = daksh@unizel.com. Profile 4 = "Unizel Computer" — never use.
- A second Windows Chrome is connected; always pick Browser 1 (macOS, local).
- e-verify.gov blocks scripted access (403). Browser only.

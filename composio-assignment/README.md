# Composio AI Product Ops — Take-home

**Goal:** research 100 apps across 10 categories and determine which ones Composio
could turn into an agent toolkit today — what auth they use, whether access is
self-serve or gated, how broad the API surface is, whether an MCP server already
exists, and the buildability verdict + blocker if not ready.

**Full case study (findings, patterns, agent workflow, verification):**
open `output/case_study.html` in a browser, or see the deployed link in the
submission. Understandable in ~2 minutes, no narration needed.

## What's in this repo

```
data/
  apps_data.py      # the 100-row dataset: every field, every evidence URL, confidence tags
  analyze.py         # clusters the dataset into the pattern stats shown in the case study
  verification.py    # the 11-app verification sample: first-pass vs source-checked finding
agent/
  pipeline.py         # the runnable research + verification agent (see "Running the agent")
  apps.csv             # the 100 apps in agent-input format
generate_html.py     # builds output/case_study.html from the three data files above
output/
  case_study.html    # the single-page deliverable
```

## Research dimensions

For each of the 100 apps: **category** + one-line description, **auth
method(s)**, **self-serve vs gated** access, **API surface** (REST/GraphQL,
breadth), **existing MCP** (official/community/none), a **buildability
verdict** (Ready / Ready-friction / Blocked) with the main **blocker**, an
**evidence URL**, and a **confidence tag** (verified / high / medium / low).

## Agent workflow

The research follows a two-pass structure, implemented as a reproducible
pipeline in `agent/pipeline.py`:

**Pass 1 — Research.** For each app, an LLM with a web-search tool fills the
8-field schema above and self-rates its own confidence. It's explicitly
instructed to prefer official documentation and never invent a URL or auth
method it isn't sure of.

**Pass 2 — Verification.** A sample of the pass-1 rows — every `low`-confidence
row first, topped up with a seeded random batch — goes through a second,
deliberately skeptical pass that is *forced* to fetch the real docs URL and
re-derive each field from the live page, then diffs it against the draft.

**Human review.** Ambiguous cases are intentionally kept as low-confidence
rather than forced into an unsupported conclusion. A `low` tag is a handoff
signal, not a failure — see "Human handoff queue" below.

### Important note on how the submitted dataset was produced

The final 100-app dataset in `data/apps_data.py` was assembled during an
AI-assisted research session using the same structured schema, evidence
requirements, and two-pass verification methodology that `agent/pipeline.py`
implements. The Python agent in this repo is the reproducible implementation
of that workflow — you can re-run it end to end against live docs with your
own API credentials (see below). The current dataset should not be
represented as the output of a single, unattended, end-to-end execution of
`pipeline.py` in this environment; it reflects the same methodology, applied
directly, with source verification on an 11-app sample. `output/case_study.html`
states this plainly in its methodology section.

## Running the agent

### 1. Demo / replay mode — no credentials needed

```bash
python agent/pipeline.py --demo
```

Loads a small fixed sample of apps, prints the exact research schema, and
replays the existing 11-app verification sample so the draft → verify
workflow is visible without an API key. This never makes a live model call
and never labels replayed results as freshly researched — it prints
`DEMO / REPLAY MODE` up front.

### 2. Small live test — real API calls, a few apps

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."   # PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
python agent/pipeline.py --apps agent/apps.csv --limit 3 --verify-sample 1
```

Runs the real research + verification pipeline against 3 apps, so you can see
it work end to end without triggering 100 API calls.

### 3. Full run — all 100 apps

```bash
python agent/pipeline.py --apps agent/apps.csv --out results.json --verify-sample 20 --seed 42
```

Researches all 100 apps, verifies a 20-app sample (every low-confidence row
first, seeded random top-up for reproducibility), and writes `results.json`.

Swap `tools=[{"type": "web_search_20250305", ...}]` in `pipeline.py` for a
Composio-hosted MCP/browser-use tool (`composio.tools.get(...)`) to run the
same two-pass structure on Composio's own infrastructure instead of
Anthropic's built-in web search.

## Human handoff queue

7 of the 100 rows could not be resolved with confidence by the research
pass — mostly low-visibility vendors with no real developer-docs footprint
in search results (`fanbasis`, `Waterfall.io`, `Paygent Connect`, `iPayX`,
`MrScraper`, `higgsfield`) or an ambiguous product (`Pumble` — only
bot/webhook docs surfaced, no confirmed general REST API). These are tagged
`confidence: "low"` in the dataset and called out on the case-study page
rather than smoothed into a confident-looking row. The likely next action for
each is one of: contact the vendor directly, request developer access, spin
up a trial account, or request docs that aren't publicly indexed. None of
that outreach has been performed as part of this submission — it's the
queue a human product-ops reviewer would work next.

## Reproducing the case study page

`output/case_study.html` is a static, self-contained page (no build step)
generated by `generate_html.py` from `data/apps_data.py` + `data/analyze.py`
+ `data/verification.py`. After editing the dataset, regenerate with:

```bash
python data/analyze.py      # recomputes data/analysis.json and data/apps.json
python generate_html.py     # rebuilds output/case_study.html
```

## Security / secrets

No API keys, tokens, or credentials are committed to this repo. `.gitignore`
excludes `.env`, `*.key`, `secrets/`, and generated `results.json` files —
set `ANTHROPIC_API_KEY` as an environment variable, never in a committed file.

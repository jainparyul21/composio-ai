# Composio AI Product Ops — Take-home

AI-assisted research and verification workflow for evaluating **100 apps across 10 categories** and determining which ones Composio could potentially turn into agent toolkits today.

The research evaluates authentication, access requirements, API surface, MCP availability, buildability, blockers, evidence, and confidence, then turns the 100 rows into product-level patterns and a practical build queue.

## Live case study

The final case study is a self-contained static HTML page.

**Live:** `PASTE_YOUR_VERCEL_URL_HERE`

**Source:** this repository

The page is designed to be understood in roughly two minutes without narration and contains the findings, patterns, agent workflow, verification results, human handoff queue, and the full 100-app matrix.

---

## What's in this repo

```text
agent/
  pipeline.py          # runnable two-pass research + verification agent
  apps.csv             # 100 apps in agent-input format

data/
  apps_data.py         # final 100-row research dataset
  analyze.py           # computes aggregate patterns and analysis outputs
  apps.json            # machine-readable dataset generated from the research
  analysis.json        # computed analysis used by the case study
  verification.py      # 11-app draft-vs-source verification sample

output/
  case_study.html      # generated self-contained case-study page

index.html              # deployment entry point for the live static site
generate_html.py        # regenerates output/case_study.html
check_consistency.py    # validates dataset, analysis, HTML and repository consistency

README.md
.gitignore
```

---

## What was researched

For each of the 100 apps, the research captures:

* **Category** and one-line description
* **Authentication** — OAuth2, API key, Basic, token, or other
* **Self-serve vs gated** access
* **API surface** — REST / GraphQL and approximate breadth
* **Existing MCP** — official, community, or none found
* **Buildability** — `Ready`, `Ready-friction`, or `Blocked`
* **Blocker** where the integration is not straightforward
* **Evidence URL** behind the finding
* **Confidence** — `verified`, `high`, `medium`, or `low`

The goal was not only to produce 100 rows, but to determine **where Composio could build first, where integration friction exists, and where vendor outreach is required.**

---

## Key findings

The current dataset produces:

| Finding                                               |       Result |
| ----------------------------------------------------- | -----------: |
| Ready                                                 | **66 / 100** |
| Ready with friction                                   | **23 / 100** |
| Blocked                                               | **11 / 100** |
| OAuth2 present as an auth path                        | **61 / 100** |
| Apps with an MCP server                               | **32 / 100** |
| Low-confidence rows requiring follow-up               |  **7 / 100** |
| Rows checked in the source-backed verification sample |       **11** |

The case study turns these numbers into the main product conclusions and build-priority tiers.

---

## Research workflow

The research was structured as a **two-pass pipeline** rather than a single model response.

### Pass 1 — Research

For each app, the research agent is given the app name and website hint and asked to fill the structured research schema.

The research prompt explicitly requires the agent to:

* prefer official documentation
* provide evidence for each finding
* avoid inventing URLs or authentication methods
* record uncertainty instead of guessing
* assign a confidence level to the result

### Sampling

The verification budget is allocated deliberately.

All rows marked `low` confidence are included first. The remaining slots are filled with a seeded spot-check sample so the verification set can be reproduced.

### Pass 2 — Verification

A second, skeptical pass is asked to check the cited documentation and re-derive the relevant fields from the source rather than simply trusting the first answer.

The result is compared with the original draft and the differences are recorded.

This catches issues such as:

* an API existing but being gated
* an MCP existing but only on a paid tier
* legacy and current authentication systems coexisting
* self-serve signup being different from self-serve API access
* assumptions about a product's availability being wrong

---

## Verification results

The submitted case study contains an **11-app source-backed verification sample**.

**4 / 11** findings were confirmed on the first pass.

**7 / 11** required a correction or additional nuance after checking the documentation.

These numbers represent **first-pass agreement and correction within the reviewed sample**. They are not presented as a statistical accuracy estimate for all 100 apps.

The important result is that the verification pass exposed several material differences that a single-pass research workflow could have shipped without catching.

Examples include:

* **Twenty** — MCP availability depended on the hosted paid tier
* **GoHighLevel** — current OAuth2 and legacy API-key systems needed to be distinguished
* **Otter.ai** — an MCP exists while general API access remains gated
* **Consensus** — the raw API and MCP paths have different access models
* **Devin** — account signup is self-serve, while usage is gated by paid credits
* **Grain** — API access requires a paid plan even though tokens can be generated from account settings

---

## Human handoff queue

Seven rows remain explicitly marked as `low` confidence:

* Pumble
* fanbasis
* MrScraper
* Waterfall.io
* Paygent Connect
* iPayX
* higgsfield

These cases were not forced into confident-looking answers where public documentation was insufficient or ambiguous.

The appropriate next step for these rows is human product-ops follow-up such as:

* contacting the vendor
* requesting developer/API access
* creating a trial account
* requesting documentation that is not publicly indexed

No such vendor outreach is claimed as part of this submission.

A low-confidence label is therefore treated as a **handoff signal**, not as a failure to produce an answer.

---

## Build-priority framework

The case study groups the research into three practical tiers derived directly from the buildability verdict.

### Tier 1 — Easy wins

**66 apps**

Documented APIs, achievable credentials, predictable authentication, and no major external approval dependency.

### Tier 2 — Buildable with known friction

**23 apps**

The integration is possible, but a paid tier, app review, approval process, approved account, or additional setup step sits between signup and usable API access.

### Tier 3 — Outreach required

**11 apps**

Partner-gated, enterprise-only, no public self-serve path, or insufficiently confirmed API access.

This makes the research actionable: Tier 1 is primarily an engineering queue, Tier 2 adds operational dependencies, and Tier 3 requires a business/vendor conversation before engineering should commit.

---

## Running the agent

The repository provides three execution modes.

### 1. Demo / replay mode — no credentials

```bash
python agent/pipeline.py --demo
```

This mode requires no API key.

It loads the existing verification sample and replays the research → verification structure so the workflow can be inspected without making live model calls.

The output is explicitly labelled:

```text
DEMO / REPLAY MODE
```

It does **not** claim that the replay is a fresh live research run.

### 2. Small live test

For a real LLM execution, install the Anthropic SDK:

```bash
pip install anthropic
```

Set the API key as an environment variable.

macOS / Linux:

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

Windows PowerShell:

```powershell
$env:ANTHROPIC_API_KEY="your-api-key"
```

Then run a small test:

```bash
python agent/pipeline.py \
  --apps agent/apps.csv \
  --limit 3 \
  --verify-sample 1
```

This performs a genuine live research + verification run on a small number of apps before attempting a full run.

### 3. Full run

```bash
python agent/pipeline.py \
  --apps agent/apps.csv \
  --out results.json \
  --verify-sample 20 \
  --seed 42
```

The full run researches all 100 apps, prioritizes low-confidence rows for verification, fills the remainder with a seeded spot-check sample, and writes the resulting structured output to `results.json`.

The implementation also includes retry/error handling, deterministic sampling, limited test runs, and structured parsing/failure handling.

---

## Important note about the submitted dataset

The final 100-app dataset was assembled during an **AI-assisted research session** using the same structured schema, evidence requirements, and two-pass verification methodology implemented by `agent/pipeline.py`.

The Python pipeline in this repository is the **reproducible implementation of that workflow**.

The submitted dataset should not be represented as the output of one unattended end-to-end execution of `pipeline.py`. Instead, the dataset reflects the research methodology applied during the research session, with source-backed verification performed on the 11-app sample shown in the case study.

This distinction is intentionally documented rather than implying an execution that did not occur.

---

## Reproducing the case study

The case study is a static, self-contained HTML page and does not require a web server or build framework.

To regenerate the analysis outputs and case study after changing the dataset:

```bash
python data/analyze.py
python generate_html.py
```

This updates:

```text
data/apps.json
data/analysis.json
output/case_study.html
```

`index.html` is the deployment entry point for the live static site.

---

## Consistency check

Before submission, run:

```bash
python check_consistency.py
```

The checker validates the final repository for issues including:

* 100 app IDs
* verdict totals
* confidence totals
* dataset / analysis agreement
* HTML / analysis agreement
* expected verification counts
* forbidden claims or outdated language
* accidental committed secrets

A clean pass means the numbers presented in the case study are consistent with the underlying dataset.

---

## Security

No API keys, tokens, cookies, or other credentials belong in this repository.

Use environment variables for live API execution:

```text
ANTHROPIC_API_KEY
```

Never commit a key to source control.

The repository's `.gitignore` excludes common secret files and generated outputs such as `results.json`.

#!/usr/bin/env python3
"""
Composio App-Research Agent
============================

A two-pass research pipeline for the "which apps can Composio turn into an
agent toolkit today" question. For each app it fills in: category, auth
method(s), self-serve vs gated, API surface / MCP status, a buildability
verdict + blocker, an evidence URL, and its own confidence.

Pass 1 (research):    the model researches each app (with a web-search tool)
                       and returns structured JSON. It is instructed to prefer
                       official documentation and to never invent a URL or an
                       auth method it isn't sure of.
Pass 2 (verification): for a sample of the pass-1 rows (every "low"-confidence
                       row first, topped up with a seeded random batch), a
                       second, deliberately skeptical pass is forced to fetch
                       the real docs URL and re-derive the answer, then diffs
                       it against the draft.

Reproducibility note
---------------------
This script is the reproducible implementation of the research methodology
used to assemble the dataset in ../data/apps_data.py. See ../README.md for
how the submitted dataset relates to this script (short version: same schema,
same two-pass design, run during an AI-assisted research session — this file
is provided so the workflow can be re-run end to end against live docs with
your own API credentials).

Three ways to use this file
----------------------------
1. Demo / replay mode — no credentials needed, safe to run anywhere:
     python pipeline.py --demo

2. Small live test — a few apps, real API calls, real web search:
     export ANTHROPIC_API_KEY=sk-ant-...
     python pipeline.py --apps apps.csv --limit 3 --verify-sample 1

3. Full run — all 100 apps, a real verification sample:
     export ANTHROPIC_API_KEY=sk-ant-...
     python pipeline.py --apps apps.csv --out results.json --verify-sample 20 --seed 42

Requires: pip install anthropic  (only needed for modes 2 and 3)
"""
import argparse
import csv
import json
import os
import random
import sys
import time
import traceback
from dataclasses import dataclass, asdict, field
from typing import Optional

try:
    import anthropic
except ImportError:
    anthropic = None  # only required for live API modes; --demo works without it

MODEL = "claude-sonnet-4-6"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

FIELD_SCHEMA = {
    "category": "One line: category + what the app does.",
    "auth": "Auth method(s): OAuth2, API key, Basic, token, or other. Be specific if mixed.",
    "gating": "Self-serve vs gated: can a developer get credentials themselves free/trial, "
              "or does it need a paid plan, admin approval, or a partner/contact-sales gate?",
    "api_surface": "Documented public REST/GraphQL? Roughly how broad? Any existing MCP server (official or community)?",
    "verdict": "Buildability verdict: Ready / Ready-friction / Blocked, plus the main blocker if not Ready.",
    "evidence": "The docs URL / article behind each answer. Never invent a URL.",
    "confidence": "Your own confidence in this row: verified / high / medium / low. "
                  "Say 'low' honestly if you're guessing or the app defeated you.",
}

RESEARCH_SYSTEM_PROMPT = f"""You are an API research agent for Composio. Before Composio builds an agent \
toolkit for an app, you research it. For the given app, fill in this JSON schema exactly:
{json.dumps(FIELD_SCHEMA, indent=2)}

Rules:
- If you are not sure, say so and mark confidence "low" - do NOT fabricate a docs URL or invent an auth method.
- Prefer the app's own official developer docs domain as evidence.
- Keep each field to 1-2 sentences max.
Return ONLY valid JSON with keys: category, auth, gating, api_surface, verdict, blocker, evidence, confidence."""

VERIFY_SYSTEM_PROMPT = """You are the VERIFIER in a two-pass research pipeline. You will be given an app, \
a docs URL, and a DRAFT answer produced by the research pass. Your job:
1. Actually fetch/read the docs URL (use your web tool).
2. Re-derive each field from what the live page actually says.
3. Return JSON: {"verified": {...same schema...}, "matches_draft": true/false, "diff_notes": "what changed and why, or 'confirmed' if nothing changed"}
Be skeptical of the draft - your whole job is to catch when it's wrong, not to agree with it."""


@dataclass
class AppRow:
    id: int
    name: str
    hint: str
    result: Optional[dict] = field(default=None)
    verify: Optional[dict] = field(default=None)
    error: Optional[str] = field(default=None)


def load_apps(path: str) -> list[AppRow]:
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(AppRow(id=int(r["#"]), name=r["App"], hint=r.get("Website / hint", "")))
    return rows


def _extract_json(text: str) -> dict:
    """Pull the first well-formed top-level JSON object out of a model response.

    More robust than a naive find('{')/rfind('}') slice: it walks brace depth so
    it doesn't get confused by braces inside string values or trailing commentary
    the model adds after the JSON block.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object found in model output")
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unterminated JSON object in model output")


def _call_with_retries(client, **kwargs):
    """Call the Messages API with limited retries and graceful rate-limit handling."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.messages.create(**kwargs)
        except Exception as e:  # noqa: BLE001 - deliberately broad, this is a resilience wrapper
            last_err = e
            is_rate_limit = "rate" in str(e).lower() and "limit" in str(e).lower()
            wait = RETRY_BACKOFF_SECONDS * attempt * (3 if is_rate_limit else 1)
            print(f"  [retry {attempt}/{MAX_RETRIES}] {type(e).__name__}: {e} - waiting {wait}s",
                  file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(wait)
    raise last_err


def research_pass(client, app: AppRow) -> dict:
    """Pass 1: research one app and return the structured schema."""
    msg = _call_with_retries(
        client,
        model=MODEL,
        max_tokens=800,
        system=RESEARCH_SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"App: {app.name}\nHint: {app.hint}\nResearch it now."}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return _extract_json(text)


def verify_pass(client, app: AppRow, draft: dict) -> dict:
    """Pass 2: force a live docs fetch and diff against the draft."""
    msg = _call_with_retries(
        client,
        model=MODEL,
        max_tokens=1000,
        system=VERIFY_SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": f"App: {app.name}\nDraft docs URL: {draft.get('evidence')}\nDraft answer: {json.dumps(draft)}\n"
                       f"Fetch the real docs and verify.",
        }],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return _extract_json(text)


def run_live(apps_path: str, out_path: str, verify_sample: int, seed, limit):
    if anthropic is None:
        print("The 'anthropic' package isn't installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Export it first, or use --demo for a no-credential run.",
              file=sys.stderr)
        sys.exit(1)

    apps = load_apps(apps_path)
    if limit:
        apps = apps[:limit]
    client = anthropic.Anthropic()

    # Pass 1: research every app, continuing past individual failures.
    failed = 0
    for app in apps:
        print(f"[research] {app.name}...", file=sys.stderr)
        try:
            app.result = research_pass(client, app)
        except Exception as e:  # noqa: BLE001
            failed += 1
            app.error = f"{type(e).__name__}: {e}"
            app.result = {"confidence": "low", "verdict": "Blocked - agent could not complete research",
                          "blocker": "Research pass failed; see 'error' field", "evidence": ""}
            print(f"  [error] {app.name}: {app.error}", file=sys.stderr)
            print(f"  [trace] {traceback.format_exc(limit=1)}", file=sys.stderr)

    # Pass 2: verify a sample - every "low"-confidence row first, topped up with a
    # seeded random batch so the sample is reproducible across runs.
    rng = random.Random(seed)
    low_conf = [a for a in apps if a.result and a.result.get("confidence") == "low"]
    remaining = [a for a in apps if a not in low_conf]
    rng.shuffle(remaining)
    sample = (low_conf + remaining)[:verify_sample]

    confirmed = 0
    corrected = 0
    verify_failed = 0
    for app in sample:
        print(f"[verify] {app.name}...", file=sys.stderr)
        try:
            app.verify = verify_pass(client, app, app.result)
            if app.verify.get("matches_draft", True):
                confirmed += 1
            else:
                corrected += 1
        except Exception as e:  # noqa: BLE001
            verify_failed += 1
            app.verify = {"error": f"{type(e).__name__}: {e}"}
            print(f"  [error] verify {app.name}: {e}", file=sys.stderr)

    checked = confirmed + corrected
    print(f"\nVerification sample: {len(sample)} apps ({verify_failed} failed to verify). "
          f"First-pass agreement: {confirmed}/{max(checked, 1)} confirmed on first read, "
          f"{corrected}/{max(checked, 1)} required correction or added nuance after checking the live docs.",
          file=sys.stderr)
    if failed:
        print(f"Research pass failures: {failed}/{len(apps)} apps could not be researched "
              f"and were marked low-confidence / Blocked instead of guessed.", file=sys.stderr)

    with open(out_path, "w") as f:
        json.dump([asdict(a) for a in apps], f, indent=2)
    print(f"Wrote {out_path}")


def run_demo():
    """No-credential demo/replay mode.

    Loads a small fixed sample of apps, prints the research schema, and replays
    the existing verification examples from data/verification.py so the
    draft -> verify workflow is visible without an API key. This never makes a
    live LLM call and never presents replayed results as freshly researched.
    """
    print("=" * 72)
    print("DEMO / REPLAY MODE - no live LLM calls, no web search performed")
    print("=" * 72)

    here = os.path.dirname(os.path.abspath(__file__))
    apps_csv = os.path.join(here, "apps.csv")
    sample_apps = load_apps(apps_csv)[:5] if os.path.exists(apps_csv) else []

    print(f"\nLoaded {len(sample_apps)} apps from apps.csv for the demo:")
    for a in sample_apps:
        print(f"  #{a.id:>3}  {a.name}")

    print("\nResearch schema each app is scored against (pass 1):")
    print(json.dumps(FIELD_SCHEMA, indent=2))

    print("\nWorkflow shape (draft -> sample -> verify):")
    print("  1. research_pass(app)  -> structured JSON draft + self-rated confidence")
    print("  2. sample selection    -> every 'low'-confidence row + a seeded random top-up")
    print("  3. verify_pass(app, draft) -> forced live-docs fetch, diffed against the draft")

    ver_path = os.path.join(os.path.dirname(here), "data", "verification.py")
    if os.path.exists(ver_path):
        sys.path.insert(0, os.path.join(os.path.dirname(here), "data"))
        try:
            from verification import SAMPLE, summarize  # type: ignore
            s = summarize()
            print(f"\n[REPLAY] Existing verification sample ({s['total']} apps reviewed against live docs "
                  f"during the research session - not re-fetched now):")
            for row in SAMPLE[:3]:
                print(f"  - {row['app']} / {row['field']}: {row['result']}")
            print(f"  ...({s['total'] - 3} more in data/verification.py)")
            print(f"  {s['confirmed']} confirmed on first pass, {s['corrected']} required correction - "
                  f"see data/verification.py and the case study for the full, labeled sample.")
        except Exception as e:  # noqa: BLE001
            print(f"\n(Could not load data/verification.py for replay: {e})")

    print("\nThis mode never calls a live model and never claims a fresh research run happened.")
    print("For a real (small, cheap) live test: python pipeline.py --apps apps.csv --limit 3 --verify-sample 1")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Composio app-research agent (research + verification pipeline)")
    p.add_argument("--apps", default="apps.csv", help="CSV with columns #, App, Website / hint")
    p.add_argument("--out", default="results.json")
    p.add_argument("--verify-sample", type=int, default=20, help="How many apps to run through the verify pass")
    p.add_argument("--seed", type=int, default=None, help="Random seed for the verification sample (reproducible runs)")
    p.add_argument("--limit", type=int, default=None, help="Only process the first N apps (safe for testing)")
    p.add_argument("--demo", action="store_true",
                    help="No-credential demo/replay mode - shows the schema and replays existing verification examples")
    p.add_argument("--dry-run", action="store_true",
                    help="Deprecated alias for --demo, kept for backward compatibility")
    args = p.parse_args()

    if args.demo or args.dry_run:
        run_demo()
    else:
        run_live(args.apps, args.out, args.verify_sample, args.seed, args.limit)

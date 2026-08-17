# -*- coding: utf-8 -*-
import sys, json, html, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data'))
from apps_data import APPS
from verification import SAMPLE, summarize
import importlib
import analyze as analyze_mod
importlib.reload(analyze_mod)

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, 'data', 'analysis.json')) as f:
    A = json.load(f)

VER_SUMMARY = summarize()

VERDICT_CLASS = {"Ready": "v-ready", "Ready-friction": "v-friction", "Blocked": "v-blocked"}
VERDICT_LABEL = {"Ready": "Ready", "Ready-friction": "Ready \u2014 friction", "Blocked": "Blocked"}
CONF_CLASS = {"verified": "c-verified", "high": "c-high", "medium": "c-medium", "low": "c-low"}

def esc(s):
    return html.escape(str(s), quote=True)

def render_row(a):
    return f"""<tr class="app-row" data-verdict="{a['verdict']}" data-category="{esc(a['category'])}" data-confidence="{a['confidence']}" data-name="{esc(a['name'].lower())}">
  <td class="col-id">{a['id']}</td>
  <td class="col-name"><strong>{esc(a['name'])}</strong><span class="blurb">{esc(a['blurb'])}</span></td>
  <td class="col-cat">{esc(a['category'])}</td>
  <td class="col-auth">{esc(a['auth'])}</td>
  <td class="col-gating">{esc(a['gating'])}</td>
  <td class="col-api">{esc(a['api_surface'])}<span class="breadth">{esc(a['breadth'])}</span></td>
  <td class="col-mcp">{esc(a['mcp'])}</td>
  <td class="col-verdict"><span class="chip {VERDICT_CLASS[a['verdict']]}">{VERDICT_LABEL[a['verdict']]}</span>{f'<span class="blocker-note">{esc(a["blocker"])}</span>' if a['blocker'] else ''}</td>
  <td class="col-conf"><span class="chip conf {CONF_CLASS[a['confidence']]}">{a['confidence']}</span></td>
  <td class="col-evidence">{f'<a href="{esc(a["evidence"])}" target="_blank" rel="noopener">' + esc(a['evidence'].split('//')[-1].split('/')[0]) + ' \u2197</a>' if a['evidence'] and a['evidence'].startswith('http') else '<span class="no-evidence">no public source found</span>'}</td>
</tr>"""

rows_html = "\n".join(render_row(a) for a in APPS)

def render_verify_row(s):
    result_class = "diff-corrected" if s["result"].startswith("Corrected") else "diff-confirmed"
    return f"""<tr class="{result_class}">
  <td><strong>{esc(s['app'])}</strong><div class="vfield">{esc(s['field'])}</div></td>
  <td class="vcell">{esc(s['first_pass'])}</td>
  <td class="vcell">{esc(s['verified'])}</td>
  <td><span class="chip {'v-friction' if s['result'].startswith('Corrected') else 'v-ready'}">{esc(s['result'])}</span></td>
  <td class="vcell why">{esc(s.get('why', ''))}</td>
</tr>"""

verify_rows_html = "\n".join(render_verify_row(s) for s in SAMPLE)

cat_order = list(dict.fromkeys(a['category'] for a in APPS))
def cat_bar(cat):
    stats = A['cat_stats'][cat]
    total = sum(stats.values())
    ss = stats.get('Self-serve', 0)
    pct = round(ss/total*100)
    return f"""<div class="catrow">
  <div class="catname">{esc(cat)}</div>
  <div class="catbar"><div class="catbar-fill" style="width:{pct}%"></div></div>
  <div class="catpct">{ss}/{total} self-serve</div>
</div>"""

cat_bars_html = "\n".join(cat_bar(c) for c in cat_order)

blocked_list_html = "\n".join(
    f'<li><strong>{esc(b["name"])}</strong> <span class="cat-tag">{esc(b["category"])}</span><br><span class="blk-text">{esc(b["blocker"])}</span></li>'
    for b in A['blocked_apps']
)

low_conf_html = ", ".join(f"<strong>{esc(n)}</strong>" for n in A['low_confidence'])

easy_wins = [a['name'] for a in APPS if a['verdict']=='Ready' and a['mcp'].lower().startswith('yes')]
easy_wins_html = ", ".join(esc(n) for n in easy_wins[:18]) + (f" \u2014 and {len(easy_wins)-18} more" if len(easy_wins) > 18 else "")

blocker_theme_rows = "\n".join(
    f'<div class="btrow"><div class="btbar" style="width:{round(v/max(A["blocker_themes"].values())*100)}%"></div><div class="btlabel">{esc(k)} <span class="btcount">{v}</span></div></div>'
    for k, v in A['blocker_themes'].items()
)

# ---- Tier framework (Section 02) — derived directly from the existing `verdict`
# field already in the dataset. No separate priority score is invented; the
# tiers are exactly Ready / Ready-friction / Blocked, reframed operationally.
tier1 = [a for a in APPS if a['verdict'] == 'Ready']
tier2 = [a for a in APPS if a['verdict'] == 'Ready-friction']
tier3 = [a for a in APPS if a['verdict'] == 'Blocked']

def name_list(apps_list, limit=14):
    names = [a['name'] for a in apps_list]
    shown = ", ".join(esc(n) for n in names[:limit])
    rest = len(names) - limit
    return shown + (f" \u2014 and {rest} more" if rest > 0 else "")

# OAuth2 stat, computed rather than hardcoded
oauth_count = sum(1 for a in APPS if 'oauth2' in a['auth'].lower())
apikey_only_count = sum(1 for a in APPS if 'oauth2' not in a['auth'].lower() and
                         ('api key' in a['auth'].lower() or 'token' in a['auth'].lower() or 'bearer' in a['auth'].lower()))
no_api_count = sum(1 for a in APPS if a['api_surface'].lower().startswith('none'))
mcp_names_sample = [a['name'] for a in APPS if a['mcp'].lower().startswith('yes')][:12]

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Composio App Research \u2014 100-App Buildability Audit</title>
<style>
:root {{
  --paper: #F1F2EE;
  --panel: #FFFFFF;
  --ink: #14171A;
  --ink-soft: #4B5058;
  --line: #D9DBD3;
  --brand: #2B4C8C;
  --brand-soft: #E7ECF5;
  --ready: #1F7A4D;
  --ready-bg: #E4F3EA;
  --friction: #A9691A;
  --friction-bg: #FBEEDD;
  --blocked: #B23A2E;
  --blocked-bg: #FBE7E4;
  --mono: 'IBM Plex Mono', 'SF Mono', Consolas, monospace;
  --sans: 'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0; background: var(--paper); color: var(--ink);
  font-family: var(--sans); line-height: 1.5; font-size: 15px;
}}
a {{ color: var(--brand); }}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 0 28px; }}
header.hero {{
  border-bottom: 1px solid var(--line); padding: 56px 0 40px; background: var(--panel);
}}
.eyebrow {{
  font-family: var(--mono); text-transform: uppercase; letter-spacing: 0.12em; font-size: 12px;
  color: var(--brand); margin-bottom: 14px; display:flex; gap: 10px; align-items:center;
}}
.eyebrow .dot {{ width:7px; height:7px; border-radius:50%; background: var(--brand); display:inline-block; }}
h1 {{ font-size: 40px; line-height: 1.12; margin: 0 0 14px; font-weight: 700; letter-spacing: -0.01em; }}
.hero-sub {{ font-size: 17px; color: var(--ink-soft); max-width: 760px; margin: 0 0 30px; }}
.stat-row {{ display: flex; gap: 0; border: 1px solid var(--line); border-radius: 10px; overflow: hidden; flex-wrap: wrap; }}
.stat {{ flex: 1; min-width: 150px; padding: 18px 20px; border-right: 1px solid var(--line); }}
.stat:last-child {{ border-right: none; }}
.stat .n {{ font-family: var(--mono); font-size: 30px; font-weight: 700; color: var(--brand); }}
.stat .l {{ font-size: 12.5px; color: var(--ink-soft); margin-top: 2px; }}

nav.toc {{
  position: sticky; top: 0; z-index: 50; background: rgba(241,242,238,0.94); backdrop-filter: blur(6px);
  border-bottom: 1px solid var(--line); font-family: var(--mono); font-size: 13px;
}}
nav.toc .wrap {{ display: flex; gap: 22px; padding: 12px 28px; overflow-x: auto; }}
nav.toc a {{ color: var(--ink-soft); text-decoration: none; white-space: nowrap; }}
nav.toc a:hover {{ color: var(--brand); }}

section {{ padding: 48px 0; border-bottom: 1px solid var(--line); }}
section h2 {{
  font-family: var(--mono); font-size: 13px; text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--brand); margin: 0 0 6px;
}}
section h3.headline {{ font-size: 25px; font-weight: 700; margin: 0 0 26px; max-width: 800px; letter-spacing: -0.01em; }}

.pattern-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 22px; margin-top: 8px; }}
@media (max-width: 860px) {{ .pattern-grid {{ grid-template-columns: 1fr; }} }}
.tier-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 8px; }}
@media (max-width: 980px) {{ .tier-grid {{ grid-template-columns: 1fr; }} }}
.card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 22px 24px; }}
.card h4 {{ margin: 0 0 14px; font-size: 14px; font-family: var(--mono); text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink); }}
.tier-card {{ border-top: 4px solid var(--line); }}
.tier-card.t1 {{ border-top-color: var(--ready); }}
.tier-card.t2 {{ border-top-color: var(--friction); }}
.tier-card.t3 {{ border-top-color: var(--blocked); }}
.tier-count {{ font-family: var(--mono); font-size: 26px; font-weight: 700; margin-bottom: 4px; }}
.t1 .tier-count {{ color: var(--ready); }}
.t2 .tier-count {{ color: var(--friction); }}
.t3 .tier-count {{ color: var(--blocked); }}
.tier-crit {{ font-size: 12.5px; color: var(--ink-soft); margin: 0 0 12px; }}
.tier-examples {{ font-size: 12.5px; color: var(--ink-soft); }}

.catrow {{ display: grid; grid-template-columns: 190px 1fr 110px; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 13.5px; }}
.catname {{ color: var(--ink-soft); }}
.catbar {{ background: var(--brand-soft); border-radius: 5px; height: 16px; overflow: hidden; }}
.catbar-fill {{ background: var(--brand); height: 100%; border-radius: 5px 0 0 5px; }}
.catpct {{ font-family: var(--mono); font-size: 12px; text-align: right; color: var(--ink-soft); }}

.btrow {{ position: relative; margin-bottom: 12px; }}
.btbar {{ background: var(--friction-bg); border-left: 3px solid var(--friction); height: 30px; border-radius: 4px; }}
.btlabel {{ position: absolute; left: 12px; top: 6px; font-size: 13px; }}
.btcount {{ font-family: var(--mono); color: var(--friction); font-weight: 700; margin-left: 6px; }}

.verdict-legend {{ display:flex; gap:16px; margin: 18px 0 6px; flex-wrap: wrap; font-size: 13px; }}
.chip {{
  display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-family: var(--mono);
  font-weight: 600;
}}
.v-ready {{ background: var(--ready-bg); color: var(--ready); }}
.v-friction {{ background: var(--friction-bg); color: var(--friction); }}
.v-blocked {{ background: var(--blocked-bg); color: var(--blocked); }}
.chip.conf {{ font-weight: 500; }}
.c-verified {{ background: #E4F3EA; color: #1F7A4D; }}
.c-high {{ background: #EDEEF2; color: #4B5058; }}
.c-medium {{ background: #FBEEDD; color: #A9691A; }}
.c-low {{ background: #FBE7E4; color: #B23A2E; }}

.agent-flow {{ display: flex; align-items: stretch; gap: 0; margin: 26px 0; flex-wrap: wrap; }}
.flow-step {{
  flex: 1; min-width: 190px; background: var(--panel); border: 1px solid var(--line); padding: 18px 18px;
  position: relative; border-radius: 10px; margin-right: 26px; margin-bottom: 14px;
}}
.flow-step:not(:last-child)::after {{
  content: "\\2192"; position: absolute; right: -24px; top: 50%; transform: translateY(-50%);
  font-size: 20px; color: var(--brand); font-family: var(--mono);
}}
.flow-step .fn {{ font-family: var(--mono); font-size: 11px; color: var(--brand); text-transform:uppercase; letter-spacing:0.08em; }}
.flow-step h5 {{ margin: 6px 0 6px; font-size: 15px; }}
.flow-step p {{ margin: 0; font-size: 13px; color: var(--ink-soft); }}

.honesty-box {{
  background: #FBEEDD; border: 1px solid #E9CB9C; border-radius: 12px; padding: 20px 24px; margin-top: 18px;
}}
.honesty-box h4 {{ margin: 0 0 8px; font-size: 14px; font-family: var(--mono); color: var(--friction); text-transform: uppercase;}}
.method-note {{
  background: var(--brand-soft); border: 1px solid #C9D4E8; border-radius: 10px; padding: 14px 18px;
  font-size: 13px; color: var(--ink-soft); margin-top: 20px;
}}
.method-note strong {{ color: var(--ink); }}

table.vtable {{ width: 100%; border-collapse: collapse; font-size: 13.5px; margin-top: 18px; }}
table.vtable th {{ text-align: left; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-soft); padding: 8px 12px; border-bottom: 2px solid var(--line); }}
table.vtable td {{ padding: 12px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
.vfield {{ font-size: 11.5px; color: var(--ink-soft); font-family: var(--mono); margin-top: 2px; }}
.vcell {{ color: var(--ink-soft); font-size: 13px; }}
.vcell.why {{ font-size: 12px; font-style: italic; }}
tr.diff-corrected {{ background: #FDF9F2; }}

.controls {{ display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }}
.controls input, .controls select {{
  font-family: var(--sans); font-size: 13.5px; padding: 8px 12px; border: 1px solid var(--line);
  border-radius: 8px; background: var(--panel); color: var(--ink);
}}
.controls input {{ flex: 1; min-width: 200px; }}
.count-note {{ font-family: var(--mono); font-size: 12px; color: var(--ink-soft); margin-left: auto; }}

.tablewrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; background: var(--panel); }}
table.apptable {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 1100px; }}
table.apptable th {{
  position: sticky; top: 45px; background: #FAFAF7; text-align: left; font-family: var(--mono); font-size: 10.5px;
  text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink-soft); padding: 10px 12px;
  border-bottom: 2px solid var(--line); cursor: pointer; user-select: none;
}}
table.apptable th:hover {{ color: var(--brand); }}
table.apptable td {{ padding: 11px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
table.apptable tr:hover {{ background: #FAFAF7; }}
.col-id {{ color: var(--ink-soft); font-family: var(--mono); font-size: 12px; }}
.col-name strong {{ display: block; }}
.blurb {{ display: block; font-size: 11.5px; color: var(--ink-soft); margin-top: 2px; max-width: 220px; }}
.breadth {{ display: block; font-size: 11px; color: var(--ink-soft); margin-top: 2px; }}
.blocker-note {{ display: block; font-size: 11px; color: var(--ink-soft); margin-top: 4px; max-width: 200px; }}
.col-evidence a {{ font-family: var(--mono); font-size: 12px; text-decoration: none; white-space: nowrap; }}
.no-evidence {{ font-family: var(--mono); font-size: 11px; color: var(--blocked); }}

.pill-row {{ display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}
.pill {{
  font-family: var(--mono); font-size: 12px; padding: 6px 14px; border-radius: 20px; border: 1px solid var(--line);
  background: var(--panel); cursor: pointer; color: var(--ink-soft);
}}
.pill.active {{ background: var(--ink); color: var(--paper); border-color: var(--ink); }}

footer {{ padding: 40px 0 70px; font-size: 13px; color: var(--ink-soft); }}
footer a {{ color: var(--brand); }}
.foot-grid {{ display: flex; gap: 40px; flex-wrap: wrap; }}
code {{ background: var(--brand-soft); padding: 1px 6px; border-radius: 4px; font-family: var(--mono); font-size: 12px; }}
pre code {{ background: none; padding: 0; }}
</style>
</head>
<body>

<header class="hero">
  <div class="wrap">
    <div class="eyebrow"><span class="dot"></span> COMPOSIO &middot; AI PRODUCT OPS TAKE-HOME &middot; APP RESEARCH CASE STUDY</div>
    <h1>100 apps, mapped for agent-toolkit readiness.<br>66 are buildable today.</h1>
    <p class="hero-sub">An AI-assisted research pipeline maps auth, gating, API surface and MCP availability
    across 100 real apps, then uses targeted source verification to catch first-pass mistakes before they'd
    ship into a toolkit decision. Every wrong first guess found in verification is shown below, not hidden.</p>
    <div class="stat-row">
      <div class="stat"><div class="n">66</div><div class="l">Ready today, no friction</div></div>
      <div class="stat"><div class="n">23</div><div class="l">Ready, but with a hoop to jump</div></div>
      <div class="stat"><div class="n">11</div><div class="l">Blocked \u2014 needs outreach/contract</div></div>
      <div class="stat"><div class="n">{oauth_count}/100</div><div class="l">Use OAuth2 (alone or mixed)</div></div>
      <div class="stat"><div class="n">{A['mcp_yes']}/100</div><div class="l">Already have an MCP server</div></div>
      <div class="stat"><div class="n">7</div><div class="l">Low-confidence \u2014 flagged for human follow-up</div></div>
    </div>
  </div>
</header>

<nav class="toc"><div class="wrap">
  <a href="#patterns">What the research says</a>
  <a href="#build-first">Where to build first</a>
  <a href="#agent">The agent</a>
  <a href="#verification">Verification</a>
  <a href="#honesty">Human handoff</a>
  <a href="#table">Full matrix (100)</a>
  <a href="#repro">Methodology &amp; repo</a>
</div></nav>

<section id="patterns">
  <div class="wrap">
    <h2>01 &middot; What the research says</h2>
    <h3 class="headline">Self-serve access is the norm ({A['gating_counts'].get('Self-serve', 0)}/100) \u2014 but
    "self-serve" and "buildable today" are different questions. A quarter of apps need a review, a paid tier,
    or an approved account on top of self-serve signup, and 11 have no public path in at all.</h3>

    <div class="pattern-grid">
      <div class="card">
        <h4>Pattern 1 &middot; Auth is usually solvable; access policy is the real blocker</h4>
        <p style="font-size:13.5px;">OAuth2 and API-key auth together cover the overwhelming majority of the
        set \u2014 the auth <em>mechanism</em> is rarely the hard part. What actually determines buildability is
        access policy layered on top: paid tiers, enterprise-only accounts, approval flows, and partner gates.
        DealCloud and Salesforce Commerce Cloud both use ordinary OAuth2, but neither has a public signup at all.</p>
      </div>
      <div class="card">
        <h4>Pattern 2 &middot; A documented API doesn't mean an easy toolkit</h4>
        <p style="font-size:13.5px;">A stable, well-documented REST API (Brex, Ramp, Ahrefs, Google Ads) can
        still carry real friction from account-tier requirements, app-review processes, production approval, or
        rate limits. "Has an API" and "Ready" are correlated but not the same field \u2014 that gap is most of
        what separates the 66 Ready rows from the 23 Ready-friction ones.</p>
      </div>
    </div>

    <div class="pattern-grid" style="margin-top:22px;">
      <div class="card">
        <h4>Pattern 3 &middot; MCP changes the integration path, where it exists</h4>
        <p style="font-size:13.5px;">{A['mcp_yes']}/100 apps already ship an MCP server (official or credible
        community build) \u2014 concentrated in developer/infra tools (GitHub, Cloudflare, Supabase, Vercel),
        CRM/support (HubSpot, Attio, Zendesk, Intercom, Twenty) and newer AI-native tools (Devin, Consensus,
        Apify, Firecrawl, Bright Data). Where MCP exists, Composio's opportunity may be a different integration
        (or a wrapper/aggregation play) rather than building a REST connector from scratch. {A['mcp_none']} apps
        have no MCP at all \u2014 that's most of the addressable set still needing the MCP layer built.</p>
      </div>
      <div class="card">
        <h4>Pattern 4 &middot; Easy wins cluster in mature, self-serve APIs</h4>
        <p style="font-size:13.5px;">The cleanest buildable rows share a shape: documented API, self-serve
        credentials, predictable auth (usually OAuth2 or a plain API key), broad surface, and low operational
        friction. These aren't evenly spread \u2014 they concentrate in Developer &amp; Infra, Productivity &amp;
        PM, and CRM &amp; Sales, where the product category itself assumes an API-literate developer audience.</p>
      </div>
    </div>

    <div class="pattern-grid" style="margin-top:22px;">
      <div class="card">
        <h4>Pattern 5 &middot; Some apps need outreach, not more scraping</h4>
        <p style="font-size:13.5px;">7 rows stayed low-confidence after the research pass \u2014 mostly small,
        low-visibility vendors with no real developer-docs footprint in search results. More searching doesn't
        fix that; a human contacting the vendor does. Treating these as an outreach queue, not a research
        failure, is itself part of the finding \u2014 see Section 05.</p>
      </div>
      <div class="card">
        <h4>What actually blocks the other 34 apps</h4>
        {blocker_theme_rows}
      </div>
    </div>

    <div class="pattern-grid" style="margin-top:22px;">
      <div class="card">
        <h4>Self-serve rate by category</h4>
        {cat_bars_html}
      </div>
      <div class="card">
        <h4>Auth &amp; MCP shape of the set</h4>
        <p style="font-size:13.5px;">{oauth_count}/100 apps use OAuth2 (alone or mixed with an API key/token) as
        at least one auth path; {apikey_only_count}/100 more use API-key/token-only auth \u2014 together that's
        the large majority of the set on just two auth shapes, which matters for how generic Composio's
        connector plumbing can be. Only {no_api_count} apps (local CLI tools, not services) have no API surface
        at all.</p>
        <p style="font-size:13.5px;">{A['mcp_yes']}/100 apps already have an MCP server; {A['mcp_none']}/100
        have none.</p>
      </div>
    </div>
  </div>
</section>

<section id="build-first">
  <div class="wrap">
    <h2>02 &middot; Where to build first</h2>
    <h3 class="headline">Three tiers, derived directly from the buildability verdict already in the dataset \u2014
    no separate priority score, just the same field reframed as a build queue.</h3>
    <div class="tier-grid">
      <div class="card tier-card t1">
        <h4>Tier 1 &middot; Easy wins</h4>
        <div class="tier-count">{len(tier1)}</div>
        <p class="tier-crit">Broad API + self-serve credentials + clean, predictable auth + low operational
        friction. Buildable today with no extra approval step.</p>
        <p class="tier-examples">{name_list(tier1)}</p>
      </div>
      <div class="card tier-card t2">
        <h4>Tier 2 &middot; Buildable with known friction</h4>
        <div class="tier-count">{len(tier2)}</div>
        <p class="tier-crit">The API exists and access is achievable, but a tier upgrade, app review, approved
        account, or extra setup step sits between "signed up" and "calling the API."</p>
        <p class="tier-examples">{name_list(tier2)}</p>
      </div>
      <div class="card tier-card t3">
        <h4>Tier 3 &middot; Outreach required</h4>
        <div class="tier-count">{len(tier3)}</div>
        <p class="tier-crit">Partner-gated, enterprise-only, no public signup, or the API surface couldn't be
        confirmed at all. These need a conversation with the vendor before engineering starts.</p>
        <p class="tier-examples">{name_list(tier3)}</p>
      </div>
    </div>
    <p style="font-size:13px;color:var(--ink-soft);margin-top:18px;max-width:800px;">Sequencing follows the
    tiers directly: Tier 1 needs no external dependency and should be first in any build queue; Tier 2 is a
    scheduling/ops problem (who requests the approval, how long it takes); Tier 3 is a business-development
    problem, not an engineering one, until a self-serve or partner path opens up.</p>
  </div>
</section>

<section id="agent">
  <div class="wrap">
    <h2>03 &middot; The agent</h2>
    <h3 class="headline">A two-pass pipeline: research everything first, then force a skeptical second pass to
    actually read the docs for anything uncertain.</h3>
    <div class="agent-flow">
      <div class="flow-step"><div class="fn">Pass 1</div><h5>Research pass</h5>
        <p>For each app, an LLM with a web-search tool fills the 8-field schema (category, auth, gating, API
        surface, MCP, verdict, blocker, evidence) and self-rates its own confidence: verified / high / medium /
        low.</p></div>
      <div class="flow-step"><div class="fn">Sampling</div><h5>Pick what to check</h5>
        <p>Every "low"-confidence row is auto-included. The rest is topped up with a seeded, reproducible
        spot-check batch, so the verification budget goes where the pipeline is least sure, not spread evenly.</p></div>
      <div class="flow-step"><div class="fn">Pass 2</div><h5>Verification pass</h5>
        <p>A second, deliberately skeptical pass is <em>forced</em> to fetch the real docs URL and re-derive
        each field from the live page \u2014 not from the draft \u2014 then diffs its answer against pass 1.</p></div>
      <div class="flow-step"><div class="fn">Output</div><h5>Reviewed dataset</h5>
        <p>Verified corrections overwrite the draft. Anything still uncertain stays tagged <code>low</code> on
        the page below instead of being smoothed over.</p></div>
    </div>
    <div class="card" style="margin-top:8px;">
      <h4>Where human review was needed</h4>
      <p style="font-size:13.5px;">Two situations the pipeline can't fully resolve on its own: (1)
      <strong>low-visibility vendors</strong> with no real developer-docs footprint in search results \u2014
      fanbasis, Waterfall.io, Paygent Connect, iPayX, MrScraper, higgsfield \u2014 where the honest output is
      "couldn't confirm, low confidence" rather than a guess; and (2) <strong>judgment calls that read as simple
      but aren't</strong>, like Consensus (gated raw API <em>but</em> a free self-serve MCP path exists side by
      side) or Devin (self-serve signup, but the real gate is paid usage credits, not account access). Those
      needed a human reading the nuance in the verification pass and deciding which label was more useful, rather
      than forcing a single self-serve/gated flag onto a genuinely split answer.</p>
    </div>
    <div class="method-note">
      <strong>Research methodology:</strong> AI-assisted two-pass workflow with source-backed verification.
      The submitted dataset was assembled during the research session using this methodology; the Python
      implementation in the repository (<code>agent/pipeline.py</code>) provides the reproducible agent
      workflow for reruns against live docs with your own credentials \u2014 see Section 07.
    </div>
  </div>
</section>

<section id="verification">
  <div class="wrap">
    <h2>04 &middot; Verify your accuracy</h2>
    <h3 class="headline">On an 11-app spot-check sample, the research pass's first read was confirmed on
    {VER_SUMMARY['confirmed']}/{VER_SUMMARY['total']} judgment calls \u2014 the other
    {VER_SUMMARY['corrected']} needed a real correction or added nuance after checking the actual docs.</h3>
    <p style="max-width:800px;font-size:14px;color:var(--ink-soft);">This is the loop the brief asks for: draft,
    then cross-check against real docs, then report hits and misses honestly. This measures first-pass agreement
    and correction rate on this reviewed sample \u2014 it is not a statistical accuracy claim about the other 89
    rows in the full dataset. The corrections below aren't typos \u2014 they're exactly the kind of "looks
    simple, isn't" nuance a single-pass read misses: MCP existing but paywalled, an API existing but gated, a
    product assumed dead that's actually fine.</p>
    <div class="pattern-grid" style="margin-top:18px;max-width:640px;">
      <div class="card" style="text-align:center;">
        <div class="tier-count" style="color:var(--ink);">{VER_SUMMARY['total']}</div>
        <p class="tier-crit">apps verified against live docs</p>
      </div>
      <div class="card" style="text-align:center;">
        <div class="tier-count" style="color:var(--ready);">{VER_SUMMARY['confirmed']}</div>
        <p class="tier-crit">confirmed on first pass</p>
      </div>
      <div class="card" style="text-align:center;">
        <div class="tier-count" style="color:var(--friction);">{VER_SUMMARY['corrected']}</div>
        <p class="tier-crit">required correction or added nuance</p>
      </div>
    </div>
    <div class="tablewrap" style="margin-top:16px;">
      <table class="vtable">
        <thead><tr><th style="width:14%">App / field checked</th><th style="width:26%">First-pass assumption</th><th style="width:26%">What the live docs actually show</th><th style="width:14%">Result</th><th style="width:20%">Why it mattered</th></tr></thead>
        <tbody>
          {verify_rows_html}
        </tbody>
      </table>
    </div>
    <p style="font-size:13px;color:var(--ink-soft);margin-top:14px;">The verification loop caught multiple
    material errors and ambiguities that a single-pass read could have shipped without noticing \u2014 that's
    the case for running a verification pass at all, independent of the exact percentage on any one sample.</p>
  </div>
</section>

<section id="honesty">
  <div class="wrap">
    <h2>05 &middot; Human handoff</h2>
    <h3 class="headline">Where the pipeline got it wrong, or an app defeated it \u2014 said plainly, not buried.</h3>
    <div class="honesty-box">
      <h4>7 apps: low confidence, flagged rather than guessed</h4>
      <p style="font-size:13.5px;">{low_conf_html} \u2014 either no real public developer-docs footprint could
      be found (Waterfall.io, fanbasis, Paygent Connect, iPayX), the product's actual public API couldn't be
      confirmed at all (Pumble \u2014 only bot/webhook docs surfaced, no general REST API), or the finding just
      wasn't independently re-verified against live docs this session and shouldn't be taken as more certain
      than it is (MrScraper, higgsfield). These are marked <span class="chip conf c-low">low</span> in the table
      below rather than smoothed into a confident-looking row.</p>
      <p style="font-size:13px;margin-top:10px;">A low-confidence label is preferable to a fabricated answer. In
      production, these rows become a human follow-up queue, not a dead end: contact the vendor directly, request
      developer access, spin up a trial account, or request docs that aren't publicly indexed. These are not
      failures to hide \u2014 they're the cases where automated research should hand off to a human.</p>
    </div>
    <p style="max-width:800px;font-size:13.5px;margin-top:18px;color:var(--ink-soft);">More broadly: most of the
    100 rows rest on strong, stable training knowledge of well-documented mainstream APIs (Stripe, GitHub,
    Shopify, Slack, etc.) rather than a live doc-fetch in this session \u2014 tagged <span class="chip conf c-high">high</span>
    confidence, not <span class="chip conf c-verified">verified</span>. The rows tagged
    <span class="chip conf c-verified">verified</span> in the full table (including the 11 in the verification
    sample above) were actually cross-checked against a live page during this research pass. A production
    version of this pipeline would verify all 100, not 11 \u2014 the sample here is sized to fit the assignment's
    time budget while still demonstrating a real, honest verification loop rather than a token gesture at one.</p>
  </div>
</section>

<section id="table">
  <div class="wrap">
    <h2>06 &middot; The findings \u2014 all 100 apps</h2>
    <h3 class="headline">Sortable, filterable, and machine-readable \u2014 click any column header to sort, or
    filter by verdict/category below.</h3>
    <div class="verdict-legend">
      <span class="chip v-ready">Ready</span><span style="color:var(--ink-soft);font-size:13px;">no blocker, buildable now</span>
      <span class="chip v-friction">Ready \u2014 friction</span><span style="color:var(--ink-soft);font-size:13px;">buildable, but needs approval / paid tier / extra setup</span>
      <span class="chip v-blocked">Blocked</span><span style="color:var(--ink-soft);font-size:13px;">no public self-serve path today</span>
    </div>
    <div class="pill-row" id="verdictPills">
      <button class="pill active" data-verdict="all">All 100</button>
      <button class="pill" data-verdict="Ready">Ready ({len(tier1)})</button>
      <button class="pill" data-verdict="Ready-friction">Friction ({len(tier2)})</button>
      <button class="pill" data-verdict="Blocked">Blocked ({len(tier3)})</button>
      <button class="pill" data-conf="low">Low confidence (7)</button>
    </div>
    <div class="controls">
      <input type="text" id="searchBox" placeholder="Filter by app name, category, auth method...">
      <select id="catFilter"><option value="all">All categories</option></select>
      <span class="count-note" id="countNote">showing 100 / 100</span>
    </div>
    <div class="tablewrap">
      <table class="apptable" id="appTable">
        <thead>
          <tr>
            <th data-key="id">#</th>
            <th data-key="name">App</th>
            <th data-key="category">Category</th>
            <th data-key="auth">Auth</th>
            <th data-key="gating">Self-serve / gated</th>
            <th data-key="api_surface">API surface</th>
            <th data-key="mcp">MCP</th>
            <th data-key="verdict">Buildability</th>
            <th data-key="confidence">Confidence</th>
            <th>Evidence</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="repro" style="border-bottom:none;">
  <div class="wrap">
    <h2>07 &middot; Methodology &amp; repro</h2>
    <h3 class="headline">The agent, the dataset, and this page are generated from the same source \u2014
    nothing here was typed twice.</h3>
    <div class="pattern-grid">
      <div class="card">
        <h4>What's in the repo</h4>
        <p style="font-size:13.5px;"><code>data/apps_data.py</code> \u2014 the 100-row dataset (every field
        above, plus confidence tags)<br><br>
        <code>data/analyze.py</code> \u2014 computes the pattern stats shown in Section 01<br><br>
        <code>data/verification.py</code> \u2014 the 11-app first-pass-vs-verified sample in Section 04<br><br>
        <code>agent/pipeline.py</code> \u2014 the runnable research + verification agent<br><br>
        <code>generate_html.py</code> \u2014 builds this exact page from the files above</p>
      </div>
      <div class="card">
        <h4>Run the agent yourself</h4>
        <pre style="font-family:var(--mono);font-size:12px;background:#FAFAF7;padding:14px;border-radius:8px;overflow-x:auto;"># No credentials needed
python agent/pipeline.py --demo

# Small live test (real API calls, 3 apps)
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python agent/pipeline.py --apps agent/apps.csv \\
  --limit 3 --verify-sample 1

# Full run
python agent/pipeline.py --apps agent/apps.csv \\
  --out results.json --verify-sample 20 --seed 42</pre>
        <p style="font-size:13px;color:var(--ink-soft);">Full explanation of the two-pass design, and how this
        submission's dataset relates to the runnable pipeline, is in the repo's <code>README.md</code>.</p>
      </div>
    </div>
  </div>
</section>

<footer><div class="wrap">
  <div class="foot-grid">
    <div><strong>Composio AI Product Ops Intern \u2014 take-home submission</strong><br>Researched using an
    AI-assisted two-pass workflow (research pass + source-backed verification pass), with human review on
    ambiguous and low-confidence rows.</div>
    <div>Source repo: <code>see README.md in submission</code><br>Data: <code>data/apps_data.py</code> (100 rows, machine-readable)</div>
  </div>
</div></footer>

<script id="app-json" type="application/json">{json.dumps(APPS)}</script>
<script>
const DATA = JSON.parse(document.getElementById('app-json').textContent);
const tbody = document.querySelector('#appTable tbody');
const rows = Array.from(document.querySelectorAll('.app-row'));
const catFilter = document.getElementById('catFilter');
const cats = [...new Set(DATA.map(a => a.category))];
cats.forEach(c => {{ const o = document.createElement('option'); o.value = c; o.textContent = c; catFilter.appendChild(o); }});

let state = {{ verdict: 'all', conf: 'all', cat: 'all', q: '' }};

function applyFilters() {{
  let visible = 0;
  rows.forEach(r => {{
    const okV = state.verdict === 'all' || r.dataset.verdict === state.verdict;
    const okConf = state.conf === 'all' || r.dataset.confidence === state.conf;
    const okC = state.cat === 'all' || r.dataset.category === state.cat;
    const okQ = !state.q || r.dataset.name.includes(state.q) || r.textContent.toLowerCase().includes(state.q);
    const show = okV && okConf && okC && okQ;
    r.style.display = show ? '' : 'none';
    if (show) visible++;
  }});
  document.getElementById('countNote').textContent = `showing ${{visible}} / 100`;
}}

document.getElementById('verdictPills').addEventListener('click', e => {{
  if (e.target.tagName !== 'BUTTON') return;
  document.querySelectorAll('#verdictPills .pill').forEach(p => p.classList.remove('active'));
  e.target.classList.add('active');
  if (e.target.dataset.verdict) {{
    state.verdict = e.target.dataset.verdict;
    state.conf = 'all';
  }} else if (e.target.dataset.conf) {{
    state.conf = e.target.dataset.conf;
    state.verdict = 'all';
  }}
  applyFilters();
}});
catFilter.addEventListener('change', e => {{ state.cat = e.target.value; applyFilters(); }});
document.getElementById('searchBox').addEventListener('input', e => {{ state.q = e.target.value.toLowerCase(); applyFilters(); }});

// Sortable columns
let sortDir = {{}};
document.querySelectorAll('#appTable th[data-key]').forEach(th => {{
  th.addEventListener('click', () => {{
    const key = th.dataset.key;
    sortDir[key] = !sortDir[key];
    const sorted = [...rows].sort((a, b) => {{
      let av = a.dataset[key] || a.children[[...th.parentNode.children].indexOf(th)].textContent;
      let bv = b.dataset[key] || b.children[[...th.parentNode.children].indexOf(th)].textContent;
      if (key === 'id') {{ av = +a.children[0].textContent; bv = +b.children[0].textContent; }}
      return sortDir[key] ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
    }});
    sorted.forEach(r => tbody.appendChild(r));
  }});
}});
</script>
</body>
</html>
"""

out_path = os.path.join(HERE, 'output', 'case_study.html')
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w') as f:
    f.write(HTML)

print(f"Wrote {out_path} ({len(HTML):,} bytes)")

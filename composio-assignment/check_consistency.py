# -*- coding: utf-8 -*-
"""Final internal consistency check for the submission. Run after any edit to
data/apps_data.py, data/verification.py, or generate_html.py."""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'data'))
from apps_data import APPS
from verification import SAMPLE, summarize

errors = []
warnings = []

def check(cond, msg, bucket=errors):
    if not cond:
        bucket.append(msg)

# 1-2: exactly 100 apps, ids 1-100 complete
check(len(APPS) == 100, f"Expected 100 apps, found {len(APPS)}")
ids = sorted(a['id'] for a in APPS)
check(ids == list(range(1, 101)), "App IDs are not exactly 1..100 with no gaps/dupes")

# 4: verdict counts sum to 100
verdicts = [a['verdict'] for a in APPS]
check(len(verdicts) == 100, "Verdict count does not sum to 100")
check(set(verdicts) <= {"Ready", "Ready-friction", "Blocked"}, "Unexpected verdict value present")

# 5: confidence counts sum to 100
confs = [a['confidence'] for a in APPS]
check(len(confs) == 100, "Confidence count does not sum to 100")
check(set(confs) <= {"verified", "high", "medium", "low"}, "Unexpected confidence value present")

# 6/7: analysis.json matches dataset
analysis_path = os.path.join(HERE, 'data', 'analysis.json')
if os.path.exists(analysis_path):
    with open(analysis_path) as f:
        A = json.load(f)
    mcp_yes_live = sum(1 for a in APPS if a['mcp'].lower().startswith('yes'))
    check(A.get('mcp_yes') == mcp_yes_live,
          f"analysis.json mcp_yes ({A.get('mcp_yes')}) != live count ({mcp_yes_live})")
    check(A.get('ready_count') == verdicts.count('Ready'), "analysis.json ready_count mismatch")
    check(A.get('friction_count') == verdicts.count('Ready-friction'), "analysis.json friction_count mismatch")
    check(A.get('blocked_count') == verdicts.count('Blocked'), "analysis.json blocked_count mismatch")
    live_low = sorted(a['name'] for a in APPS if a['confidence'] == 'low')
    check(sorted(A.get('low_confidence', [])) == live_low, "analysis.json low_confidence list mismatch")
else:
    warnings.append("data/analysis.json not found — run data/analyze.py first")

# 9: verification summary matches verification.py itself (sanity, always true, but check field consistency)
vs = summarize()
check(vs['total'] == len(SAMPLE), "verification summary total mismatch")
check(vs['confirmed'] + vs['corrected'] == vs['total'], "verification confirmed+corrected != total")

# 10/11: no forbidden phrases in generated HTML
html_path = os.path.join(HERE, 'output', 'case_study.html')
if os.path.exists(html_path):
    with open(html_path, encoding='utf-8') as f:
        page = f.read()
    forbidden = [
        "100% accuracy", "100% factual accuracy",
        "I (Claude)", "Claude manually", "this sandbox", "the assistant",
        "the model knew", "I personally", "in the chat session",
    ]
    for phrase in forbidden:
        check(phrase.lower() not in page.lower(), f"Forbidden phrase found in case_study.html: {phrase!r}")
    check("pipeline.py generated" not in page.lower(),
          "HTML implies pipeline.py literally generated the dataset")
else:
    warnings.append("output/case_study.html not found — run generate_html.py first")

# 12: no obvious secrets committed
for root, dirs, files in os.walk(HERE):
    dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules')]
    for fn in files:
        if fn in ('.env',) or fn.endswith('.key'):
            errors.append(f"Possible secret file committed: {os.path.join(root, fn)}")
        if fn.endswith('.py') or fn.endswith('.html') or fn.endswith('.md'):
            p = os.path.join(root, fn)
            try:
                with open(p, encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                if re.search(r"sk-ant-[a-zA-Z0-9]{10,}", content):
                    errors.append(f"Possible live API key committed in {p}")
            except Exception:
                pass

# 13: evidence URLs preserved (either a real URL or explicitly flagged as none found)
missing_evidence = [a['name'] for a in APPS if not a['evidence']]
check(not missing_evidence, f"Apps with no evidence field at all: {missing_evidence}")

print(f"Checked {len(APPS)} apps.")
print(f"Verdicts: Ready={verdicts.count('Ready')} Ready-friction={verdicts.count('Ready-friction')} Blocked={verdicts.count('Blocked')}")
print(f"Confidence: {dict((c, confs.count(c)) for c in set(confs))}")
print(f"Verification sample: {vs}")

if warnings:
    print(f"\n{len(warnings)} warning(s):")
    for w in warnings:
        print(f"  - {w}")

if errors:
    print(f"\n{len(errors)} ERROR(S):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("\nAll consistency checks passed.")

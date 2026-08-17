import json, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from apps_data import APPS

def bucket_auth(a):
    a = a.lower()
    if 'oauth2' in a and ('api key' in a or 'token' in a or 'basic' in a):
        return 'OAuth2 + API key/token (mixed)'
    if 'oauth2' in a:
        return 'OAuth2'
    if 'api key' in a or 'api token' in a or 'bearer' in a:
        return 'API key / token'
    if 'basic' in a:
        return 'Basic auth'
    if 'none' in a:
        return 'None (no API)'
    return 'Other'

def bucket_gating(g):
    g = g.lower()
    if g.startswith('self-serve'):
        return 'Self-serve'
    if g.startswith('gated'):
        return 'Gated'
    if g.startswith('mixed'):
        return 'Mixed'
    if g.startswith('split'):
        return 'Split (varies by access path)'
    if g.startswith('unclear') or g.startswith('likely'):
        return 'Unclear/Unverified'
    return 'Other'

auth_counts = collections.Counter(bucket_auth(a['auth']) for a in APPS)
gating_counts = collections.Counter(bucket_gating(a['gating']) for a in APPS)
verdict_counts = collections.Counter(a['verdict'] for a in APPS)
mcp_yes = sum(1 for a in APPS if a['mcp'].lower().startswith('yes'))
mcp_none = sum(1 for a in APPS if a['mcp'].lower().startswith('none'))
mcp_other = 100 - mcp_yes - mcp_none

confidence_counts = collections.Counter(a['confidence'] for a in APPS)

# category-level self-serve vs gated
cat_stats = collections.defaultdict(lambda: collections.Counter())
for a in APPS:
    cat_stats[a['category']][bucket_gating(a['gating'])] += 1

# Blocked apps and their blockers
blocked = [a for a in APPS if a['verdict'] == 'Blocked']
friction = [a for a in APPS if a['verdict'] == 'Ready-friction']
ready = [a for a in APPS if a['verdict'] == 'Ready']

# common blocker themes (keyword bucket on blocker text)
blocker_themes = collections.Counter()
for a in APPS:
    b = a['blocker'].lower()
    if not b:
        continue
    if 'contact' in b or 'sales-led' in b or 'enterprise contract' in b or 'no public signup' in b or 'no self-serve' in b:
        blocker_themes['Contact-sales / enterprise-only gate'] += 1
    elif 'approval' in b or 'review' in b:
        blocker_themes['Platform approval/review process'] += 1
    elif 'paid plan' in b or 'paid subscription' in b or 'upgrade' in b or 'credits' in b or 'free plan has no api' in b:
        blocker_themes['Paywalled tier (API not on free/entry plan)'] += 1
    elif 'no api' in b or 'cli' in b or 'no rest' in b or "no public, documented" in b:
        blocker_themes['No real API surface (CLI-only / webhook-only)'] += 1
    elif 'could not locate' in b or 'low-visibility' in b or 'not independently' in b:
        blocker_themes['Agent could not find docs (needs human research)'] += 1
    elif 'approved' in b and 'account' in b:
        blocker_themes['Requires being an existing paying customer'] += 1
    else:
        blocker_themes['Other/nuanced'] += 1

result = dict(
    total=len(APPS),
    auth_counts=dict(auth_counts.most_common()),
    gating_counts=dict(gating_counts.most_common()),
    verdict_counts=dict(verdict_counts.most_common()),
    mcp_yes=mcp_yes, mcp_none=mcp_none, mcp_other=mcp_other,
    confidence_counts=dict(confidence_counts.most_common()),
    cat_stats={k: dict(v) for k, v in cat_stats.items()},
    blocker_themes=dict(blocker_themes.most_common()),
    blocked_apps=[dict(name=a['name'], category=a['category'], blocker=a['blocker']) for a in blocked],
    friction_apps=[dict(name=a['name'], category=a['category'], blocker=a['blocker']) for a in friction],
    ready_count=len(ready), friction_count=len(friction), blocked_count=len(blocked),
    low_confidence=[a['name'] for a in APPS if a['confidence'] == 'low'],
)

with open(os.path.join(HERE, 'analysis.json'), 'w') as f:
    json.dump(result, f, indent=2)

with open(os.path.join(HERE, 'apps.json'), 'w') as f:
    json.dump(APPS, f, indent=2)

print(json.dumps(result, indent=2))

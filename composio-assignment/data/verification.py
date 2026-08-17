# -*- coding: utf-8 -*-
# Verification log: for an 11-app sample, what the research pass's FIRST-PASS
# assumption was vs what checking the real, live docs actually showed. This is
# the verification loop the assignment asks for: draft -> source-backed
# cross-check -> human read of the diff. It measures agreement/correction on
# this sample, not statistical ground truth for all 100 rows.

SAMPLE = [
    dict(app="Twenty CRM", field="MCP status",
         first_pass="Assumed: open-source, self-hosted, probably no MCP yet.",
         verified="Has a native MCP server - but it ships on the paid Cloud Pro tier, not the free self-hosted install.",
         result="Corrected", evidence="https://twenty.com/",
         why="A 'has MCP' checkbox would have overstated readiness for the free self-hosted path most developers actually use."),
    dict(app="Podio", field="Is it even still alive?",
         first_pass="Assumed: likely stale/deprecated - old product, bounced between Citrix and Progress Software.",
         verified="Still live and fully self-serve. Docs are dated (2012-era design) but the API and OAuth flow work today.",
         result="Corrected", evidence="https://developers.podio.com/",
         why="Would have wrongly dropped a viable, self-serve app from the buildable set based on an age assumption."),
    dict(app="DealCloud", field="Gating",
         first_pass="Assumed: gated, enterprise PE/IB tool, no free signup.",
         verified="Confirmed gated - OAuth2 client-credentials, but only for existing paying clients with admin-enabled API access.",
         result="Confirmed", evidence="https://api.docs.dealcloud.com/docs/apikeys",
         why="Confirms the blocker is real and specific enough to act on (needs an existing client site, not just a signup)."),
    dict(app="Pylon", field="Auth + MCP",
         first_pass="Assumed: Bearer token, self-serve, probably has an MCP given the AI-support angle.",
         verified="Confirmed - Bearer API token, self-serve dashboard token generation, and \"Pylon MCP\" is in their own docs nav.",
         result="Confirmed", evidence="https://docs.usepylon.com/pylon-docs/developer/api/authentication",
         why="A clean confirm - good sanity check that the first pass isn't wrong by default."),
    dict(app="GoHighLevel", field="Auth model",
         first_pass="Assumed: single OAuth2 flow, self-serve.",
         verified="Self-serve confirmed, but it's actually two coexisting systems: a legacy API key (v1, now EOL) and OAuth2 (v2, current) - agent needed to catch the version split.",
         result="Corrected (added nuance)", evidence="https://highlevel.stoplight.io/docs/integrations/0443d7d1a4bd0-overview",
         why="A toolkit built against the wrong auth version would break for some accounts still on legacy keys."),
    dict(app="Otter.ai", field="Gating",
         first_pass="Assumed: has an official MCP server, so probably self-serve like most MCP integrations.",
         verified="MCP exists but Otter's own help center says \"we currently do not have a public API key at this time\" - REST API is Enterprise-plan only.",
         result="Corrected", evidence="https://help.otter.ai/hc/en-us/articles/35287607569687-Otter-MCP-Server",
         why="Shows that 'has an MCP' does not imply self-serve - the two fields need to be checked independently."),
    dict(app="Fathom", field="Gating + auth",
         first_pass="Assumed: self-serve API key, since most AI-notetaker startups open their API to all users.",
         verified="Confirmed - public API + webhooks, any user can generate a key at fathom.video/api_settings.",
         result="Confirmed", evidence="https://developers.fathom.ai/",
         why="Confirms a category-level heuristic (AI-notetaker startups tend to be self-serve) held up here."),
    dict(app="Consensus", field="Gating",
         first_pass="Assumed: fully gated - it's an academic-research data product, those are usually contact-sales.",
         verified="Split finding the first pass missed entirely: the raw REST API IS gated (apply, ~$0.10/call), but Consensus also ships a free, self-serve MCP server that needs no account for basic use.",
         result="Corrected (missed the self-serve path)", evidence="https://docs.consensus.app/docs/mcp",
         why="A single self-serve/gated flag would have hidden a real, free integration path via MCP."),
    dict(app="Devin", field="Gating",
         first_pass="Assumed: fully gated/enterprise-only, expensive AI-engineer product.",
         verified="Actually self-serve to sign up and get API/MCP keys - the real gate is that running sessions burns paid credits (ACUs), not account access itself.",
         result="Corrected", evidence="https://docs.devin.ai/work-with-devin/devin-mcp",
         why="Distinguishes 'gated to sign up' from 'gated to use at volume' - different blockers with different fixes."),
    dict(app="Grain", field="Gating",
         first_pass="Assumed: self-serve, since the token is self-generated from account settings.",
         verified="Actually gated - API access requires the Starter plan or above; the Free plan has no API access at all.",
         result="Corrected", evidence="https://developers.grain.com/",
         why="Shows that a self-service token UI doesn't guarantee the underlying plan includes API access at all."),
    dict(app="Airtable", field="MCP status",
         first_pass="Assumed: MCP probably exists but might just be community-built, not official.",
         verified="Confirmed official - Airtable ships and maintains its own MCP server at mcp.airtable.com.",
         result="Confirmed (upgraded confidence)", evidence="https://support.airtable.com/docs/using-the-airtable-mcp-server",
         why="Upgrades confidence from 'probably' to 'verified' - relevant since official vs community MCP changes the integration bet."),
]

# Tally. Terms are deliberately conservative: this is a first-pass agreement /
# correction rate on an 11-app sample, not a statistical accuracy claim about
# the full 100-app dataset.
def summarize():
    total = len(SAMPLE)
    corrected = sum(1 for s in SAMPLE if s["result"].startswith("Corrected"))
    confirmed = total - corrected
    return dict(total=total, corrected=corrected, confirmed=confirmed,
                first_pass_agreement_pct=round(confirmed/total*100),
                reviewed_pct=100)  # 100% of the *sample* was reviewed against live docs -
                                   # not a claim about the other 89 rows

if __name__ == "__main__":
    import json
    print(json.dumps(dict(sample=SAMPLE, summary=summarize()), indent=2))

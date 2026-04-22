---
name: ads-linkedin-launch
description: "Programmatically create LinkedIn ad campaigns (Campaign Groups, Campaigns, Creatives, Lead Gen Forms) from a campaign-brief.md. Reads the `## LinkedIn Launch Config` YAML section, validates it, previews the exact API payloads, then creates everything in Campaign Manager via the linkedin-ads MCP server. Triggers on: launch LinkedIn campaign, push to LinkedIn, create LinkedIn ads, publish LinkedIn campaign, ship LinkedIn ads, deploy LinkedIn campaign."
user-invokable: true
---

# Ads LinkedIn Launch: Programmatic Campaign Creation

Turns a `campaign-brief.md` (with a `## LinkedIn Launch Config` YAML section)
into live Campaign Groups, Campaigns, Creatives, and Lead Gen Forms in
LinkedIn Campaign Manager via the `linkedin-ads` MCP server.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/ads linkedin-launch` | Full pipeline on `./campaign-brief.md` (dry-run first, then confirm) |
| `/ads linkedin-launch <path>` | Launch from a specific brief file |
| `/ads linkedin-launch --plan` | Show the API payloads, never call the network |
| `/ads linkedin-launch --activate` | After confirm, create in ACTIVE status (default: DRAFT) |

## Prerequisites

1. **LinkedIn Marketing Developer Platform access** — see
   `ads/references/linkedin-api.md` for the application process (5-15 business days).
2. **`linkedin-ads` MCP server configured** in `.mcp.json` or `~/.claude.json`.
   See `mcp/linkedin-ads/README.md`.
3. **A `campaign-brief.md` with a `## LinkedIn Launch Config` section.**
   Generate one via `/ads create --platforms linkedin` or author manually using
   `ads/references/linkedin-launch-brief-schema.md`.

## Process

### Step 1: Verify MCP Server is Available

Check whether `linkedin-ads` MCP tools (`mcp__linkedin-ads__parse_brief`, etc.)
are connected in the current session.

If not connected, show the user this message and stop:

```
The linkedin-ads MCP server is not configured. To enable /ads linkedin-launch:

1. Add linkedin-ads to your .mcp.json (see mcp/linkedin-ads/README.md)
2. Provide LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_ACCESS_TOKEN,
   LINKEDIN_AD_ACCOUNT_ID in the env block
3. Restart Claude Code

Don't have API access yet? See ads/references/linkedin-api.md for the
Marketing Developer Platform application process.
```

### Step 2: Locate the Brief

1. If the user passed a path, use it.
2. Otherwise look for `./campaign-brief.md` in the current directory.
3. If not found, ask whether to run `/ads create --platforms linkedin` first.

### Step 3: Parse & Validate

Call the MCP tool `parse_brief` with the resolved path. If it returns an error
(missing `## LinkedIn Launch Config` section, invalid YAML), surface the error
and offer to either:
- Run `/ads create --platforms linkedin` to generate a draft section
- Show `ads/references/linkedin-launch-brief-schema.md` as a template

Then call `validate_brief_tool`. Present any errors and warnings:

```
Brief validation:
  Errors: [count]
  Warnings: [count]

Errors (must fix before launch):
  - ...

Warnings (review):
  - ...
```

Stop on errors. On warnings, ask the user whether to proceed.

### Step 4: Dry-Run Preview

Call `plan_launch_tool`. Present the payload summary in a readable way:

```
Dry-run preview:

Campaign Group: "Q2 2026 - Enterprise Demand Gen"
  Total budget: $10,000
  Schedule: 2026-05-01 → 2026-05-31
  Status on create: DRAFT

Campaign 1: "Q2 - Sr Marketing - Lead Gen"
  Objective: LEAD_GENERATION
  Format: SPONSORED_UPDATES
  Daily budget: $250
  Bid: MAX_DELIVERY (CPM)
  Targeting: US • Marketing Manager/Director/VP • Software + Financial Services •
             Companies 1K-10K+ employees
  Creatives: 2 single-image ads
  Lead Gen Form: "Demo Request Q2" (5 fields)

Would create 1 campaign group, 1 campaign, 2 creatives, 1 lead gen form.
Total daily spend ceiling: $250 (under $500 safety limit).

Proceed with launch? [yes / plan-only / cancel]
```

### Step 5: Execute (Requires User Confirmation)

On explicit user confirmation, call `launch_from_brief_tool` with:
- `confirm: true`
- `activate: false` (default — objects created in DRAFT)
- `activate: true` only if the user passed `--activate` **and** confirmed
  they understand it will start spending immediately

**Never** pass `activate: true` without the `--activate` flag from the user.

### Step 6: Report Results

On success, present:

```
Launch complete:

Campaign Group:
  "Q2 2026 - Enterprise Demand Gen" (urn:li:sponsoredCampaignGroup:123456)
  → https://www.linkedin.com/campaignmanager/accounts/789/campaign-groups/123456

Campaigns:
  ✓ "Q2 - Sr Marketing - Lead Gen" (urn:li:sponsoredCampaign:789012)
    - 2 creatives created
    - Lead Gen Form: "Demo Request Q2" (urn:li:leadGenForm:345)
    → https://www.linkedin.com/campaignmanager/accounts/789/campaigns/789012

Status: DRAFT (review in Campaign Manager, then flip to ACTIVE)

Next steps:
  1. Open the Campaign Manager links above to review
  2. Verify targeting, creatives, and budgets look correct
  3. Toggle status to ACTIVE in the UI (or re-run with --activate)
```

On failure, surface the error from the MCP tool and, when relevant:
- Offer to call `refresh_access_token` if error is 401
- Suggest specific fixes for common errors (audience too small, image format, etc.)

## Safety Rules (Never Violate)

1. **Default to DRAFT** — only create in ACTIVE when user explicitly passes
   `--activate` and confirms.
2. **Always dry-run first** — present payloads to user before any write.
3. **Respect the budget ceiling** — the MCP server enforces
   `LINKEDIN_DAILY_BUDGET_MAX` (default $500/day). Do not suggest the user
   override it without reason.
4. **Never log tokens** — do not echo the LINKEDIN_ACCESS_TOKEN value in
   responses. The MCP server already redacts it.
5. **Confirm activation** — if the user says "launch it", that means create
   in DRAFT. It does NOT mean activate. Ask separately before activating.

## Integration with Other /ads Commands

Chains naturally with existing commands:

```
/ads dna <url>                    → brand-profile.json
/ads create --platforms linkedin  → campaign-brief.md with LinkedIn Launch Config
/ads generate --platform linkedin → ad-assets/linkedin/...png
/ads linkedin-launch              → live campaigns in Campaign Manager
```

## Input Document Handling (Client Briefs)

When the user has a client-provided document (e.g. `client-brief.docx`,
`client-brief.md`, or pasted text), convert it to a `## LinkedIn Launch Config`
section before launching:

1. Read the client doc using the Read tool
2. Map client requirements to the schema in
   `ads/references/linkedin-launch-brief-schema.md`:
   - Budget → `campaign_group.total_budget_usd`
   - Audience description → `targeting.include.{job_titles,seniorities,industries}`
   - Goal → `campaigns[].objective`
   - Offer → `creatives[].headline` + `lead_gen_form`
3. Append the YAML section to `campaign-brief.md` and confirm with the user
   before running validate/plan/launch

## MCP Tools Used

- `parse_brief(brief_path)` → parsed YAML dict
- `validate_brief_tool(brief_path)` → errors + warnings
- `plan_launch_tool(brief_path)` → dry-run payloads
- `launch_from_brief_tool(brief_path, confirm, activate)` → live creation
- `list_campaigns(limit)` → post-launch verification
- `resolve_targeting(facet, query)` → human-readable → URN lookup
- `refresh_access_token()` → renew expired tokens

## Reference Files

- `ads/references/linkedin-api.md`: API endpoints, OAuth setup, scopes
- `ads/references/linkedin-launch-brief-schema.md`: full YAML schema reference
- `ads/references/linkedin-creative-specs.md`: image dimensions, copy limits
- `mcp/linkedin-ads/README.md`: MCP server install and configuration

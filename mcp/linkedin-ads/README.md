# LinkedIn Ads MCP Server

Model Context Protocol server that lets Claude Code programmatically create
LinkedIn ad campaigns by calling the LinkedIn Marketing API.

Used by the `/ads linkedin-launch` skill to turn a `campaign-brief.md` containing
a `## LinkedIn Launch Config` section into live campaigns in Campaign Manager.

## Install

```bash
pip install -r requirements.txt
```

Requirements: Python 3.10+, `mcp`, `httpx`, `pyyaml`.

## Configure

Add to your `.mcp.json` (project-scoped) or `~/.claude.json`:

```json
{
  "mcpServers": {
    "linkedin-ads": {
      "command": "python",
      "args": ["-m", "linkedin_ads_mcp.server"],
      "cwd": "/absolute/path/to/claude-ads/mcp/linkedin-ads",
      "env": {
        "LINKEDIN_CLIENT_ID": "...",
        "LINKEDIN_CLIENT_SECRET": "...",
        "LINKEDIN_ACCESS_TOKEN": "...",
        "LINKEDIN_AD_ACCOUNT_ID": "123456789",
        "LINKEDIN_DAILY_BUDGET_MAX": "500"
      }
    }
  }
}
```

See `ads/references/linkedin-api.md` for how to obtain these credentials
(requires LinkedIn Marketing Developer Platform approval).

## Tools Exposed

| Tool | Purpose | Mutates |
|------|---------|---------|
| `parse_brief` | Parse `## LinkedIn Launch Config` from a markdown file | No |
| `validate_brief` | Run all schema and safety checks on a parsed brief | No |
| `plan_launch` | Dry-run: return the exact API payloads that would be sent | No |
| `resolve_targeting` | Resolve job titles / locations / industries to URNs | No |
| `estimate_audience` | Query LinkedIn for audience size estimate | No |
| `create_campaign_group` | Create a campaign group | Yes (requires confirm=true) |
| `create_campaign` | Create a campaign under a group | Yes (requires confirm=true) |
| `upload_image` | Upload an image asset | Yes (requires confirm=true) |
| `create_creative` | Create a creative bound to a campaign | Yes (requires confirm=true) |
| `create_lead_gen_form` | Create a Lead Gen Form | Yes (requires confirm=true) |
| `launch_from_brief` | End-to-end: parse brief, validate, and create everything | Yes (requires confirm=true) |
| `list_campaigns` | List campaigns in the ad account | No |
| `refresh_access_token` | Exchange refresh token for new access token | No |

## Safety Defaults

- All mutating tools default to **dry-run** (`confirm=false`)
- Every create starts in `DRAFT` status unless `activate=true` is passed
- Daily budget exceeding `LINKEDIN_DAILY_BUDGET_MAX` is rejected
- Access token never appears in logs or tool responses
- 429 responses trigger exponential backoff (2s/4s/8s/16s)

## Typical Claude Flow

```
1. User: "Launch this LinkedIn campaign"  (points at campaign-brief.md)
2. Claude: tool call → parse_brief       → JSON of LinkedIn Launch Config
3. Claude: tool call → validate_brief    → PASS or list of errors
4. Claude: tool call → plan_launch       → preview of API calls
5. Claude shows preview to user for approval
6. Claude: tool call → launch_from_brief(confirm=true, activate=false)
7. Returns campaign URNs + Campaign Manager deep links
8. User reviews in LinkedIn UI, then flips to ACTIVE
```

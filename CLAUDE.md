# Claude Ads: Paid Advertising Audit & Optimization Skill

## Project Overview

This repository contains **Claude Ads**, a Tier 4 Claude Code skill for comprehensive
paid advertising analysis across all major platforms. It follows the Agent Skills open
standard and the 3-layer architecture (directive, orchestration, execution). 18 sub-skills,
10 agents (6 audit + 4 creative), 11 industry templates, and a LinkedIn Marketing API MCP
server cover Google, Meta, YouTube, LinkedIn, TikTok, Microsoft, and Apple Search Ads with
225+ weighted audit checks plus programmatic LinkedIn campaign creation.

## Architecture

```
claude-ads/
  CLAUDE.md                          # Project instructions (this file)
  ads/                               # Main orchestrator skill
    SKILL.md                         # Entry point, routing table, core rules
    references/                      # On-demand knowledge files (23 files)
    scripts/                         # Python execution scripts
  skills/                            # 18 specialized sub-skills
    ads-audit/SKILL.md              # Full multi-platform audit
    ads-google/SKILL.md            # Google Ads deep analysis
    ads-meta/SKILL.md              # Meta/Facebook Ads analysis
    ads-youtube/SKILL.md           # YouTube Ads analysis
    ads-linkedin/SKILL.md         # LinkedIn Ads analysis
    ads-linkedin-launch/SKILL.md  # Programmatic LinkedIn campaign creation (MCP)
    ads-tiktok/SKILL.md           # TikTok Ads analysis
    ads-microsoft/SKILL.md        # Microsoft/Bing Ads analysis
    ads-creative/SKILL.md         # Creative quality assessment
    ads-landing/SKILL.md          # Landing page analysis
    ads-budget/SKILL.md           # Budget allocation optimization
    ads-plan/SKILL.md             # Strategic ad planning by industry
    ads-competitor/SKILL.md       # Competitor ad research
  mcp/
    linkedin-ads/                  # MCP server: LinkedIn Marketing API wrapper
      src/linkedin_ads_mcp/        # brief_parser, validator, launcher, server
      README.md
      requirements.txt
  agents/                            # 10 agents (6 audit + 4 creative)
    audit-google.md                # Google Ads audit agent
    audit-meta.md                  # Meta Ads audit agent
    audit-creative.md              # Creative quality agent
    audit-tracking.md              # Conversion tracking agent
    audit-budget.md                # Budget analysis agent
    audit-compliance.md            # Compliance verification agent
  install.sh / install.ps1          # Cross-platform installers
  uninstall.sh / uninstall.ps1      # Cross-platform uninstallers
```

## Commands

| Command | Purpose |
|---------|---------|
| `/ads audit` | Full multi-platform audit with 6 parallel agents |
| `/ads google` | Google Ads deep analysis |
| `/ads meta` | Meta/Facebook Ads analysis |
| `/ads youtube` | YouTube Ads analysis |
| `/ads linkedin` | LinkedIn Ads analysis |
| `/ads linkedin-launch` | Create LinkedIn campaigns from a brief via LinkedIn Marketing API MCP |
| `/ads tiktok` | TikTok Ads analysis |
| `/ads microsoft` | Microsoft/Bing Ads analysis |
| `/ads creative` | Creative quality and fatigue assessment |
| `/ads landing` | Landing page conversion analysis |
| `/ads budget` | Budget allocation optimization |
| `/ads plan <type>` | Strategic ad planning by industry |
| `/ads competitor` | Competitor ad research |

## Development Rules

- Keep SKILL.md files under 500 lines / 5000 tokens
- Reference files should be focused and under 200 lines
- Scripts must have docstrings, CLI interface, and JSON output
- Follow kebab-case naming for all skill directories
- Agents invoked via Task tool with `context: fork`, never via Bash
- No hardcoded credentials; use MCP servers for external API access
- Mutating MCP tools (campaign creation, etc.) default to dry-run and require
  explicit `confirm=true`; creates default to `DRAFT` status unless `activate=true`

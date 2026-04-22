"""MCP server entry point.

Exposes tools that parse, validate, plan, and (with explicit confirmation)
execute LinkedIn campaign launches from a campaign-brief.md.

Run as: `python -m linkedin_ads_mcp.server`
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .brief_parser import BriefParseError, parse_brief_file
from .config import ConfigError, load_config
from .launcher import launch_from_brief, plan_launch
from .linkedin_client import LinkedInAPIError, LinkedInClient
from .validator import validate_brief

logger = logging.getLogger("linkedin-ads-mcp")
mcp = FastMCP("linkedin-ads")


def _load_config_or_error() -> dict[str, Any] | None:
    try:
        return {"config": load_config()}
    except ConfigError as exc:
        return {"error": str(exc)}


@mcp.tool()
def parse_brief(brief_path: str) -> dict[str, Any]:
    """Parse the `## LinkedIn Launch Config` YAML block from a markdown file.

    Args:
        brief_path: Absolute or relative path to a campaign-brief.md.

    Returns:
        The parsed config as a dict, or {"error": ...} on failure.
    """
    try:
        return {"ok": True, "brief": parse_brief_file(brief_path)}
    except (BriefParseError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def validate_brief_tool(brief_path: str) -> dict[str, Any]:
    """Parse and validate a brief. Returns schema errors and safety warnings."""
    loaded = _load_config_or_error()
    if "error" in loaded:
        return {"ok": False, "error": loaded["error"]}
    try:
        brief = parse_brief_file(brief_path)
    except (BriefParseError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}
    report = validate_brief(
        brief,
        daily_budget_max_usd=loaded["config"].daily_budget_max_usd,
        brief_path=brief_path,
    )
    return report.to_dict()


@mcp.tool()
def plan_launch_tool(brief_path: str) -> dict[str, Any]:
    """Dry-run: return the exact API payloads that would be sent for each step.

    No network calls. Use this to review before calling launch_from_brief_tool.
    """
    loaded = _load_config_or_error()
    if "error" in loaded:
        return {"ok": False, "error": loaded["error"]}
    try:
        brief = parse_brief_file(brief_path)
    except (BriefParseError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}
    report = validate_brief(
        brief,
        daily_budget_max_usd=loaded["config"].daily_budget_max_usd,
        brief_path=brief_path,
    )
    plan = plan_launch(brief, loaded["config"])
    return {"ok": report.ok, "validation": report.to_dict(), "plan": plan}


@mcp.tool()
async def launch_from_brief_tool(
    brief_path: str,
    confirm: bool = False,
    activate: bool = False,
) -> dict[str, Any]:
    """Execute the full launch flow.

    Args:
        brief_path: Path to campaign-brief.md with LinkedIn Launch Config.
        confirm: Must be true to make any API calls. Default false (dry-run).
        activate: If true, creates objects in ACTIVE status. Default false
            (creates in DRAFT for manual review in Campaign Manager).

    Returns:
        On confirm=false: the same payload as plan_launch_tool.
        On confirm=true: URNs, IDs, and Campaign Manager deep links.
    """
    loaded = _load_config_or_error()
    if "error" in loaded:
        return {"ok": False, "error": loaded["error"]}
    config = loaded["config"]

    try:
        brief = parse_brief_file(brief_path)
    except (BriefParseError, FileNotFoundError) as exc:
        return {"ok": False, "error": str(exc)}

    report = validate_brief(
        brief, daily_budget_max_usd=config.daily_budget_max_usd, brief_path=brief_path
    )
    if not report.ok:
        return {"ok": False, "validation": report.to_dict()}

    if not confirm:
        plan = plan_launch(brief, config)
        return {
            "ok": True,
            "dry_run": True,
            "message": "Pass confirm=true to execute. Pass activate=true to create in ACTIVE status.",
            "validation": report.to_dict(),
            "plan": plan,
        }

    client = LinkedInClient(config)
    try:
        result = await launch_from_brief(
            brief, config, client, brief_path=brief_path, activate=activate
        )
        return {"ok": True, "dry_run": False, "result": result}
    except LinkedInAPIError as exc:
        return {"ok": False, "error": str(exc), "status": exc.status}
    finally:
        await client.close()


@mcp.tool()
async def list_campaigns(limit: int = 25) -> dict[str, Any]:
    """List existing campaigns in the configured ad account."""
    loaded = _load_config_or_error()
    if "error" in loaded:
        return {"ok": False, "error": loaded["error"]}
    client = LinkedInClient(loaded["config"])
    try:
        campaigns = await client.list_campaigns(limit=limit)
        return {"ok": True, "campaigns": campaigns}
    except LinkedInAPIError as exc:
        return {"ok": False, "error": str(exc), "status": exc.status}
    finally:
        await client.close()


@mcp.tool()
async def resolve_targeting(facet: str, query: str) -> dict[str, Any]:
    """Typeahead search for targeting URNs (job titles, industries, locations, etc.).

    Args:
        facet: One of TITLE, INDUSTRY, LOCATION, SKILL, EMPLOYER.
        query: Free-text search, e.g. "Marketing Manager".
    """
    loaded = _load_config_or_error()
    if "error" in loaded:
        return {"ok": False, "error": loaded["error"]}
    client = LinkedInClient(loaded["config"])
    try:
        results = await client.typeahead(facet, query)
        return {"ok": True, "results": results}
    except LinkedInAPIError as exc:
        return {"ok": False, "error": str(exc), "status": exc.status}
    finally:
        await client.close()


@mcp.tool()
async def refresh_access_token() -> dict[str, Any]:
    """Exchange the refresh token for a new access token.

    The new token is returned in the response; the caller (Claude) should
    update the env var or .mcp.json for subsequent server starts.
    """
    loaded = _load_config_or_error()
    if "error" in loaded:
        return {"ok": False, "error": loaded["error"]}
    client = LinkedInClient(loaded["config"])
    try:
        token_data = await client.refresh_access_token()
        return {
            "ok": True,
            "access_token": token_data.get("access_token"),
            "expires_in": token_data.get("expires_in"),
            "refresh_token": token_data.get("refresh_token"),
            "note": "Update LINKEDIN_ACCESS_TOKEN in .mcp.json or env, then restart.",
        }
    except LinkedInAPIError as exc:
        return {"ok": False, "error": str(exc), "status": exc.status}
    finally:
        await client.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run()


if __name__ == "__main__":
    main()

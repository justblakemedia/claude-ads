"""Brief → LinkedIn API payload translation + launch orchestration.

`plan_launch` returns the exact payloads that would be sent (no network calls).
`launch_from_brief` executes the full create flow when `confirm=true`.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config import LinkedInConfig

if TYPE_CHECKING:
    from .linkedin_client import LinkedInClient

_SENIORITY_FACET = "urn:li:adTargetingFacet:seniorities"
_TITLE_FACET = "urn:li:adTargetingFacet:titles"
_INDUSTRY_FACET = "urn:li:adTargetingFacet:industries"
_LOCATION_FACET = "urn:li:adTargetingFacet:locations"
_COMPANY_SIZE_FACET = "urn:li:adTargetingFacet:staffCountRanges"
_EMPLOYER_FACET = "urn:li:adTargetingFacet:employers"
_SKILL_FACET = "urn:li:adTargetingFacet:skills"


def _to_millis(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp() * 1000)


def _money(amount: float, currency: str) -> dict[str, str]:
    return {"currencyCode": currency, "amount": f"{amount}"}


def build_campaign_group_payload(
    brief: dict[str, Any], config: LinkedInConfig
) -> dict[str, Any]:
    group = brief["campaign_group"]
    payload: dict[str, Any] = {
        "account": config.ad_account_urn,
        "name": group["name"],
        "status": group.get("status", "DRAFT"),
        "totalBudget": _money(
            group["total_budget_usd"],
            group.get("currency", config.default_currency),
        ),
    }
    if group.get("start_date"):
        schedule: dict[str, int] = {"start": _to_millis(group["start_date"])}
        if group.get("end_date"):
            schedule["end"] = _to_millis(group["end_date"])
        payload["runSchedule"] = schedule
    return payload


def build_targeting_criteria(
    targeting: dict[str, Any], resolved_urns: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    """Build LinkedIn targetingCriteria from the brief's simple targeting dict.

    `resolved_urns` is an optional map of {facet_name: [urn, ...]} for facets
    where the caller has already resolved human-readable values to URNs. When
    absent, the raw values are passed through (dry-run friendly).
    """
    resolved_urns = resolved_urns or {}
    include = targeting.get("include") or {}
    ands: list[dict[str, Any]] = []

    def add(facet_urn: str, values: list[str]) -> None:
        if values:
            ands.append({"or": {facet_urn: values}})

    add(_LOCATION_FACET, resolved_urns.get("locations", targeting.get("locations", [])))
    add(_TITLE_FACET, resolved_urns.get("job_titles", include.get("job_titles", [])))
    add(_SENIORITY_FACET, include.get("seniorities", []))
    add(_INDUSTRY_FACET, resolved_urns.get("industries", include.get("industries", [])))
    add(_COMPANY_SIZE_FACET, include.get("company_sizes", []))
    add(_EMPLOYER_FACET, resolved_urns.get("companies", include.get("companies", [])))
    add(_SKILL_FACET, resolved_urns.get("skills", include.get("skills", [])))

    criteria: dict[str, Any] = {"include": {"and": ands}}

    exclude = targeting.get("exclude") or {}
    exclude_ors: list[dict[str, Any]] = []
    if exclude.get("companies"):
        exclude_ors.append({_EMPLOYER_FACET: exclude["companies"]})
    if exclude.get("job_titles"):
        exclude_ors.append({_TITLE_FACET: exclude["job_titles"]})
    if exclude_ors:
        criteria["exclude"] = {"or": exclude_ors}

    return criteria


def build_campaign_payload(
    campaign: dict[str, Any],
    group_urn: str,
    config: LinkedInConfig,
    resolved_urns: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    bid = campaign.get("bid") or {}
    schedule = campaign["schedule"]
    payload: dict[str, Any] = {
        "account": config.ad_account_urn,
        "campaignGroup": group_urn,
        "name": campaign["name"],
        "type": campaign.get("format", "SPONSORED_UPDATES"),
        "objectiveType": campaign["objective"],
        "status": campaign.get("status", "DRAFT"),
        "costType": bid.get("cost_type", "CPM"),
        "dailyBudget": _money(
            campaign["daily_budget_usd"],
            campaign.get("currency", config.default_currency),
        ),
        "locale": campaign.get("locale", {"country": "US", "language": "en"}),
        "audienceExpansionEnabled": bool(
            (campaign.get("targeting") or {}).get("audience_expansion", False)
        ),
        "offsiteDeliveryEnabled": bool(
            (campaign.get("targeting") or {}).get("linkedin_audience_network", False)
        ),
        "runSchedule": {"start": _to_millis(schedule["start_date"])},
        "targetingCriteria": build_targeting_criteria(
            campaign.get("targeting") or {}, resolved_urns
        ),
    }
    if schedule.get("end_date"):
        payload["runSchedule"]["end"] = _to_millis(schedule["end_date"])
    if bid.get("unit_cost_usd") is not None:
        payload["unitCost"] = _money(
            bid["unit_cost_usd"], config.default_currency
        )
    return payload


def build_creative_payload(
    creative: dict[str, Any],
    campaign_urn: str,
    image_urn: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaign": campaign_urn,
        "type": _creative_type(creative),
        "status": creative.get("status", "DRAFT"),
        "content": {
            "textAd": {
                "headline": creative.get("headline", ""),
                "description": creative.get("intro_text", ""),
                "destinationUrl": creative.get("destination_url", ""),
            }
        },
    }
    if image_urn:
        payload["content"] = {
            "singleImage": {
                "image": image_urn,
                "headline": creative.get("headline", ""),
                "description": creative.get("intro_text", ""),
                "destinationUrl": creative.get("destination_url", ""),
                "callToActionLabel": creative.get("cta", "LEARN_MORE"),
            }
        }
    return payload


def _creative_type(creative: dict[str, Any]) -> str:
    ctype = creative.get("type", "SINGLE_IMAGE")
    return {
        "SINGLE_IMAGE": "SPONSORED_STATUS_UPDATE",
        "VIDEO": "SPONSORED_VIDEO",
        "CAROUSEL": "CAROUSEL",
        "TEXT": "TEXT_AD",
    }.get(ctype, "SPONSORED_STATUS_UPDATE")


def build_lead_gen_form_payload(
    form: dict[str, Any], config: LinkedInConfig
) -> dict[str, Any]:
    return {
        "account": config.ad_account_urn,
        "name": form["name"],
        "headline": form["headline"],
        "description": form.get("description", ""),
        "privacyPolicyUrl": form["privacy_policy_url"],
        "thankYouMessage": form.get("thank_you_message", ""),
        "questions": [{"type": q} for q in form["questions"]],
    }


def plan_launch(brief: dict[str, Any], config: LinkedInConfig) -> dict[str, Any]:
    """Return the full set of payloads that would be sent, without calling the API."""
    group_payload = build_campaign_group_payload(brief, config)
    plans: list[dict[str, Any]] = []
    for campaign in brief["campaigns"]:
        plan: dict[str, Any] = {
            "campaign_payload": build_campaign_payload(
                campaign, "urn:li:sponsoredCampaignGroup:<new>", config
            ),
            "creatives": [
                {
                    "image_path": c.get("image_path"),
                    "payload": build_creative_payload(
                        c, "urn:li:sponsoredCampaign:<new>", image_urn=None
                    ),
                }
                for c in campaign.get("creatives", [])
            ],
        }
        if campaign.get("lead_gen_form"):
            plan["lead_gen_form_payload"] = build_lead_gen_form_payload(
                campaign["lead_gen_form"], config
            )
        plans.append(plan)
    return {
        "campaign_group_payload": group_payload,
        "campaigns": plans,
        "api_version": config.api_version,
        "ad_account_urn": config.ad_account_urn,
    }


async def launch_from_brief(
    brief: dict[str, Any],
    config: LinkedInConfig,
    client: "LinkedInClient",
    *,
    brief_path: str | Path | None = None,
    activate: bool = False,
) -> dict[str, Any]:
    """Execute the full launch flow. Returns URNs + Campaign Manager links."""
    base_dir = Path(brief_path).parent if brief_path else Path.cwd()
    status_override = "ACTIVE" if activate else brief["campaign_group"].get("status", "DRAFT")

    group_payload = build_campaign_group_payload(brief, config)
    group_payload["status"] = status_override
    group_result = await client.create_campaign_group(group_payload)
    group_urn = group_result["urn"]

    results: list[dict[str, Any]] = []
    for campaign in brief["campaigns"]:
        lgf_urn = None
        if campaign.get("lead_gen_form"):
            lgf_payload = build_lead_gen_form_payload(campaign["lead_gen_form"], config)
            lgf_result = await client.create_lead_gen_form(lgf_payload)
            lgf_urn = lgf_result["urn"]

        campaign_payload = build_campaign_payload(campaign, group_urn, config)
        campaign_payload["status"] = status_override
        if lgf_urn:
            campaign_payload["leadGenForm"] = lgf_urn
        campaign_result = await client.create_campaign(campaign_payload)
        campaign_urn = campaign_result["urn"]

        creative_results: list[dict[str, Any]] = []
        for creative in campaign.get("creatives", []):
            image_urn = None
            if creative.get("image_path"):
                image_path = (base_dir / creative["image_path"]).resolve()
                upload = await client.upload_image(image_path)
                image_urn = upload["urn"]
            creative_payload = build_creative_payload(creative, campaign_urn, image_urn)
            creative_payload["status"] = status_override
            creative_result = await client.create_creative(creative_payload)
            creative_results.append(
                {
                    "urn": creative_result["urn"],
                    "image_urn": image_urn,
                    "headline": creative.get("headline"),
                }
            )

        results.append(
            {
                "campaign_urn": campaign_urn,
                "campaign_id": campaign_result["id"],
                "lead_gen_form_urn": lgf_urn,
                "creatives": creative_results,
                "campaign_manager_url": (
                    f"https://www.linkedin.com/campaignmanager/accounts/"
                    f"{config.ad_account_id}/campaigns/{campaign_result['id']}"
                ),
            }
        )

    return {
        "status": status_override,
        "campaign_group": {
            "urn": group_urn,
            "id": group_result["id"],
            "campaign_manager_url": (
                f"https://www.linkedin.com/campaignmanager/accounts/"
                f"{config.ad_account_id}/campaign-groups/{group_result['id']}"
            ),
        },
        "campaigns": results,
    }

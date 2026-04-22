"""Schema and safety validation for a parsed LinkedIn Launch Config brief.

Validation always runs before any API call. Failures return a structured list
of issues rather than raising, so the MCP server can surface all problems at
once.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

VALID_OBJECTIVES = {
    "LEAD_GENERATION", "WEBSITE_VISITS", "WEBSITE_CONVERSIONS",
    "BRAND_AWARENESS", "ENGAGEMENT", "VIDEO_VIEWS", "JOB_APPLICANTS",
    "TALENT_LEADS",
}
VALID_FORMATS = {
    "SPONSORED_UPDATES", "TEXT_AD", "SPONSORED_INMAILS", "MESSAGE_AD", "DYNAMIC",
}
VALID_BID_STRATEGIES = {"MAX_DELIVERY", "TARGET_COST", "MANUAL"}
VALID_COST_TYPES = {"CPM", "CPC", "CPV"}
VALID_STATUSES = {"DRAFT", "PAUSED", "ACTIVE"}
VALID_SENIORITIES = {
    "UNPAID", "TRAINING", "ENTRY", "SENIOR", "MANAGER", "DIRECTOR",
    "VP", "CXO", "OWNER", "PARTNER",
}
VALID_SIZES = {
    "SIZE_1", "SIZE_2_TO_10", "SIZE_11_TO_50", "SIZE_51_TO_200",
    "SIZE_201_TO_500", "SIZE_501_TO_1000", "SIZE_1001_TO_5000",
    "SIZE_5001_TO_10000", "SIZE_10001_OR_MORE",
}
VALID_CTAS = {
    "LEARN_MORE", "SIGN_UP", "DOWNLOAD", "SUBSCRIBE", "REGISTER", "JOIN",
    "ATTEND", "APPLY_NOW", "REQUEST_DEMO", "GET_QUOTE", "CONTACT_US",
    "VIEW_QUOTE", "VIEW_NOW", "VISIT_WEBSITE",
}
LEAD_CTAS = {"REQUEST_DEMO", "SIGN_UP", "DOWNLOAD", "SUBSCRIBE", "REGISTER", "APPLY_NOW"}


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


def _as_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def validate_brief(
    brief: dict[str, Any],
    *,
    daily_budget_max_usd: float,
    brief_path: str | Path | None = None,
) -> ValidationReport:
    report = ValidationReport()
    today = date.today()

    group = brief.get("campaign_group") or {}
    campaigns = brief.get("campaigns") or []

    if not group.get("name"):
        report.errors.append("campaign_group.name is required")
    total_budget = group.get("total_budget_usd")
    if not isinstance(total_budget, (int, float)) or total_budget <= 0:
        report.errors.append("campaign_group.total_budget_usd must be a positive number")
    group_start = _as_date(group.get("start_date"))
    group_end = _as_date(group.get("end_date"))
    if group.get("start_date") and not group_start:
        report.errors.append("campaign_group.start_date must be YYYY-MM-DD")
    if group.get("end_date") and not group_end:
        report.errors.append("campaign_group.end_date must be YYYY-MM-DD")
    if group_start and group_start < today:
        report.warnings.append(
            f"campaign_group.start_date {group_start} is in the past"
        )
    if group_start and group_end and group_end <= group_start:
        report.errors.append("campaign_group.end_date must be after start_date")
    group_status = group.get("status", "DRAFT")
    if group_status not in VALID_STATUSES:
        report.errors.append(
            f"campaign_group.status must be one of {sorted(VALID_STATUSES)}"
        )

    if not isinstance(campaigns, list) or not campaigns:
        report.errors.append("at least one campaign is required")
        return report

    total_daily_budget = 0.0
    brief_dir = Path(brief_path).parent if brief_path else Path.cwd()

    for idx, campaign in enumerate(campaigns):
        prefix = f"campaigns[{idx}]"
        if not campaign.get("name"):
            report.errors.append(f"{prefix}.name is required")

        objective = campaign.get("objective")
        if objective not in VALID_OBJECTIVES:
            report.errors.append(
                f"{prefix}.objective must be one of {sorted(VALID_OBJECTIVES)}"
            )

        fmt = campaign.get("format", "SPONSORED_UPDATES")
        if fmt not in VALID_FORMATS:
            report.errors.append(f"{prefix}.format invalid: {fmt}")

        daily = campaign.get("daily_budget_usd")
        if not isinstance(daily, (int, float)) or daily <= 0:
            report.errors.append(f"{prefix}.daily_budget_usd must be a positive number")
        else:
            total_daily_budget += daily
            if daily > daily_budget_max_usd:
                report.errors.append(
                    f"{prefix}.daily_budget_usd ${daily} exceeds safety ceiling "
                    f"${daily_budget_max_usd}. Override via LINKEDIN_DAILY_BUDGET_MAX."
                )

        bid = campaign.get("bid") or {}
        strategy = bid.get("strategy")
        if strategy not in VALID_BID_STRATEGIES:
            report.errors.append(
                f"{prefix}.bid.strategy must be one of {sorted(VALID_BID_STRATEGIES)}"
            )
        cost_type = bid.get("cost_type")
        if cost_type not in VALID_COST_TYPES:
            report.errors.append(
                f"{prefix}.bid.cost_type must be one of {sorted(VALID_COST_TYPES)}"
            )
        if strategy in {"TARGET_COST", "MANUAL"} and not bid.get("unit_cost_usd"):
            report.errors.append(
                f"{prefix}.bid.unit_cost_usd is required for {strategy} strategy"
            )

        sched = campaign.get("schedule") or {}
        c_start = _as_date(sched.get("start_date"))
        c_end = _as_date(sched.get("end_date"))
        if not c_start:
            report.errors.append(f"{prefix}.schedule.start_date is required (YYYY-MM-DD)")
        if c_end and c_start and c_end <= c_start:
            report.errors.append(f"{prefix}.schedule.end_date must be after start_date")

        targeting = campaign.get("targeting") or {}
        include = targeting.get("include") or {}
        if not any(include.get(k) for k in (
            "job_titles", "seniorities", "industries", "company_sizes",
            "skills", "companies",
        )):
            report.errors.append(
                f"{prefix}.targeting.include must specify at least one facet"
            )
        for seniority in include.get("seniorities", []) or []:
            if seniority not in VALID_SENIORITIES:
                report.errors.append(
                    f"{prefix}.targeting.include.seniorities: invalid value {seniority}"
                )
        for size in include.get("company_sizes", []) or []:
            if size not in VALID_SIZES:
                report.errors.append(
                    f"{prefix}.targeting.include.company_sizes: invalid value {size}"
                )

        creatives = campaign.get("creatives") or []
        if not creatives:
            report.errors.append(f"{prefix}.creatives must contain at least one creative")
        for cidx, creative in enumerate(creatives):
            cprefix = f"{prefix}.creatives[{cidx}]"
            cta = creative.get("cta")
            if cta not in VALID_CTAS:
                report.errors.append(
                    f"{cprefix}.cta must be one of {sorted(VALID_CTAS)}"
                )
            if objective == "LEAD_GENERATION" and cta not in LEAD_CTAS:
                report.warnings.append(
                    f"{cprefix}.cta={cta} is unusual for LEAD_GENERATION; "
                    f"consider {sorted(LEAD_CTAS)}"
                )
            url = creative.get("destination_url", "")
            if url and "utm_source" not in url.lower():
                report.warnings.append(
                    f"{cprefix}.destination_url is missing utm_source tagging"
                )
            img = creative.get("image_path")
            if img:
                resolved = (brief_dir / img).resolve()
                if not resolved.is_file():
                    report.errors.append(
                        f"{cprefix}.image_path not found: {resolved}"
                    )

        lgf = campaign.get("lead_gen_form")
        if objective == "LEAD_GENERATION" and not lgf:
            report.warnings.append(
                f"{prefix}: LEAD_GENERATION objective without a lead_gen_form block"
            )
        if lgf:
            if not lgf.get("privacy_policy_url"):
                report.errors.append(f"{prefix}.lead_gen_form.privacy_policy_url is required")
            if not lgf.get("questions"):
                report.errors.append(f"{prefix}.lead_gen_form.questions must list at least one field")

    if (
        isinstance(total_budget, (int, float))
        and group_start and group_end
    ):
        days = max(1, (group_end - group_start).days)
        if total_daily_budget * days > total_budget * 1.05:
            report.errors.append(
                f"sum(daily_budget_usd) * days = "
                f"${total_daily_budget * days:,.0f} exceeds "
                f"campaign_group.total_budget_usd ${total_budget:,.0f}"
            )

    return report

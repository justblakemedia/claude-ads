"""Environment-driven configuration and credential loading.

Credentials are loaded from env vars on demand. Access tokens never appear
in logs or tool responses; helper accessors redact them on error.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


@dataclass(frozen=True)
class LinkedInConfig:
    client_id: str
    client_secret: str
    access_token: str
    refresh_token: str | None
    ad_account_id: str
    api_version: str
    daily_budget_max_usd: float
    default_currency: str
    dry_run_default: bool

    @property
    def ad_account_urn(self) -> str:
        return f"urn:li:sponsoredAccount:{self.ad_account_id}"


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(
            f"{name} is not set. See ads/references/linkedin-api.md for setup."
        )
    return value


def load_config() -> LinkedInConfig:
    return LinkedInConfig(
        client_id=_require("LINKEDIN_CLIENT_ID"),
        client_secret=_require("LINKEDIN_CLIENT_SECRET"),
        access_token=_require("LINKEDIN_ACCESS_TOKEN"),
        refresh_token=os.environ.get("LINKEDIN_REFRESH_TOKEN") or None,
        ad_account_id=_require("LINKEDIN_AD_ACCOUNT_ID"),
        api_version=os.environ.get("LINKEDIN_API_VERSION", "202504"),
        daily_budget_max_usd=float(os.environ.get("LINKEDIN_DAILY_BUDGET_MAX", "500")),
        default_currency=os.environ.get("LINKEDIN_DEFAULT_CURRENCY", "USD"),
        dry_run_default=os.environ.get("LINKEDIN_DRY_RUN_DEFAULT", "true").lower() != "false",
    )


def redact(payload: dict) -> dict:
    """Strip anything that looks like a credential before returning to the caller."""
    redacted: dict = {}
    for key, value in payload.items():
        lower = key.lower()
        if any(s in lower for s in ("token", "secret", "authorization", "cookie")):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact(value)
        else:
            redacted[key] = value
    return redacted

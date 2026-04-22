"""Thin HTTP client for the LinkedIn Marketing API.

Wraps authentication headers, version pinning, retry/backoff on 429, and
redaction of credentials from error output. Does NOT implement business
logic — higher-level functions live in `launcher.py`.
"""
from __future__ import annotations

import asyncio
import logging
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from .config import LinkedInConfig

logger = logging.getLogger(__name__)

BASE_URL = "https://api.linkedin.com/rest"
OAUTH_URL = "https://www.linkedin.com/oauth/v2/accessToken"


class LinkedInAPIError(RuntimeError):
    def __init__(self, status: int, body: Any, message: str = ""):
        super().__init__(f"LinkedIn API {status}: {message or body}")
        self.status = status
        self.body = body


class LinkedInClient:
    def __init__(self, config: LinkedInConfig, http: httpx.AsyncClient | None = None):
        self.config = config
        self._http = http or httpx.AsyncClient(timeout=30.0)
        self._owns_http = http is None

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "LinkedIn-Version": self.config.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
        headers: dict | None = None,
        max_retries: int = 4,
    ) -> httpx.Response:
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        backoff = 2.0
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = await self._http.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=self._headers(headers),
                )
                if response.status_code == 429:
                    logger.warning("429 from LinkedIn, sleeping %.0fs", backoff)
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                if 500 <= response.status_code < 600 and attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                return response
            except httpx.TransportError as exc:
                last_exc = exc
                await asyncio.sleep(backoff)
                backoff *= 2
        if last_exc:
            raise last_exc
        raise LinkedInAPIError(429, "rate limited", "exhausted retries")

    async def refresh_access_token(self) -> dict[str, Any]:
        if not self.config.refresh_token:
            raise LinkedInAPIError(0, "", "no refresh token configured")
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.config.refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        response = await self._http.post(OAUTH_URL, data=data)
        if response.status_code != 200:
            raise LinkedInAPIError(response.status_code, response.text, "refresh failed")
        return response.json()

    async def create_campaign_group(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = f"/adAccounts/{self.config.ad_account_id}/adCampaignGroups"
        response = await self._request("POST", path, json=payload)
        if response.status_code not in (200, 201):
            raise LinkedInAPIError(response.status_code, response.text, "create group")
        entity_id = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
        return {
            "id": entity_id,
            "urn": f"urn:li:sponsoredCampaignGroup:{entity_id}" if entity_id else None,
            "status_code": response.status_code,
        }

    async def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = f"/adAccounts/{self.config.ad_account_id}/adCampaigns"
        response = await self._request("POST", path, json=payload)
        if response.status_code not in (200, 201):
            raise LinkedInAPIError(response.status_code, response.text, "create campaign")
        entity_id = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
        return {
            "id": entity_id,
            "urn": f"urn:li:sponsoredCampaign:{entity_id}" if entity_id else None,
            "status_code": response.status_code,
        }

    async def upload_image(self, image_path: str | Path) -> dict[str, Any]:
        init_body = {
            "initializeUploadRequest": {
                "owner": self.config.ad_account_urn,
            }
        }
        init_resp = await self._request(
            "POST", "/images?action=initializeUpload", json=init_body
        )
        if init_resp.status_code not in (200, 201):
            raise LinkedInAPIError(
                init_resp.status_code, init_resp.text, "initializeUpload"
            )
        init_data = init_resp.json().get("value", {})
        upload_url = init_data.get("uploadUrl")
        image_urn = init_data.get("image")
        if not upload_url or not image_urn:
            raise LinkedInAPIError(0, init_data, "init response missing uploadUrl/image")

        path = Path(image_path)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        put_resp = await self._http.put(
            upload_url,
            content=path.read_bytes(),
            headers={"Content-Type": mime},
        )
        if put_resp.status_code not in (200, 201):
            raise LinkedInAPIError(
                put_resp.status_code, put_resp.text, "PUT upload"
            )
        return {"urn": image_urn, "uploaded_bytes": path.stat().st_size}

    async def create_creative(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = f"/adAccounts/{self.config.ad_account_id}/creatives"
        response = await self._request("POST", path, json=payload)
        if response.status_code not in (200, 201):
            raise LinkedInAPIError(response.status_code, response.text, "create creative")
        entity_id = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
        return {
            "id": entity_id,
            "urn": f"urn:li:sponsoredCreative:{entity_id}" if entity_id else None,
            "status_code": response.status_code,
        }

    async def create_lead_gen_form(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", "/leadGenForms", json=payload)
        if response.status_code not in (200, 201):
            raise LinkedInAPIError(
                response.status_code, response.text, "create lead gen form"
            )
        entity_id = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
        return {
            "id": entity_id,
            "urn": f"urn:li:leadGenForm:{entity_id}" if entity_id else None,
            "status_code": response.status_code,
        }

    async def list_campaigns(self, limit: int = 25) -> list[dict[str, Any]]:
        path = f"/adAccounts/{self.config.ad_account_id}/adCampaigns"
        response = await self._request(
            "GET", path, params={"q": "search", "count": str(limit)}
        )
        if response.status_code != 200:
            raise LinkedInAPIError(response.status_code, response.text, "list campaigns")
        body = response.json()
        return body.get("elements", [])

    async def typeahead(self, facet: str, query: str) -> list[dict[str, Any]]:
        response = await self._request(
            "GET",
            "/adTargetingEntities",
            params={"q": "typeahead", "query": query, "facet": facet},
        )
        if response.status_code != 200:
            raise LinkedInAPIError(response.status_code, response.text, f"typeahead {facet}")
        return response.json().get("elements", [])

    async def audience_count(self, targeting_criteria: dict[str, Any]) -> dict[str, Any]:
        response = await self._request(
            "POST",
            f"/adAccounts/{self.config.ad_account_id}/adTargetingFacets?action=audienceCount",
            json={"targetingCriteria": targeting_criteria},
        )
        if response.status_code != 200:
            raise LinkedInAPIError(response.status_code, response.text, "audienceCount")
        return response.json()

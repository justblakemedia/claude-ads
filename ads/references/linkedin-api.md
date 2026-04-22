# LinkedIn Marketing API Reference

<!-- Used by: ads-linkedin-launch skill, mcp/linkedin-ads server -->
<!-- Purpose: endpoints, scopes, and setup for programmatic LinkedIn campaign creation -->

## Overview

This reference documents the LinkedIn Marketing API endpoints needed to create
Campaign Groups, Campaigns, Creatives, and Lead Gen Forms programmatically.

The `mcp/linkedin-ads` MCP server wraps these endpoints so Claude Code can
launch LinkedIn campaigns by reading a `campaign-brief.md` that contains a
`## LinkedIn Launch Config` section.

---

## 1. One-Time Setup (Before First Use)

### Step 1: Create a LinkedIn Developer App

1. Visit <https://www.linkedin.com/developers/apps>
2. Click **Create app**
3. Fill in: app name, associated LinkedIn Company Page, logo
4. Verify the Company Page (an admin of that page must confirm)

### Step 2: Apply for Marketing Developer Platform (MDP) Access

Standard developer apps cannot call the Ads API. You must apply for MDP access:

1. In your app, go to **Products** tab
2. Request **Marketing Developer Platform**
3. Fill out the access request form explaining your use case
4. Approval typically takes **5-15 business days**

**What LinkedIn looks for in your application:**
- Clear description of how the integration serves advertisers
- Not a mass-market tool; concrete use case
- Compliance with LinkedIn API Terms of Use

### Step 3: Configure OAuth Scopes

Once MDP is approved, request these scopes in your app's **Auth** tab:

| Scope | Purpose |
|-------|---------|
| `r_ads` | Read ad accounts, campaigns, creatives |
| `rw_ads` | Create/update campaigns and creatives |
| `r_ads_reporting` | Pull performance metrics |
| `r_organization_social` | Read Company Page posts (required for Sponsored Content) |
| `w_member_social` | Post on behalf of authenticated member (Thought Leader Ads) |
| `r_basicprofile` | Read basic member profile (needed for OAuth identity) |

### Step 4: Get Your Ad Account URN

Your numeric ad account ID is visible in Campaign Manager URLs:
```
https://www.linkedin.com/campaignmanager/accounts/123456789/...
                                                  ^^^^^^^^^^
                                                  ad account ID
```

The fully qualified URN used in API calls: `urn:li:sponsoredAccount:123456789`

---

## 2. Authentication

### OAuth 2.0 Three-Legged Flow

Required for any API call that creates or modifies ads.

**Authorization URL:**
```
https://www.linkedin.com/oauth/v2/authorization
  ?response_type=code
  &client_id={CLIENT_ID}
  &redirect_uri={REDIRECT_URI}
  &scope=r_ads%20rw_ads%20r_ads_reporting%20r_organization_social
  &state={RANDOM_STATE}
```

**Token Exchange (POST):**
```
https://www.linkedin.com/oauth/v2/accessToken
  grant_type=authorization_code
  code={CODE_FROM_CALLBACK}
  redirect_uri={REDIRECT_URI}
  client_id={CLIENT_ID}
  client_secret={CLIENT_SECRET}
```

**Response:**
```json
{
  "access_token": "AQV...",
  "expires_in": 5183999,
  "refresh_token": "AQW...",
  "refresh_token_expires_in": 31536000,
  "scope": "r_ads,rw_ads,..."
}
```

Access tokens expire in ~60 days. Refresh tokens last ~365 days.

### Required Headers on Every API Call

```
Authorization: Bearer {ACCESS_TOKEN}
LinkedIn-Version: 202504
X-Restli-Protocol-Version: 2.0.0
Content-Type: application/json
```

`LinkedIn-Version` must be a valid monthly version (use the current or most
recent stable version). The server pins a default and lets callers override.

---

## 3. Campaign Creation Flow

The create flow requires four sequential calls:

```
1. Create Campaign Group    (budget envelope; parent container)
         |
2. Create Campaign          (targeting + bidding; child of group)
         |
3. Upload Creative Asset    (image/video via Assets API)
         |
4. Create Creative          (ad unit; binds asset to campaign)
```

### 3.1 Create Campaign Group

`POST https://api.linkedin.com/rest/adAccounts/{accountId}/adCampaignGroups`

```json
{
  "account": "urn:li:sponsoredAccount:123456789",
  "name": "Q2 2026 - Enterprise Demand Gen",
  "status": "DRAFT",
  "totalBudget": {
    "currencyCode": "USD",
    "amount": "10000"
  },
  "runSchedule": {
    "start": 1714521600000,
    "end": 1717113600000
  }
}
```

Returns `X-RestLi-Id` header with the new campaign group ID (numeric).

### 3.2 Create Campaign

`POST https://api.linkedin.com/rest/adAccounts/{accountId}/adCampaigns`

```json
{
  "account": "urn:li:sponsoredAccount:123456789",
  "campaignGroup": "urn:li:sponsoredCampaignGroup:456",
  "name": "Q2 - Sr Marketing - Lead Gen",
  "type": "SPONSORED_UPDATES",
  "objectiveType": "LEAD_GENERATION",
  "status": "DRAFT",
  "costType": "CPM",
  "dailyBudget": {
    "currencyCode": "USD",
    "amount": "250"
  },
  "unitCost": {
    "currencyCode": "USD",
    "amount": "55"
  },
  "locale": { "country": "US", "language": "en" },
  "targetingCriteria": {
    "include": {
      "and": [
        { "or": { "urn:li:adTargetingFacet:locations": ["urn:li:geo:103644278"] } },
        { "or": { "urn:li:adTargetingFacet:titles": ["urn:li:title:100", "urn:li:title:1001"] } },
        { "or": { "urn:li:adTargetingFacet:staffCountRanges": ["SIZE_1001_TO_5000", "SIZE_5001_TO_10000"] } }
      ]
    }
  },
  "runSchedule": { "start": 1714521600000 }
}
```

**Common `type` values:** `SPONSORED_UPDATES`, `TEXT_AD`, `SPONSORED_INMAILS`, `DYNAMIC`.

**Common `objectiveType` values:** `LEAD_GENERATION`, `WEBSITE_VISITS`,
`WEBSITE_CONVERSIONS`, `BRAND_AWARENESS`, `ENGAGEMENT`, `VIDEO_VIEWS`, `JOB_APPLICANTS`.

### 3.3 Upload Image Asset

Two-step: (a) register upload, (b) PUT the bytes.

**Step 3.3a — Register upload:**
`POST https://api.linkedin.com/rest/images?action=initializeUpload`

```json
{
  "initializeUploadRequest": {
    "owner": "urn:li:sponsoredAccount:123456789"
  }
}
```

Response contains `value.uploadUrl` and `value.image` (the asset URN).

**Step 3.3b — PUT the bytes:**
```
PUT {uploadUrl}
Content-Type: {image_mime}
<binary body>
```

Video uploads follow a similar pattern at `/rest/videos?action=initializeUpload`
with multi-part upload instructions in the response.

### 3.4 Create Creative

`POST https://api.linkedin.com/rest/adAccounts/{accountId}/creatives`

```json
{
  "campaign": "urn:li:sponsoredCampaign:789",
  "type": "SPONSORED_STATUS_UPDATE",
  "status": "DRAFT",
  "content": {
    "reference": "urn:li:share:7123456789"
  }
}
```

For single-image ads, first create a Share (organic post) on the Company Page
or a "dark post" via `/rest/posts`, then reference its URN in the creative.

### 3.5 Lead Gen Form (Optional)

`POST https://api.linkedin.com/rest/leadGenForms`

```json
{
  "account": "urn:li:sponsoredAccount:123456789",
  "name": "Demo Request Q2",
  "headline": "See it in action",
  "description": "15-minute personalized demo.",
  "privacyPolicyUrl": "https://example.com/privacy",
  "questions": [
    { "type": "FIRST_NAME" },
    { "type": "LAST_NAME" },
    { "type": "EMAIL" },
    { "type": "COMPANY_NAME" },
    { "type": "JOB_TITLE" }
  ],
  "thankYouMessage": "Thanks! We'll reach out within one business day."
}
```

Reference the returned URN in the campaign's `creativeCallToAction` or in the
creative's content block for Lead Gen objective campaigns.

---

## 4. Targeting Facet Lookup Endpoints

Targeting criteria use URNs. Look up values via these endpoints:

| Facet | Lookup Endpoint |
|-------|----------------|
| Job titles | `GET /rest/adTargetingEntities?q=typeahead&query={text}&facet=TITLE` |
| Skills | `GET /rest/adTargetingEntities?q=typeahead&query={text}&facet=SKILL` |
| Companies | `GET /rest/adTargetingEntities?q=typeahead&query={text}&facet=EMPLOYER` |
| Industries | `GET /rest/adTargetingEntities?q=typeahead&query={text}&facet=INDUSTRY` |
| Geographies | `GET /rest/adTargetingEntities?q=typeahead&query={text}&facet=LOCATION` |
| Seniorities | Fixed list (see below) |
| Staff count | Fixed enum (see below) |

**Seniority enum:**
`UNPAID`, `TRAINING`, `ENTRY`, `SENIOR`, `MANAGER`, `DIRECTOR`, `VP`, `CXO`,
`OWNER`, `PARTNER`.

**Staff count range enum:**
`SIZE_1`, `SIZE_2_TO_10`, `SIZE_11_TO_50`, `SIZE_51_TO_200`, `SIZE_201_TO_500`,
`SIZE_501_TO_1000`, `SIZE_1001_TO_5000`, `SIZE_5001_TO_10000`, `SIZE_10001_OR_MORE`.

---

## 5. Safety Rules Enforced by the MCP Server

The `mcp/linkedin-ads` server enforces these rules by default:

1. **All creates start in `DRAFT` or `PAUSED`** — never `ACTIVE` unless the
   `activate=true` flag is explicitly passed.
2. **Budget ceiling** — the server refuses daily budgets above
   `LINKEDIN_DAILY_BUDGET_MAX` env var (default: $500). Override per-call.
3. **Audience minimum** — targeting criteria estimated to yield <500 members
   are rejected (LinkedIn minimum).
4. **Dry-run is the default** — all mutating tools require `confirm=true`.
   Without it, the tool returns the exact payload that would be sent.
5. **Token redaction** — access tokens are never logged; payloads in error
   responses are redacted before returning to the caller.

---

## 6. Rate Limits

| Scope | Application Limit | Member Limit |
|-------|------------------|--------------|
| Daily app-wide | 500,000 calls | — |
| Per-member daily | — | 100,000 calls |
| Bursts | ~100 req/sec | ~100 req/sec |

The MCP server implements exponential backoff on 429 responses
(2s, 4s, 8s, 16s, then fail).

---

## 7. Environment Variables

The MCP server reads these from env:

| Variable | Required | Purpose |
|----------|----------|---------|
| `LINKEDIN_CLIENT_ID` | Yes | OAuth app client ID |
| `LINKEDIN_CLIENT_SECRET` | Yes | OAuth app client secret |
| `LINKEDIN_ACCESS_TOKEN` | Yes | Current access token |
| `LINKEDIN_REFRESH_TOKEN` | No | Used for auto-refresh |
| `LINKEDIN_AD_ACCOUNT_ID` | Yes | Numeric ad account ID |
| `LINKEDIN_API_VERSION` | No | Defaults to `202504` |
| `LINKEDIN_DAILY_BUDGET_MAX` | No | Safety ceiling, default `500` |
| `LINKEDIN_DEFAULT_CURRENCY` | No | Default `USD` |

---

## 8. Links

- Marketing API docs: <https://learn.microsoft.com/en-us/linkedin/marketing/>
- Developer portal: <https://www.linkedin.com/developers/apps>
- MDP application: <https://learn.microsoft.com/en-us/linkedin/marketing/getting-access>
- Rate limits: <https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits>

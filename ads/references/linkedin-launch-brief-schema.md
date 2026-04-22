# LinkedIn Launch Config: Brief Schema

<!-- Used by: ads-linkedin-launch skill, mcp/linkedin-ads brief_parser -->
<!-- Extends: campaign-brief.md produced by /ads create -->

## Purpose

Defines the `## LinkedIn Launch Config` YAML section appended to `campaign-brief.md`.
This section contains everything the LinkedIn API needs to create the campaign that
the rest of the brief describes in natural language.

When a client hands you a doc with campaign requirements, you (or `/ads create`)
translate those requirements into this schema. `/ads linkedin-launch` then parses
it and issues the API calls.

---

## Placement in campaign-brief.md

Append after `## Copy Deck` and before `## Next Steps`:

```markdown
## LinkedIn Launch Config

```yaml
# (schema below)
```
```

---

## Full Schema

```yaml
version: 1

campaign_group:
  name: "Q2 2026 - Enterprise Demand Gen"
  total_budget_usd: 10000
  start_date: "2026-05-01"
  end_date: "2026-05-31"
  status: DRAFT                    # DRAFT | PAUSED | ACTIVE (default: DRAFT)

campaigns:
  - name: "Q2 - Sr Marketing - Lead Gen"
    objective: LEAD_GENERATION     # see list below
    format: SPONSORED_UPDATES      # see list below
    daily_budget_usd: 250
    bid:
      strategy: MAX_DELIVERY       # MAX_DELIVERY | TARGET_COST | MANUAL
      cost_type: CPM               # CPM | CPC | CPV
      unit_cost_usd: 55            # only required if strategy = MANUAL or TARGET_COST
    schedule:
      start_date: "2026-05-01"
      end_date: "2026-05-31"
    locale: { country: US, language: en }

    targeting:
      locations: ["United States"] # resolved to geo URNs at launch
      include:
        job_titles:
          - "Marketing Manager"
          - "Director of Marketing"
          - "VP of Marketing"
        seniorities: [MANAGER, DIRECTOR, VP]
        industries:
          - "Software Development"
          - "Financial Services"
        company_sizes: [SIZE_1001_TO_5000, SIZE_5001_TO_10000, SIZE_10001_OR_MORE]
        skills: []
        companies: []              # for ABM; up to 300,000
      exclude:
        companies: ["Acme Corp"]
        job_titles: []
      audience_expansion: false
      linkedin_audience_network: true

    creatives:
      - type: SINGLE_IMAGE
        headline: "Turn pipeline into revenue"
        intro_text: "See how 500+ B2B teams cut sales cycle by 30%."
        cta: LEARN_MORE            # see LinkedIn CTA enum
        destination_url: "https://example.com/demo?utm_source=linkedin"
        image_path: "./ad-assets/linkedin/concept-1/feed-1080x1080.png"
      - type: SINGLE_IMAGE
        headline: "Your sales team, 2x as efficient"
        intro_text: "Book a 15-minute demo this week."
        cta: REQUEST_DEMO
        destination_url: "https://example.com/demo?utm_source=linkedin&v=2"
        image_path: "./ad-assets/linkedin/concept-1/feed-alt-1080x1080.png"

    lead_gen_form:                 # optional; only for LEAD_GENERATION objective
      name: "Demo Request Q2"
      headline: "See it in action"
      description: "15-minute personalized demo."
      privacy_policy_url: "https://example.com/privacy"
      thank_you_message: "Thanks! We'll reach out within one business day."
      questions:
        - FIRST_NAME
        - LAST_NAME
        - EMAIL
        - COMPANY_NAME
        - JOB_TITLE
      custom_questions: []
```

---

## Field Reference

### `campaign_group.status`
- `DRAFT` (default, safest) — created but won't spend
- `PAUSED` — fully configured, one click to activate
- `ACTIVE` — **requires `--activate` flag on /ads linkedin-launch**

### `campaigns[].objective`
Valid: `LEAD_GENERATION`, `WEBSITE_VISITS`, `WEBSITE_CONVERSIONS`,
`BRAND_AWARENESS`, `ENGAGEMENT`, `VIDEO_VIEWS`, `JOB_APPLICANTS`, `TALENT_LEADS`.

### `campaigns[].format`
- `SPONSORED_UPDATES` — feed ads (most common)
- `TEXT_AD` — right rail, desktop only
- `SPONSORED_INMAILS` / `MESSAGE_AD` — inbox delivery
- `DYNAMIC` — personalized (follower, spotlight)

### `campaigns[].bid.strategy`
- `MAX_DELIVERY` — LinkedIn optimizes for most results (no unit cost needed)
- `TARGET_COST` — LinkedIn targets a specific CPX (unit_cost_usd required)
- `MANUAL` — caller sets the exact bid (unit_cost_usd required)

### `campaigns[].creatives[].cta`
Valid values: `LEARN_MORE`, `SIGN_UP`, `DOWNLOAD`, `SUBSCRIBE`, `REGISTER`,
`JOIN`, `ATTEND`, `APPLY_NOW`, `REQUEST_DEMO`, `GET_QUOTE`, `CONTACT_US`,
`VIEW_QUOTE`, `VIEW_NOW`, `VISIT_WEBSITE`.

### `targeting.seniorities`
Enum: `UNPAID`, `TRAINING`, `ENTRY`, `SENIOR`, `MANAGER`, `DIRECTOR`, `VP`, `CXO`,
`OWNER`, `PARTNER`.

### `targeting.company_sizes`
Enum: `SIZE_1`, `SIZE_2_TO_10`, `SIZE_11_TO_50`, `SIZE_51_TO_200`,
`SIZE_201_TO_500`, `SIZE_501_TO_1000`, `SIZE_1001_TO_5000`,
`SIZE_5001_TO_10000`, `SIZE_10001_OR_MORE`.

---

## Validation Rules (enforced before any API call)

1. **Budget sanity**: `daily_budget_usd * days_in_schedule <= campaign_group.total_budget_usd`
2. **Audience minimum**: estimated size ≥500 (LinkedIn enforces this)
3. **Creative count**: at least 1 creative per campaign
4. **Asset existence**: every `image_path` must resolve to a readable file
5. **CTA match**: lead gen campaigns require a CTA from the "lead" family
   (`REQUEST_DEMO`, `SIGN_UP`, `DOWNLOAD`, `SUBSCRIBE`, `REGISTER`)
6. **URL utm tagging**: warn if destination URLs lack `utm_source=linkedin`
7. **Schedule sanity**: `start_date < end_date`, `start_date >= today`

Validation failures produce a report before any API call fires.

---

## Minimal Example (what a client doc typically maps to)

For a client brief that says:
> "$5k test, targeting senior marketers at mid-market SaaS in US, want demo
> bookings, one ad with our Q2 whitepaper as the offer."

The minimum YAML:

```yaml
version: 1
campaign_group:
  name: "Q2 Whitepaper Test"
  total_budget_usd: 5000
  start_date: "2026-05-01"
  end_date: "2026-05-31"
campaigns:
  - name: "Senior Marketers - Mid-Market SaaS"
    objective: LEAD_GENERATION
    format: SPONSORED_UPDATES
    daily_budget_usd: 166
    bid:
      strategy: MAX_DELIVERY
      cost_type: CPM
    schedule: { start_date: "2026-05-01", end_date: "2026-05-31" }
    locale: { country: US, language: en }
    targeting:
      locations: ["United States"]
      include:
        seniorities: [SENIOR, MANAGER, DIRECTOR, VP]
        industries: ["Software Development"]
        company_sizes: [SIZE_201_TO_500, SIZE_501_TO_1000]
    creatives:
      - type: SINGLE_IMAGE
        headline: "Download the Q2 B2B Marketing Report"
        intro_text: "What 500+ marketing leaders are prioritizing this quarter."
        cta: DOWNLOAD
        destination_url: "https://example.com/q2-report?utm_source=linkedin"
        image_path: "./ad-assets/linkedin/concept-1/feed-1080x1080.png"
    lead_gen_form:
      name: "Q2 Report Download"
      headline: "Get the full report"
      description: "44 pages of benchmark data."
      privacy_policy_url: "https://example.com/privacy"
      questions: [FIRST_NAME, LAST_NAME, EMAIL, COMPANY_NAME, JOB_TITLE]
      thank_you_message: "Thanks! Check your inbox."
```

---

## How /ads create populates this section

When `/ads create --platforms linkedin` runs, the `copy-writer` agent
appends a draft `## LinkedIn Launch Config` section filled with placeholders
(budget, targeting, schedule) for the user to confirm or override before
`/ads linkedin-launch` runs.

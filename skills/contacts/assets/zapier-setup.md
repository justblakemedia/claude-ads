# Blinq → Zapier → OneDrive → Obsidian Setup

One-time setup to auto-sync Blinq business card scans into an Obsidian vault as markdown files with YAML frontmatter.

## Prerequisites

- Blinq account (Free tier is fine)
- Zapier account (Free tier: 100 tasks/month, 15-min polling — sufficient for business cards)
- OneDrive with an Obsidian vault synced to it
- Gmail (or any IMAP inbox) receiving Blinq's `notifications@blinq.me` emails

## Step 1: Create the landing folder

In your Obsidian vault, create a `People/` subfolder. Zapier will drop one `.md` file per new contact here.

## Step 2: Zapier trigger — Blinq or Email Parser fallback

**Try first:** In Zapier, search "Blinq" → create a Zap with trigger **"New Contact"**. Connect your Blinq account.

**If Blinq's Zapier app is paywalled on Free tier**, use the email-parser fallback:

1. Go to `parser.zapier.com`, create a mailbox. Copy the `xxxxxx@robot.zapier.com` address.
2. In Gmail, create a filter: `from:(*@blinq.me)` → **Forward to** the parser address (you'll need to add and verify it as a forwarding address first).
3. Trigger one real Blinq card exchange so a notification email hits the parser.
4. In the parser, open the received email and highlight the fields to extract: **name**, **email**, **phone**, **company**, **title**. Save the template.
5. In your Zap, set the trigger to **Email Parser by Zapier → New Email**, pick your mailbox.

## Step 3: Formatter step (for a clean date)

Add a **Formatter by Zapier** step before the OneDrive action:

- Action: **Date / Time → Format**
- Input: `{{zap_meta_human_now}}`
- To Format: `YYYY-MM-DD`

This gives you a Dataview-queryable `met:` date instead of a verbose timestamp.

## Step 4: OneDrive action — Create New Text File

- App: **OneDrive**
- Action: **Create New Text File**
- Folder: `/JB vault/People/` (adjust if your vault is named differently or nested)
- File Name: `{{name}} — {{company}}.md`
  *The em dash (`—`, not a hyphen) is the intended separator. Prevents collisions when two people share a name.*
- File Content:

  ```markdown
  ---
  name: {{name}}
  email: {{email}}
  phone: "{{phone}}"
  company: {{company}}
  title: {{title}}
  met: {{formatter_output}}
  source: blinq
  tags: [contact, blinq]
  ---

  ## Notes

  ```

- Overwrite: **No** (so manually edited notes survive if Zapier re-fires).

## Step 5: Turn the Zap on

Send yourself one test card. Within 15 minutes:

1. Zapier shows the task ran green.
2. A `.md` file appears in `OneDrive/JB vault/People/`.
3. After OneDrive sync (30–60 sec), the file is visible in Obsidian and on disk locally.

## Gotchas

- **YAML phone quoting** — always wrap `{{phone}}` in double quotes. Numbers with leading `+` break YAML otherwise.
- **OneDrive sync delay** — new contacts take 30–60 seconds to appear locally. Not instant.
- **Zapier Free task limits** — 100/month is plenty for cards, but if you also use Zapier for other flows, watch the usage meter.
- **Parser breaks if Blinq redesigns their email** — keep a screenshot of the trained template; re-training takes 2 minutes.
- **Duplicate contacts** — if someone re-shares their card, Zapier will create a second file (same name, same company, different timestamp in filename if you add one). Either accept dupes or add a "Find File" step before Create to skip existing.
- **Filename special characters** — Zapier doesn't sanitize `name` / `company` from Blinq. If a contact's company is "Foo/Bar" or contains `:`, OneDrive will reject the filename. Add a **Formatter → Text → Replace** step to strip `/\:*?"<>|` from both fields before the OneDrive action.

## Claude side — nothing to configure

The `contacts` skill reads the vault directly. Set `OBSIDIAN_VAULT_PATH` in your shell once (example for WSL):

```bash
echo 'export OBSIDIAN_VAULT_PATH="/mnt/c/Users/YOU/OneDrive/JB vault"' >> ~/.bashrc
source ~/.bashrc
```

Then ask Claude things like "what's Jane Doe's email?" or "who did I meet at SaaStr?" — it'll grep the `People/` folder on demand.

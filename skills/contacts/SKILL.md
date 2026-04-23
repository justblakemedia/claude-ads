---
name: contacts
description: "Look up people in the user's Obsidian vault (JB vault). Contacts auto-sync from Blinq business card scans via Zapier and OneDrive. Use when user asks about a person by name, company, email, or when they met someone, or wants to pull contact info."
user-invokable: true
---

# Contacts (Blinq to Obsidian)

## Source of truth

Contacts live in the user's Obsidian vault, one markdown file per person, in the `People/` subfolder. Files are written automatically by a Zapier automation: Blinq business card scan to Zapier to OneDrive to Obsidian vault.

## Vault path resolution

Resolve the vault path in this order:

1. `OBSIDIAN_VAULT_PATH` environment variable (preferred).
2. Common defaults to try if env var is unset:
   - WSL: `/mnt/c/Users/*/OneDrive*/JB vault`
   - macOS: `~/Library/CloudStorage/OneDrive-*/JB vault`
   - Native Windows: `C:\Users\<user>\OneDrive\JB vault`
3. If none exist, ask the user for the full path and suggest they set `OBSIDIAN_VAULT_PATH` in their shell rc.

Contact files are at `${VAULT}/People/*.md`.

## File schema

Each person file has YAML frontmatter followed by free-text notes:

```markdown
---
name: Jane Doe
email: jane@acme.com
phone: "+1-555-0100"
company: Acme
title: VP Marketing
met: 2026-04-23
source: blinq
tags: [contact, blinq]
---

## Notes

(free-form notes added later by the user)
```

Filename format: `{name} ({company}).md`. Parens prevent collisions when two people share a name and avoid filename-unsafe characters.

## Lookup process

When the user asks about a person:

1. Run `ls "${VAULT}/People/"` or `grep -l -r -i "<query>" "${VAULT}/People/"` to find matches.
2. Read matching files with `Read`.
3. Answer from the frontmatter + notes body.
4. If multiple matches, list them with company + met-date so the user can disambiguate.

Do NOT auto-load all contacts at session start. Read on demand only. The folder can grow large.

## Common queries

- "Who did I meet at X event?" -> grep notes body for event name, filter by `met:` date.
- "What's Jane's email?" -> find `name:` match, return `email:`.
- "Pull everyone from Acme" -> grep `company: Acme`.
- "Who did I meet last week?" -> filter by `met:` within the last 7 days.

## Adding notes after a meeting

When the user shares follow-up context (e.g., "Met Jane at SaaStr, she's looking for an ads audit"), append to the `## Notes` section of her file. Never overwrite frontmatter. Zapier owns it.

## Slash command

`/contact <query>` runs the lookup process above and displays matches.

## Setup

The Zapier pipeline must be configured once before anything lands in the vault. See `assets/zapier-setup.md` for the full Blinq to Zapier to OneDrive to Obsidian walkthrough.

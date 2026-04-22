"""Parse `## LinkedIn Launch Config` from campaign-brief.md.

The section is a fenced YAML block under a level-2 heading. This parser is
permissive about surrounding markdown (it locates the section and yaml block
using simple markers rather than a full markdown parser).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_SECTION_RE = re.compile(
    r"^##\s+LinkedIn\s+Launch\s+Config\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_FENCE_START_RE = re.compile(r"^```(?:yaml|yml)?\s*$", re.MULTILINE)
_FENCE_END_RE = re.compile(r"^```\s*$", re.MULTILINE)


class BriefParseError(ValueError):
    """Raised when the brief is missing the LinkedIn Launch Config section."""


def extract_yaml_block(markdown_text: str) -> str:
    """Return the first fenced YAML block under `## LinkedIn Launch Config`."""
    section_match = _SECTION_RE.search(markdown_text)
    if not section_match:
        raise BriefParseError(
            "No `## LinkedIn Launch Config` section found. "
            "See ads/references/linkedin-launch-brief-schema.md."
        )
    after = markdown_text[section_match.end():]

    fence_start = _FENCE_START_RE.search(after)
    if not fence_start:
        raise BriefParseError(
            "Found `## LinkedIn Launch Config` but no fenced YAML block beneath it."
        )
    body_start = fence_start.end()
    fence_end = _FENCE_END_RE.search(after, pos=body_start)
    if not fence_end:
        raise BriefParseError("YAML block is missing a closing fence.")
    return after[body_start:fence_end.start()]


def parse_brief_file(path: str | Path) -> dict[str, Any]:
    """Load a markdown file and return the parsed LinkedIn Launch Config dict."""
    text = Path(path).read_text(encoding="utf-8")
    yaml_text = extract_yaml_block(text)
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise BriefParseError(f"YAML parse error: {exc}") from exc
    if not isinstance(data, dict):
        raise BriefParseError("LinkedIn Launch Config must be a YAML mapping.")
    return data

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


HEADING_PATTERN = re.compile(r"^## ([^\n]+)\n", re.MULTILINE)


@dataclass
class MarkdownSections:
    preamble: str
    order: List[str]
    sections: Dict[str, str]


def parse_sections(markdown: str) -> MarkdownSections:
    matches = list(HEADING_PATTERN.finditer(markdown))
    if not matches:
        return MarkdownSections(markdown, [], {})
    preamble = markdown[: matches[0].start()]
    order: List[str] = []
    sections: Dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        order.append(heading)
        sections[heading] = markdown[match.start() : end]
    return MarkdownSections(preamble, order, sections)


def changed_sections(
    baseline: str, refined: str, allowed: Optional[Iterable[str]] = None
) -> List[str]:
    before = parse_sections(baseline)
    after = parse_sections(refined)
    allowed_set = set(allowed) if allowed is not None else None
    order = before.order + [name for name in after.order if name not in before.sections]
    return [
        name
        for name in order
        if (allowed_set is None or name in allowed_set)
        and name in after.sections
        and before.sections.get(name, "") != after.sections.get(name, "")
    ]


def merge_sections(baseline: str, refined: str, accepted: Iterable[str]) -> str:
    before = parse_sections(baseline)
    after = parse_sections(refined)
    accepted_set = set(accepted)
    result = before.preamble
    for heading in before.order:
        if heading in accepted_set and heading in after.sections:
            result += after.sections[heading]
        else:
            result += before.sections[heading]
    for heading in after.order:
        if heading not in before.sections and heading in accepted_set:
            result += after.sections[heading]
    return result.rstrip() + "\n"

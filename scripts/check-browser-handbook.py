#!/usr/bin/env python3
"""structural checks for the English browser handbook and example recipe."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

guides = [ROOT / 'handbook/docs/en/guide/browser.md', ROOT / 'handbook/docs/vi/guide/browser.md']
guide = guides[0]
for g in guides:
    if not g.is_file():
        errors.append(f'missing {g.relative_to(ROOT)}')
if guide.is_file():
    text = guide.read_text(encoding='utf-8')
    for needle in ('STUDIO_ENABLE_BROWSER', 'Allowed origins', 'Browserless', 'URL source', 'chat turn'):
        if needle not in text:
            errors.append(f'guide missing section text: {needle}')
    for image in ('browser-connection-settings.png', 'browser-agent-url-binding.png'):
        path = ROOT / 'handbook/docs/en/images' / image
        if not path.is_file() or path.stat().st_size < 100:
            errors.append(f'missing/empty screenshot {image}')

nav = (ROOT / 'handbook/mkdocs.yml').read_text(encoding='utf-8')
if 'guide/browser.md' not in nav:
    errors.append('handbook/mkdocs.yml missing Browser tools nav entry')
vi_nav = (ROOT / 'handbook/mkdocs.vi.yml').read_text(encoding='utf-8')
if 'guide/browser.md' not in vi_nav:
    errors.append('handbook/mkdocs.vi.yml missing Browser tools nav entry')

example = ROOT / 'examples/browser/lookup_shipment.json'
try:
    data = json.loads(example.read_text(encoding='utf-8'))
except Exception as exc:  # noqa: BLE001
    errors.append(f'example JSON: {exc}')
else:
    recipe = data.get('browser_recipe') or {}
    if recipe.get('version') != 1:
        errors.append('example browser_recipe.version must be 1')
    if not recipe.get('inputs') or not recipe.get('outputs'):
        errors.append('example recipe must declare inputs and outputs')
    if not any(n.get('type') == 'mcp' for n in data.get('nodes') or []):
        errors.append('example must include MCP browser actions')

settings = (ROOT / 'docs/browser-settings.md').read_text(encoding='utf-8')
if 'non-empty whitelist' not in settings and 'require a non-empty' not in settings:
    errors.append('docs/browser-settings.md must state required whitelist')

if errors:
    print('browser handbook checks failed:')
    for item in errors:
        print(' -', item)
    sys.exit(1)
print('browser handbook checks passed')

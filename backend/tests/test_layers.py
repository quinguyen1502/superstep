"""Layering rules (see DEC-0009): lower layers must not import upper ones."""
import pathlib, re
APP = pathlib.Path(__file__).resolve().parents[1] / "app"
FORBIDDEN = {
    "core": ["models", "repositories", "services", "api", "engine", "fastapi"],
    "engine": ["models", "repositories", "services", "api", "fastapi"],
    "models": ["repositories", "services", "api", "engine"],
    "schemas": ["models", "repositories", "services", "api"],
    "repositories": ["services", "api", "fastapi"],
    "services": ["api", "fastapi"],
    "storage": ["models", "repositories", "services", "api", "engine", "fastapi"],  # adapters for attachment bytes (TASK-0191)
}

def test_import_directions():
    bad = []
    for layer, banned in FORBIDDEN.items():
        for f in (APP / layer).rglob("*.py"):
            for line in f.read_text().splitlines():
                m = re.match(r"\s*(?:from|import)\s+([\w.]+)", line)
                if not m: continue
                mod = m.group(1)
                for b in banned:
                    if mod == b or mod.startswith(b + ".") or re.match(rf"^\.+{b}\b", mod) or mod.startswith(f"app.{b}"):
                        bad.append(f"{f.relative_to(APP)}: {line.strip()}")
    assert not bad, "\n".join(bad)

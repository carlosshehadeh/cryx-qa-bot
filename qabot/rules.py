"""Marketplace rules: one JSON file per marketplace and genre in rules/.

Every number a check uses comes from here, never from the check itself. A
rules file Carlos edited is merged over the bundled one, so a newer app
version can add fields without losing his changes.
"""

import json
from pathlib import Path

from qabot.config import bundle_dir


def _merge(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def profiles(rules_dir):
    """{profile id: display name}, sorted by name."""
    found = {}
    for d in (bundle_dir() / "rules", Path(rules_dir)):
        for f in sorted(Path(d).glob("*.json")):
            try:
                found[f.stem] = _read(f).get("name", f.stem)
            except ValueError:
                continue
    return dict(sorted(found.items(), key=lambda kv: kv[1].lower()))


def load(profile, rules_dir=None):
    bundled = bundle_dir() / "rules" / f"{profile}.json"
    user = Path(rules_dir) / f"{profile}.json" if rules_dir else None
    rules = _read(bundled) if bundled.exists() else {}
    if user and user.exists():
        rules = _merge(rules, _read(user))
    if not rules:
        raise FileNotFoundError(f"No rules file called '{profile}.json'")
    rules.setdefault("id", profile)
    return rules

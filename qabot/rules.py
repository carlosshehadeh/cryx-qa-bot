"""Marketplace rules. A profile is one website plus one genre, e.g.
"edmgp-tech-house" = rules/sites/edmgp.json + rules/genres/tech-house.json.

Every number a check uses comes from these files, never from the check. A
site file can hold per-genre changes under "genres". Files Carlos edited
(in the data folder's rules\\) are merged over the bundled ones, so a newer
app version can add fields without losing his changes.
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


def _layer(kind, name, rules_dir):
    """Bundled file with the user's copy merged over it."""
    data = {}
    for d in (bundle_dir() / "rules", Path(rules_dir) if rules_dir else None):
        if d is None:
            continue
        f = d / kind / f"{name}.json"
        if f.exists():
            data = _merge(data, _read(f))
    return data


def _names(kind, rules_dir):
    found = set()
    for d in (bundle_dir() / "rules", Path(rules_dir) if rules_dir else None):
        if d is not None and (d / kind).is_dir():
            found |= {f.stem for f in (d / kind).glob("*.json")}
    return sorted(found)


def profiles(rules_dir=None):
    """{profile id: display name}, e.g. {"edmgp-tech-house": "EDM GP: Tech House"}."""
    out = {}
    for site in _names("sites", rules_dir):
        s = _layer("sites", site, rules_dir)
        for genre in _names("genres", rules_dir):
            g = _layer("genres", genre, rules_dir)
            out[f"{site}-{genre}"] = f"{s.get('name', site)}: {g.get('name', genre)}"
    return out


def split(profile, rules_dir=None):
    """'edmgp-tech-house' -> ('edmgp', 'tech-house')."""
    for site in sorted(_names("sites", rules_dir), key=len, reverse=True):
        if profile.startswith(site + "-"):
            return site, profile[len(site) + 1:]
    raise FileNotFoundError(f"No rules for profile '{profile}'")


def load(profile, rules_dir=None):
    site, genre = split(profile, rules_dir)
    s = _layer("sites", site, rules_dir)
    g = _layer("genres", genre, rules_dir)
    if not s or not g:
        raise FileNotFoundError(f"No rules for profile '{profile}'")
    rules = _merge(s, s.get("genres", {}).get(genre, {}))
    rules.pop("genres", None)
    rules.update({"id": profile, "site": site, "genre": genre, "genre_name": g.get("name", genre),
                  "bpm": g.get("bpm", 120)})
    rules.setdefault("length", {})["plan_extended_seconds"] = g.get("plan_extended_seconds")
    rules["display"] = f"{s.get('name', site)}: {g.get('name', genre)}"
    return rules

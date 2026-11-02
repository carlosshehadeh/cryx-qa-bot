import copy
import os

import pytest

from qabot import rules as rules_mod
from qabot.config import Config
from qabot.context import Context
from qabot.scan import scan
from tests import make_fixtures

BANNED = ["Carlos Test", "C:\\Users\\Carlos"]
# Short masters keep the tests quick; master_length tests ask for real lengths.
SHORT = {"extended_seconds": 130, "radio_seconds": 125}


@pytest.fixture(scope="session", autouse=True)
def data_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    os.environ["CRYX_QA_DATA"] = str(d)
    return d


@pytest.fixture(scope="session")
def export(tmp_path_factory):
    """make export(title, **variant) once per session and reuse it."""
    root = tmp_path_factory.mktemp("exports")
    made = {}

    def make(title="Good Track", **kw):
        kw = {**SHORT, **kw}
        key = (title, tuple(sorted(kw.items())))
        if key not in made:
            made[key] = make_fixtures.make_export(root / str(len(made)), title=title,
                                                  master_cache=root / ".masters", **kw)
        return made[key]
    return make


@pytest.fixture
def config(tmp_path):
    cfg = Config()
    cfg.banned_words = list(BANNED)
    cfg.output_folder = str(tmp_path / "out")
    return cfg


@pytest.fixture
def ctx_for(config):
    """Context for one export, with optional rule changes: ctx_for(folder, master={"lufs_min": -10})."""
    def make(folder, include_project=False, profile="edmgp-tech-house", **rule_changes):
        rules = copy.deepcopy(rules_mod.load(profile))
        for section, values in rule_changes.items():
            rules[section].update(values)
        return Context(scan(folder, config), rules, config, include_project=include_project)
    return make


def levels(results, check_id=None):
    return [r.level for r in results if check_id is None or r.check_id == check_id]

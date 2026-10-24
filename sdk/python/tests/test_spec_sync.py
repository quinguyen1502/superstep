"""The hand-written models follow the public spec (docs/api/openapi.public.json)."""
import json
import pathlib
import typing
from dataclasses import fields

import pytest

from superstep import Run, RunMetrics, RunStatus, RunWaiting
from superstep._errors import BY_CODE

SPEC = pathlib.Path(__file__).resolve().parents[3] / "docs/api/openapi.public.json"
pytestmark = pytest.mark.skipif(not SPEC.exists(), reason="run inside the superstep repository")


def schemas():
    return json.loads(SPEC.read_text())["components"]["schemas"]


def props(name):
    return set(schemas()[name]["properties"])


def names(cls):
    return {f.name for f in fields(cls)} - {"raw"}


def test_models_match_the_spec():
    assert names(Run) == props("RunResult") | props("RunAccepted") | props("RunPending")
    assert names(RunMetrics) == props("RunMetrics") and names(RunWaiting) == props("RunWaiting")
    assert set(typing.get_args(RunStatus)) == set(schemas()["RunResult"]["properties"]["status"]["enum"])


def test_every_documented_error_code_is_mapped():
    spec = json.loads(SPEC.read_text())
    codes = {code for item in spec["paths"].values() for op in item.values() for r in op["responses"].values()
             for code in r["content"]["application/json"].get("examples", {})}
    assert codes and codes <= set(BY_CODE)

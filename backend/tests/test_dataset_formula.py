import json
from pathlib import Path

import pytest

from app.core.dataset_formula import (
    MAX_DEPTH,
    MAX_SOURCE,
    MAX_TOKENS,
    FormulaDefinitionError,
    compile_formulas,
    evaluate_formulas,
)
from app.core.dataset_types import MAX_TEXT

CONTRACT = json.loads((Path(__file__).parent / "fixtures" / "dataset_formula_contract.json").read_text())


@pytest.mark.parametrize("case", CONTRACT["valid"], ids=lambda case: case["name"])
def test_formula_evaluation_contract(case):
    formulas = compile_formulas(case["fields"], case["expressions"])
    row = case["row"].copy()
    values, errors = evaluate_formulas(formulas, row)
    assert values == case["values"]
    assert errors == case["errors"]
    assert row == case["row"]


@pytest.mark.parametrize("case", CONTRACT["invalid"], ids=lambda case: case["name"])
def test_formula_diagnostic_contract(case):
    with pytest.raises(FormulaDefinitionError) as error:
        compile_formulas(case["fields"], case["expressions"])
    actual = {attribute: value for attribute, value in vars(error.value).items() if value is not None}
    assert actual == case["diagnostic"]


@pytest.mark.parametrize("source", [
    "1" + " " * MAX_SOURCE,
    "1+" * (MAX_TOKENS // 2) + "1",
    "(" * (MAX_DEPTH + 1) + "1" + ")" * (MAX_DEPTH + 1),
])
def test_formula_compilation_limits(source):
    with pytest.raises(FormulaDefinitionError) as error:
        compile_formulas({"total": "number"}, {"total": source})
    assert error.value.reason == "limit"


def test_limit_is_measured_in_code_points_and_applies_to_concatenation():
    formulas = compile_formulas({"title": "text", "result": "text"}, {"result": '[title] & "⭐"'})
    allowed = "🚀" * (MAX_TEXT - 1)
    assert evaluate_formulas(formulas, {"title": allowed}) == ({"result": allowed + "⭐"}, {})
    assert evaluate_formulas(formulas, {"title": allowed + "⭐"}) == ({"result": None}, {"result": "text_length"})


def test_dependency_order_and_stable_distinct_references():
    formulas = compile_formulas(
        {"price": "number", "price_twice": "number", "adjusted": "number"},
        {"adjusted": "[price_twice] - [price]", "price_twice": "[price] + [price]"},
    )
    assert list(formulas) == ["price_twice", "adjusted"]
    assert formulas["price_twice"].dependencies == ("price",)
    assert formulas["adjusted"].dependencies == ("price_twice", "price")

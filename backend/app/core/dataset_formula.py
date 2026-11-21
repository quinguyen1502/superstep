"""Compile and evaluate the bounded, same-row Dataset Formula language."""

from __future__ import annotations

import json
import math
import operator
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Literal

from .dataset_types import INVALID_TEXT, MAX_COLUMNS, MAX_SAFE_INTEGER, MAX_TEXT, TEXT_KINDS, CellValue

FormulaKind = Literal["number", "boolean", "text"]
FORMULA_KINDS = frozenset({"number", "boolean", "text"})
MAX_SOURCE = 1024
MAX_TOKENS = 256
MAX_DEPTH = 24

_TOKEN = re.compile(
    r'(?P<space>[ \t\r\n]+)|(?P<field>\[[a-z][a-z0-9_]{0,62}\])|'
    r'(?P<number>[0-9]+(?:\.[0-9]+)?(?:[Ee][+-]?[0-9]+)?)|'
    r'(?P<text>"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*")|'
    r'(?P<keyword>[A-Za-z][A-Za-z0-9_]*)|(?P<symbol>==|!=|<=|>=|[-+*/&<>,()])'
)
_OPERATORS = {
    "==": operator.eq, "!=": operator.ne,
    "<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge,
    "&": operator.add, "+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv,
}
_PRECEDENCE = {
    "==": 1, "!=": 1, "<": 1, "<=": 1, ">": 1, ">=": 1,
    "&": 2, "+": 3, "-": 3, "*": 4, "/": 4,
}


class FormulaDefinitionError(ValueError):
    """A structural diagnostic with a zero-based source offset, when applicable."""

    def __init__(self, reason: str, *, offset: int | None = None, field: str | None = None,
                 column: str | None = None):
        super().__init__(reason)
        self.reason = reason
        self.offset = offset
        self.field = field
        self.column = column


class _FormulaCellError(ValueError):
    """A row's evaluation error without input values in the diagnostic."""


@dataclass(frozen=True, slots=True)
class _Token:
    kind: str
    text: str
    offset: int


@dataclass(frozen=True, slots=True)
class _Expression:
    op: str
    kind: FormulaKind
    args: tuple[_Expression, ...] = ()
    value: CellValue = None


@dataclass(frozen=True, slots=True)
class Formula:
    expression: _Expression
    dependencies: tuple[str, ...]


def _tokens(source: str) -> Iterator[_Token]:
    if len(source) > MAX_SOURCE:
        raise FormulaDefinitionError("limit", offset=MAX_SOURCE)
    offset, count = 0, 0
    while offset < len(source):
        match = _TOKEN.match(source, offset)
        if match is None:
            raise FormulaDefinitionError("syntax", offset=offset)
        kind = match.lastgroup
        if kind != "space":
            count += 1
            if count > MAX_TOKENS:
                raise FormulaDefinitionError("limit", offset=offset)
            yield _Token(kind, match[0], offset)
        offset = match.end()
    yield _Token("end", "", offset)


def _scalar_kind(kind: str | None) -> FormulaKind | None:
    if kind in TEXT_KINDS:
        return "text"
    if kind in {"number", "auto_number"}:
        return "number"
    if kind == "boolean":
        return "boolean"
    return None


def _binary_kind(token: _Token, left: FormulaKind, right: FormulaKind) -> FormulaKind:
    match token.text:
        case "==" | "!=" if left == right:
            return "boolean"
        case "<" | "<=" | ">" | ">=" if left == right == "number":
            return "boolean"
        case "&" if left == right == "text":
            return "text"
        case "+" | "-" | "*" | "/" if left == right == "number":
            return "number"
    raise FormulaDefinitionError("type", offset=token.offset)


class _Parser:
    def __init__(self, source: str, fields: Mapping[str, str]):
        self.tokens = _tokens(source)
        self.current = next(self.tokens)
        self.fields = fields
        self.dependencies: dict[str, None] = {}

    def _next(self) -> _Token:
        token = self.current
        if token.kind != "end":
            self.current = next(self.tokens)
        return token

    def _expect(self, symbol: str) -> None:
        token = self._next()
        if token.kind != "symbol" or token.text != symbol:
            raise FormulaDefinitionError("syntax", offset=token.offset)

    def parse(self, result_kind: FormulaKind) -> Formula:
        expression = self._expression(1, 0)
        if self.current.kind != "end":
            raise FormulaDefinitionError("syntax", offset=self.current.offset)
        if expression.kind != result_kind:
            raise FormulaDefinitionError("result_type")
        return Formula(expression, tuple(self.dependencies))

    def _expression(self, minimum: int, depth: int) -> _Expression:
        if depth > MAX_DEPTH:
            raise FormulaDefinitionError("limit", offset=self.current.offset)
        left = self._prefix(depth)
        while self.current.kind == "symbol" and _PRECEDENCE.get(self.current.text, 0) >= minimum:
            token = self._next()
            right = self._expression(_PRECEDENCE[token.text] + 1, depth + 1)
            kind = _binary_kind(token, left.kind, right.kind)
            left = _Expression(token.text, kind, (left, right))
        return left

    def _prefix(self, depth: int) -> _Expression:
        token = self._next()
        if token.kind == "field":
            key = token.text[1:-1]
            if key not in self.fields:
                raise FormulaDefinitionError("unknown_field", offset=token.offset, field=key)
            kind = _scalar_kind(self.fields[key])
            if kind is None:
                raise FormulaDefinitionError("field_type", offset=token.offset, field=key)
            self.dependencies[key] = None
            return _Expression("field", kind, value=key)
        if token.kind == "number":
            value = float(token.text)
            if not math.isfinite(value) or value > MAX_SAFE_INTEGER:
                raise FormulaDefinitionError("numeric_range", offset=token.offset)
            return _Expression("literal", "number", value=value)
        if token.kind == "text":
            value = json.loads(token.text)
            if INVALID_TEXT.search(value):
                raise FormulaDefinitionError("syntax", offset=token.offset)
            return _Expression("literal", "text", value=value)
        if token.kind == "keyword":
            if token.text in {"true", "false"}:
                return _Expression("literal", "boolean", value=token.text == "true")
            if token.text == "IF":
                return self._conditional(token, depth)
        if token.kind == "symbol":
            if token.text == "(":
                inside = self._expression(1, depth + 1)
                self._expect(")")
                return inside
            if token.text in {"+", "-"}:
                operand = self._expression(5, depth + 1)
                if operand.kind != "number":
                    raise FormulaDefinitionError("type", offset=token.offset)
                return _Expression("positive" if token.text == "+" else "negative", "number", (operand,))
        raise FormulaDefinitionError("syntax", offset=token.offset)

    def _conditional(self, token: _Token, depth: int) -> _Expression:
        self._expect("(")
        condition = self._expression(1, depth + 1)
        self._expect(",")
        yes = self._expression(1, depth + 1)
        self._expect(",")
        no = self._expression(1, depth + 1)
        self._expect(")")
        if condition.kind != "boolean" or yes.kind != no.kind:
            raise FormulaDefinitionError("type", offset=token.offset)
        return _Expression("if", yes.kind, (condition, yes, no))


def compile_formulas(fields: Mapping[str, str], expressions: Mapping[str, str]) -> dict[str, Formula]:
    """Validate definitions and return Formulas ordered after their dependencies."""
    if len(fields) > MAX_COLUMNS or len(expressions) > MAX_COLUMNS:
        raise FormulaDefinitionError("limit")
    compiled = {}
    for key, source in expressions.items():
        kind = fields.get(key)
        if kind not in FORMULA_KINDS:
            raise FormulaDefinitionError("result_type", column=key)
        try:
            compiled[key] = _Parser(source, fields).parse(kind)
        except FormulaDefinitionError as exc:
            raise FormulaDefinitionError(exc.reason, offset=exc.offset, field=exc.field, column=key) from exc

    ordered, visiting = {}, set()

    def visit(key: str) -> None:
        if key in visiting:
            raise FormulaDefinitionError("cycle", column=key)
        visiting.add(key)
        for dependency in compiled[key].dependencies:
            if dependency in compiled and dependency not in ordered:
                visit(dependency)
        visiting.remove(key)
        ordered[key] = compiled[key]

    for key in compiled:
        if key not in ordered:
            visit(key)
    return ordered


def _number(value: CellValue) -> float:
    if type(value) not in (int, float):
        raise _FormulaCellError("invalid_input")
    if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
        raise _FormulaCellError("numeric_range")
    return float(value) if value else 0.0


def _text(value: CellValue) -> str:
    if not isinstance(value, str) or INVALID_TEXT.search(value):
        raise _FormulaCellError("invalid_input")
    if len(value) > MAX_TEXT:
        raise _FormulaCellError("text_length")
    return value


def _evaluate(node: _Expression, values: Mapping[str, CellValue], errors: Mapping[str, str]) -> CellValue:
    if node.op == "literal":
        return node.value
    if node.op == "field":
        key = node.value
        if key in errors:
            raise _FormulaCellError("dependency")
        value = values.get(key)
        if value is None:
            return None
        if node.kind == "number":
            return _number(value)
        if node.kind == "text":
            return _text(value)
        if type(value) is bool:
            return value
        raise _FormulaCellError("invalid_input")

    left = _evaluate(node.args[0], values, errors)
    if node.op == "if":
        return None if left is None else _evaluate(node.args[1 if left else 2], values, errors)
    if node.op in {"positive", "negative"}:
        if left is None:
            return None
        return _number(left if node.op == "positive" else -left)

    right = _evaluate(node.args[1], values, errors)
    if left is None or right is None:
        return None
    if node.op == "/" and right == 0:
        raise _FormulaCellError("division_by_zero")
    result = _OPERATORS[node.op](left, right)
    if node.kind == "number":
        return _number(result)
    if node.kind == "text":
        return _text(result)
    return result


def evaluate_formulas(formulas: Mapping[str, Formula], row: Mapping[str, CellValue]) -> tuple[dict[str, CellValue], dict[str, str]]:
    """Compute fresh typed values and diagnostics in dependency order without modifying the input row."""
    if not formulas:
        return {}, {}
    values = dict(row)
    results, errors = {}, {}
    for key, formula in formulas.items():
        try:
            values[key] = results[key] = _evaluate(formula.expression, values, errors)
        except _FormulaCellError as exc:
            values[key] = results[key] = None
            errors[key] = str(exc)
    return results, errors

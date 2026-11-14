"""Validation and presentation options for a Dataset column."""
import re

from .dataset_types import DATETIME_KINDS, MAX_TEXT, normalize_cell
from .errors import AppError


def column_rules(field, kind, rules):
    rules = {key: value for key, value in (rules or {}).items() if value is not None}
    allowed = {
        "text": {"min_length", "max_length"}, "long_text": {"min_length", "max_length"},
        "number": {"min", "max", "integer"}, "date": {"min", "max"}, "datetime": {"min", "max"},
        "email": {"domains"},
    }.get(kind, set())
    if rules.keys() - allowed:
        raise AppError("DATASET_DEFINITION_INVALID", field=field)
    if any(not 0 <= rules[key] <= MAX_TEXT for key in ("min_length", "max_length") if key in rules):
        raise AppError("DATASET_DEFINITION_INVALID", field=field)
    for key in ("min", "max"):
        if key in rules:
            rules[key] = normalize_cell(field, kind, rules[key], [], required=True)
    for lower, upper in [("min_length", "max_length"), ("min", "max")]:
        if lower in rules and upper in rules and rules[lower] > rules[upper]:
            raise AppError("DATASET_DEFINITION_INVALID", field=field)
    if "domains" in rules:
        domains = sorted(set(domain.strip().lower() for domain in rules["domains"]))
        if not domains or any(not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", domain) for domain in domains):
            raise AppError("DATASET_DEFINITION_INVALID", field=field)
        rules["domains"] = domains
    return rules


def column_display(field, kind, settings):
    settings = {key: value for key, value in (settings or {}).items() if value is not None}
    allowed = {"decimals", "thousands", "style", "currency"} if kind == "number" else (
        {"date_style"} if kind == "date" or kind in DATETIME_KINDS else set()
    )
    if settings.keys() - allowed:
        raise AppError("DATASET_DEFINITION_INVALID", field=field)
    if settings.get("style") == "currency" and "currency" not in settings:
        raise AppError("DATASET_DEFINITION_INVALID", field=field)
    return settings


def violates_rule(value, rules):
    if value is None or not rules:
        return False
    if "min_length" in rules and len(value) < rules["min_length"]:
        return True
    if "max_length" in rules and len(value) > rules["max_length"]:
        return True
    if "min" in rules and value < rules["min"]:
        return True
    if "max" in rules and value > rules["max"]:
        return True
    if rules.get("integer") and int(value) != value:
        return True
    return "domains" in rules and value.rsplit("@", 1)[-1] not in rules["domains"]


def enforce_rules(field, value, rules):
    if violates_rule(value, rules):
        raise AppError("DATASET_COLUMN_RULE_VIOLATION", field=field, details={"field": field})
    return value

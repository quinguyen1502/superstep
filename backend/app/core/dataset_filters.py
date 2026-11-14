"""Bounds and traversal for Dataset filter trees, including workflow templates."""
import re
from collections.abc import Iterator

from .dataset_types import COLUMN_KEY_PATTERN, FILTER_OPERATORS

MAX_FILTER_DEPTH = 3
MAX_FILTER_RULES = 20
MAX_FILTER_VALUES = 50
LIST_FILTERS = frozenset({"in", "not_in", "contains_any", "contains_all"})


def tree_rules(tree: dict) -> Iterator[tuple[tuple[int, ...], dict]]:
    """Validate the tree shape and yield one-based paths in display order."""
    count = 0

    def visit(group, path):
        nonlocal count
        if len(path) >= MAX_FILTER_DEPTH:
            raise ValueError(f"Filter tree supports at most {MAX_FILTER_DEPTH} group levels")
        if (not isinstance(group, dict) or set(group) != {"type", "conjunction", "children"}
                or group["type"] != "group" or group["conjunction"] not in ("and", "or")
                or not isinstance(group["children"], list) or not group["children"]):
            raise ValueError("Expected a nonempty AND/OR filter group")
        if len(group["children"]) > MAX_FILTER_RULES:
            raise ValueError(f"Filter tree supports at most {MAX_FILTER_RULES} rules")
        for index, item in enumerate(group["children"], 1):
            position = (*path, index)
            if isinstance(item, dict) and item.get("type") == "group":
                yield from visit(item, position)
                continue
            if (not isinstance(item, dict) or set(item) - {"type", "field", "op", "value"}
                    or item.get("type") != "rule" or not isinstance(item.get("field"), str)
                    or not re.fullmatch(COLUMN_KEY_PATTERN, item["field"])
                    or item.get("op") not in FILTER_OPERATORS):
                where = ".".join(map(str, position))
                raise ValueError(f"Invalid filter rule at {where}")
            count += 1
            if count > MAX_FILTER_RULES:
                raise ValueError(f"Filter tree supports at most {MAX_FILTER_RULES} rules")
            yield position, item

    yield from visit(tree, ())


def filter_rules(arguments: dict) -> Iterator[tuple[tuple[int, ...], dict]]:
    tree = arguments.get("filter_tree")
    if tree is not None:
        yield from tree_rules(tree)
    else:
        yield from (((index,), rule) for index, rule in enumerate(arguments.get("filters", []), 1))

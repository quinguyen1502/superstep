from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, List

from .models import AdapterPreview, ScaffoldTarget


class ScaffoldAdapter(ABC):
    """Contract implemented by deterministic templates or official CLI wrappers."""

    adapter_id: str
    adapter_version: int = 1

    @abstractmethod
    def supports(self, target: ScaffoldTarget) -> bool:
        """Return whether this adapter owns one approved technology target."""

    @abstractmethod
    def preview(self, targets: List[ScaffoldTarget]) -> AdapterPreview:
        """Describe availability, command, and expected outputs without writing."""

    @abstractmethod
    def execute(self, targets: List[ScaffoldTarget], staging_dir: Path) -> None:
        """Generate files only below staging_dir or raise an exception."""

    def validate(self, targets: List[ScaffoldTarget], staging_dir: Path) -> List[str]:
        """Return blocking validation findings for staged output."""
        return []


class ScaffoldRegistry:
    def __init__(self, adapters: Iterable[ScaffoldAdapter] = ()) -> None:
        self.adapters = list(adapters)
        identifiers = [adapter.adapter_id for adapter in self.adapters]
        duplicates = sorted(
            identifier for identifier in set(identifiers) if identifiers.count(identifier) > 1
        )
        if duplicates:
            raise ValueError(f"Duplicate scaffold adapters: {', '.join(duplicates)}")

    def matching(self, target: ScaffoldTarget) -> List[ScaffoldAdapter]:
        return [adapter for adapter in self.adapters if adapter.supports(target)]

    def get(self, adapter_id: str) -> ScaffoldAdapter:
        matches = [adapter for adapter in self.adapters if adapter.adapter_id == adapter_id]
        if not matches:
            raise KeyError(adapter_id)
        return matches[0]


def default_scaffold_registry() -> ScaffoldRegistry:
    """Return safe built-in wrappers for supported official generators."""
    from .providers import builtin_scaffold_adapters

    return ScaffoldRegistry(builtin_scaffold_adapters())

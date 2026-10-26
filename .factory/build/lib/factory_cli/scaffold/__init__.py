"""Safe project source scaffolding primitives."""

from .adapters import ScaffoldAdapter, ScaffoldRegistry, default_scaffold_registry
from .models import (
    AdapterPreview,
    ScaffoldAction,
    ScaffoldOutput,
    ScaffoldPlan,
    ScaffoldPublishPlan,
    ScaffoldTarget,
)
from .service import (
    ScaffoldError,
    apply_scaffold_plan,
    create_scaffold_plan,
    scaffold_problems,
    stage_scaffold,
)

__all__ = [
    "AdapterPreview",
    "ScaffoldAction",
    "ScaffoldAdapter",
    "ScaffoldError",
    "ScaffoldOutput",
    "ScaffoldPlan",
    "ScaffoldPublishPlan",
    "ScaffoldRegistry",
    "ScaffoldTarget",
    "apply_scaffold_plan",
    "create_scaffold_plan",
    "default_scaffold_registry",
    "scaffold_problems",
    "stage_scaffold",
]

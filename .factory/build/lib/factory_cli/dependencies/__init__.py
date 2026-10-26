"""Project-local dependency planning, installation, and validation."""

from .models import DependencyCommand, DependencyPlan
from .service import (
    DependencyError,
    apply_dependency_plan,
    create_dependency_plan,
    dependency_problems,
    render_dependency_review,
)

__all__ = [
    "DependencyCommand",
    "DependencyError",
    "DependencyPlan",
    "apply_dependency_plan",
    "create_dependency_plan",
    "dependency_problems",
    "render_dependency_review",
]

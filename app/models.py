"""Pydantic models for request and response payloads."""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HealthStatus = Literal["healthy", "degraded", "unhealthy", "unknown"]


class ComponentInput(BaseModel):
    """Represents a single component in the request payload."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Unique component name.")
    health_check_url: str | None = Field(
        default=None,
        description="Optional health check URL for the component.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Ensure component names are not blank."""
        if not value.strip():
            raise ValueError("Component name cannot be empty.")
        return value.strip()


class HealthEvaluationRequest(BaseModel):
    """Top-level request model for evaluating a system DAG."""

    model_config = ConfigDict(extra="forbid")

    components: list[ComponentInput] = Field(
        ...,
        min_length=1,
        description="Components that make up the system graph.",
    )
    dependencies: list[list[str]] = Field(
        default_factory=list,
        description='Pairs in the form ["dependent", "dependency"].',
    )

    @model_validator(mode="after")
    def validate_unique_component_names(self) -> "HealthEvaluationRequest":
        """Ensure component names are unique across the request."""
        name_counts = Counter(component.name for component in self.components)
        duplicates = sorted(name for name, count in name_counts.items() if count > 1)
        if duplicates:
            duplicate_list = ", ".join(duplicates)
            raise ValueError(f"Duplicate component names found: {duplicate_list}.")
        return self

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, value: list[list[str]]) -> list[list[str]]:
        """Ensure dependency pairs contain valid, non-empty names."""
        for edge in value:
            if len(edge) != 2:
                raise ValueError(
                    'Each dependency must contain exactly two values: ["dependent", "dependency"].'
                )
            dependent, dependency = edge
            if not dependent.strip() or not dependency.strip():
                raise ValueError("Dependency references must contain non-empty component names.")
        return value

    def dependency_pairs(self) -> list[tuple[str, str]]:
        """Return dependency edges normalized as tuples."""
        return [(dependent, dependency) for dependent, dependency in self.dependencies]


class SummaryRow(BaseModel):
    """Human-readable row describing a component's evaluated health."""

    component: str
    own_status: HealthStatus
    effective_status: HealthStatus
    dependencies: list[str]
    reason: str


class HealthEvaluationResponse(BaseModel):
    """Response returned by the health evaluation API."""

    overall_status: HealthStatus
    bfs_traversal_order: list[str]
    summary_table: list[SummaryRow]
    summary_table_markdown: str


class ErrorResponse(BaseModel):
    """Consistent error payload returned for invalid requests."""

    message: str
    errors: list[str]

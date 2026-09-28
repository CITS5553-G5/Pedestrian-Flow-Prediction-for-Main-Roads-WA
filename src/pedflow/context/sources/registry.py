"""Context sources used by the selected model's formal prediction workflow."""

from __future__ import annotations

from pedflow.context.contracts import SourceDefinition


def build_default_registry() -> dict[str, SourceDefinition]:
    """Register only ABS; other source modules remain available for research."""

    from pedflow.context.sources import abs_meshblock_sa1

    return {abs_meshblock_sa1.DEFINITION.name: abs_meshblock_sa1.DEFINITION}

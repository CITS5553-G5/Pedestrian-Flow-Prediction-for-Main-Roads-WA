"""Approved context sources plus explicit guards for excluded experiments."""

from __future__ import annotations

from pedflow.context.contracts import SourceDefinition


def build_default_registry() -> dict[str, SourceDefinition]:
    """Return the approved source definitions keyed by configuration name."""

    from pedflow.context.sources import (
        abs_meshblock_sa1,
        google_places_aggregate_poi,
        microsoft_building_footprints,
        overture_places,
        pta_stops,
        wa_education_schools,
        wa_health_establishments,
    )

    definitions = (
        abs_meshblock_sa1.DEFINITION,
        pta_stops.DEFINITION,
        wa_health_establishments.DEFINITION,
        wa_education_schools.DEFINITION,
        microsoft_building_footprints.DEFINITION,
        overture_places.DEFINITION,
        google_places_aggregate_poi.DEFINITION,
    )
    return {definition.name: definition for definition in definitions}

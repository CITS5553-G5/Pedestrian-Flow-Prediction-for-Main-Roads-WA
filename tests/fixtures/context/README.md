# Context test fixtures

Place only small, licence-compatible, non-secret source extracts here. Each fixture
must record its origin, snapshot date, purpose, permitted sharing scope, and the test
that consumes it. Do not copy full external datasets, API keys, unrestricted API
responses, or client-confidential source material into this directory.

`pta_stops_small.geojson` is a fully synthetic, hand-authored FeatureCollection dated
2 September 2026 for `tests/unit/test_pta_stops.py`. It is not copied from PTA-001 and
contains no real source record or credential. It represents two active stops, one
planned stop and one exact duplicate so cleaning, filtering and spatial logic can be
tested deterministically. It may be shared with the project test suite.

`wa_health_establishments_fixture.geojson` is a fully synthetic Health-001-shaped
fixture created on 2 September 2026 for the WA Health unit tests. It
contains two open eligible establishments and one closed establishment, allowing the
schema, filtering, nearest matching, and mocked retrieval paths to be tested without
network access or redistribution of official source records. Its identifiers, names,
coordinates, and attributes are invented and it contains no credential or secret.

`overture_places_small.geojson` is a fully synthetic Overture-Places-shaped fixture
created on 8 September 2026. It contains invented food, shopping, closed, distant and
non-shopping records for deterministic taxonomy, operating-status, distance and cache
tests. It is not copied from Overture or any commercial map and contains no real place.

import json
from pathlib import Path

import pytest

freeze_time = pytest.importorskip("freezegun").freeze_time

from scraper.pipeline.merge import update_first_seen
from scraper.pipeline.validate import validate_event
from scraper.utils.events import generate_slug, normalize_price


@freeze_time("2026-02-03 12:00:00")
def test_golden_events_snapshot():
    fixtures_path = Path("tests/fixtures/events_input.json")
    golden_path = Path("tests/golden/events_v1.json")

    events = json.loads(fixtures_path.read_text())

    events = [normalize_price(event) for event in events]
    for event in events:
        event["slug"] = generate_slug(event)

    valid_events = [event for event in events if validate_event(event)]

    seen_cache = {"events": {}, "last_updated": None}
    updated_events, _ = update_first_seen(valid_events, seen_cache)
    updated_events.sort(key=lambda event: event["slug"])

    expected = json.loads(golden_path.read_text())
    expected.sort(key=lambda event: event["slug"])

    assert updated_events == expected

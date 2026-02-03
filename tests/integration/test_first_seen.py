from scraper.pipeline.merge import update_first_seen


def test_update_first_seen_marks_new_events():
    events = [
        {"slug": "event-1", "date": "2026-02-01"},
        {"slug": "event-2", "date": "2026-02-02"},
    ]
    seen_cache = {"events": {}, "last_updated": None}

    updated, new_count = update_first_seen(events, seen_cache)

    assert new_count == 2
    assert updated[0]["first_seen"]
    assert seen_cache["events"]["event-1"]["first_seen"]

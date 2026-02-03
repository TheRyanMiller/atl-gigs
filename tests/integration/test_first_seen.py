from freezegun import freeze_time

from scrape import update_first_seen


@freeze_time("2026-02-01T12:00:00Z")
def test_update_first_seen_sets_is_new_and_cache():
    events = [
        {"slug": "event-1"},
        {"slug": "event-2"},
    ]
    seen_cache = {"events": {}, "last_updated": None}

    updated, new_count = update_first_seen(events, seen_cache)

    assert new_count == 2
    assert all(e.get("is_new") is True for e in updated)
    assert "event-1" in seen_cache["events"]


@freeze_time("2026-02-10T12:00:00Z")
def test_update_first_seen_preserves_false_is_new():
    events = [
        {"slug": "event-1", "is_new": False},
    ]
    seen_cache = {"events": {"event-1": {"first_seen": "2026-01-01T00:00:00Z"}}, "last_updated": None}

    updated, _ = update_first_seen(events, seen_cache)
    assert updated[0]["is_new"] is False

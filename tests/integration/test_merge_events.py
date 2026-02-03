from scraper.pipeline.merge import merge_events


def test_merge_events_preserves_existing_first_seen():
    existing = [
        {
            "ticket_url": "https://tickets/1",
            "first_seen": "2025-01-01T00:00:00Z",
            "slug": "event-1",
            "is_new": False,
        }
    ]
    new = [
        {"ticket_url": "https://tickets/1", "slug": "event-1", "is_new": True}
    ]

    merged = merge_events(existing, new)

    assert merged[0]["first_seen"] == "2025-01-01T00:00:00Z"
    assert merged[0]["is_new"] is False

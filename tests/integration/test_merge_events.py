from scrape import merge_events


def test_merge_events_preserves_first_seen_and_is_new():
    existing = [
        {
            "ticket_url": "https://example.com/a",
            "slug": "2026-02-01-venue-artist",
            "first_seen": "2026-01-01T00:00:00Z",
            "is_new": False,
        },
        {
            "ticket_url": "https://example.com/b",
            "slug": "2026-02-02-venue-artist",
        },
    ]
    new = [
        {
            "ticket_url": "https://example.com/a",
            "slug": "2026-02-01-venue-artist",
        },
    ]

    merged = merge_events(existing, new)
    by_url = {e["ticket_url"]: e for e in merged}

    assert by_url["https://example.com/a"]["first_seen"] == "2026-01-01T00:00:00Z"
    assert by_url["https://example.com/a"]["is_new"] is False
    assert "https://example.com/b" in by_url

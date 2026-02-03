from datetime import datetime

from scraper import config


def merge_events(existing_events, new_events):
    """
    Merge new events with existing events.
    - New events update existing ones by ticket_url (primary key)
    - Past events (not in new scrape) are preserved
    - is_new=False is also preserved by slug (in case ticket_url changes)
    Returns merged list.
    """
    events_by_url = {e.get("ticket_url"): e for e in existing_events if e.get("ticket_url")}

    is_new_false_by_slug = {
        e.get("slug"): True
        for e in existing_events
        if e.get("slug") and e.get("is_new") is False
    }

    for event in new_events:
        url = event.get("ticket_url")
        if url:
            if url in events_by_url:
                existing = events_by_url[url]
                if "first_seen" in existing and "first_seen" not in event:
                    event["first_seen"] = existing["first_seen"]
                if existing.get("is_new") is False:
                    event["is_new"] = False

            if event.get("slug") in is_new_false_by_slug:
                event["is_new"] = False

            events_by_url[url] = event

    return list(events_by_url.values())


def update_first_seen(events, seen_cache):
    """
    Update events with first_seen field, calculate is_new, and update the seen cache.
    Returns (updated_events, new_event_count).
    """
    now = datetime.utcnow()
    now_str = now.isoformat() + "Z"
    new_count = 0

    for event in events:
        slug = event.get("slug")
        if not slug:
            continue

        if slug in seen_cache["events"]:
            event["first_seen"] = seen_cache["events"][slug]["first_seen"]
        else:
            event["first_seen"] = now_str
            seen_cache["events"][slug] = {"first_seen": now_str}
            new_count += 1

        if event.get("is_new") is False:
            pass
        else:
            try:
                first_seen_dt = datetime.fromisoformat(event["first_seen"].replace("Z", "+00:00"))
                first_seen_dt = first_seen_dt.replace(tzinfo=None)
                days_since_seen = (now - first_seen_dt).total_seconds() / (60 * 60 * 24)
                event["is_new"] = days_since_seen <= config.NEW_EVENT_DAYS
            except Exception:
                event["is_new"] = False

    return events, new_count


def prune_seen_cache(seen_cache, current_slugs):
    """Remove cache entries for events no longer tracked."""
    seen_cache["events"] = {
        slug: data
        for slug, data in seen_cache["events"].items()
        if slug in current_slugs
    }
    return seen_cache

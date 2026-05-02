from scraper import config


def validate_event(event):
    """Check that event has all required fields with valid data."""
    for field in config.REQUIRED_FIELDS:
        if not event.get(field):
            return False

    artists = event.get("artists") or []
    if not artists or not any(artist.get("name") for artist in artists):
        return False

    if event.get("category") not in config.CATEGORIES:
        return False
    return True

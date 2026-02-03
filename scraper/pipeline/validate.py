from scraper import config


def validate_event(event):
    """Check that event has all required fields with valid data."""
    for field in config.REQUIRED_FIELDS:
        if not event.get(field):
            return False
    if not event.get("artists") or len(event["artists"]) == 0:
        return False
    return True

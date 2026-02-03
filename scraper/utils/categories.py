import re


def detect_category_from_text(text):
    """
    Detect event category from text (title or URL path) using keyword analysis.
    Returns detected category or None if uncertain.
    Priority order: sports > comedy > concerts.
    """
    text_lower = text.lower()

    sports_patterns = [
        "sports",
        "basketball", "hoops", "hoopsgiving", "nba",
        "football", "nfl", "gridiron",
        "soccer", "mls", "fifa",
        "hockey", "nhl",
        "baseball", "mlb",
        "wrestling", "wwe", "aew", "raw", "smackdown",
        "boxing", "ufc", "mma", "fight night",
        "championship", "tournament", "playoffs",
        "vs",
    ]

    if any(pattern in text_lower for pattern in sports_patterns):
        return "sports"

    comedy_patterns = [
        "comedy",
        "comedian",
        "stand-up",
        "standup",
        "improv",
        "laugh",
    ]

    if any(pattern in text_lower for pattern in comedy_patterns):
        return "comedy"

    concert_patterns = [
        "concert",
        "concerts",
        "tour",
        "jam",
        "fest",
        "festival",
        "live music",
        "in concert",
    ]

    if any(pattern in text_lower for pattern in concert_patterns):
        return "concerts"

    return None


def detect_category_from_ticket_url(ticket_url):
    """
    Extract category hints from Ticketmaster URL paths.
    Returns detected category or None if URL doesn't contain useful info.
    """
    if not ticket_url or "ticketmaster.com" not in ticket_url:
        return None

    if "/event/" in ticket_url:
        path = ticket_url.split("ticketmaster.com/")[-1].split("/event/")[0]
        if path and path != "event":
            return detect_category_from_text(path.replace("-", " "))

    return None


def map_tm_classification(classifications, category_map):
    """
    Map Ticketmaster classification hierarchy to our category.
    Priority: genre > segment (more specific wins)
    """
    if not classifications:
        return "concerts"

    primary = classifications[0] if classifications else {}
    segment = primary.get("segment", {}).get("name", "")
    genre = primary.get("genre", {}).get("name", "")

    if genre in category_map:
        return category_map[genre]

    if segment in category_map:
        return category_map[segment]

    return "concerts"

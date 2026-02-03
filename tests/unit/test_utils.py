import pytest

from scraper.pipeline.validate import validate_event
from scraper.tm import TM_CATEGORY_MAP
from scraper.utils.categories import (
    detect_category_from_text,
    detect_category_from_ticket_url,
    map_tm_classification,
)
from scraper.utils.dates import normalize_time
from scraper.utils.events import generate_slug, is_zero_price, normalize_price
from scraper.spotify_enrichment import (
    normalize_artist_name,
    normalize_spotify_url,
    extract_spotify_artist_id,
    is_non_artist_name,
)


def test_normalize_time():
    assert normalize_time("8:00pm") == "20:00"
    assert normalize_time("8:00") == "08:00"
    assert normalize_time("20:00:00") == "20:00"
    assert normalize_time("12:00am") == "00:00"
    assert normalize_time("12:00pm") == "12:00"
    assert normalize_time("bad") is None


def test_normalize_price_adv_dos():
    event = {"adv_price": "$20", "dos_price": "$25"}
    result = normalize_price(event)
    assert result["price"] == "$20 ADV / $25 DOS"


def test_normalize_price_zero_free():
    event = {"price": "$0"}
    result = normalize_price(event)
    assert result["price"] == "See website"
    assert is_zero_price("$0.00") is True


def test_generate_slug_includes_stage_and_sanitizes():
    event = {
        "date": "2026-02-10",
        "venue": "Center Stage",
        "stage": "The Loft",
        "artists": [{"name": "The Filthy Frets!"}],
    }
    slug = generate_slug(event)
    assert slug.startswith("2026-02-10-center-stage-the-loft-the-filthy-frets")


def test_validate_event_required_fields():
    valid = {
        "venue": "The Earl",
        "date": "2026-02-01",
        "artists": [{"name": "Artist"}],
        "ticket_url": "https://example.com",
        "category": "concerts",
    }
    assert validate_event(valid) is True

    invalid = {
        "venue": "The Earl",
        "date": "2026-02-01",
        "artists": [],
        "ticket_url": "https://example.com",
        "category": "concerts",
    }
    assert validate_event(invalid) is False


def test_detect_category_from_text():
    assert detect_category_from_text("NBA Finals") == "sports"
    assert detect_category_from_text("Stand-up Comedy Night") == "comedy"
    assert detect_category_from_text("Summer Jam Festival") == "concerts"


def test_detect_category_from_ticket_url():
    url = "https://www.ticketmaster.com/cbs-sports-classic-2025/event/"
    assert detect_category_from_ticket_url(url) == "sports"
    assert detect_category_from_ticket_url("https://example.com") is None


def test_map_tm_classification_priority():
    classifications = [
        {"segment": {"name": "Music"}, "genre": {"name": "Comedy"}}
    ]
    assert map_tm_classification(classifications, TM_CATEGORY_MAP) == "comedy"
    assert map_tm_classification([], TM_CATEGORY_MAP) == "concerts"


def test_spotify_helpers():
    assert normalize_artist_name("Artist feat. Guest") == "artist"
    assert is_non_artist_name("tba") is True
    assert extract_spotify_artist_id("https://open.spotify.com/artist/ABC123") == "ABC123"
    assert normalize_spotify_url("spotify:artist:XYZ") == "https://open.spotify.com/artist/XYZ"

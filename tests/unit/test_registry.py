from scraper import config
from scraper.registry import get_scrapers, with_empty_fallback


def test_with_empty_fallback_uses_primary_events():
    calls = {"fallback": 0}

    def primary():
        return [{"venue": "Primary"}]

    def fallback():
        calls["fallback"] += 1
        return [{"venue": "Fallback"}]

    assert with_empty_fallback(primary, fallback, "Venue")() == [{"venue": "Primary"}]
    assert calls["fallback"] == 0


def test_with_empty_fallback_uses_fallback_for_empty_primary():
    assert with_empty_fallback(lambda: [], lambda: [{"venue": "Fallback"}], "Venue")() == [
        {"venue": "Fallback"}
    ]


def test_get_scrapers_wraps_tm_venues_with_fallback(monkeypatch):
    monkeypatch.setattr(config, "USE_TM_API", True)
    monkeypatch.setattr(config, "TM_API_KEY", "test-key")
    monkeypatch.setattr("scraper.registry.scrape_state_farm_arena_tm", lambda: [])
    monkeypatch.setattr("scraper.registry.scrape_state_farm_arena", lambda: [{"venue": "State Farm Arena"}])

    scrapers = get_scrapers()

    assert scrapers["State Farm Arena"]() == [{"venue": "State Farm Arena"}]

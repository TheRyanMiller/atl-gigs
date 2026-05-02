from scraper.spotify_enrichment import (
    SPOTIFY_SEARCH_SOURCE_VERSION,
    _pick_spotify_candidate,
    enrich_events_with_spotify,
    normalize_artist_name,
    should_retry_negative_cache,
    spotify_search_artist,
    spotify_search_names,
)
from scraper import config
from scraper import spotify_enrichment
import requests


def test_pick_spotify_candidate_exact_match():
    candidates = [
        {"name": "Other Artist", "popularity": 10, "genres": ["rock"]},
        {"name": "Exact Match", "popularity": 40, "genres": ["rock"]},
    ]
    candidate, reason = _pick_spotify_candidate("Exact Match", candidates)
    assert candidate["name"] == "Exact Match"
    assert reason == "exact"


def test_pick_spotify_candidate_genre_overlap():
    candidates = [
        {"name": "Twin", "popularity": 10, "genres": ["hip hop"]},
        {"name": "Twin", "popularity": 15, "genres": ["jazz"]},
    ]
    candidate, reason = _pick_spotify_candidate("Twin", candidates, genre_hint="jazz")
    assert candidate["genres"] == ["jazz"]
    assert reason == "genre"


def test_pick_spotify_candidate_popularity_fallback():
    candidates = [
        {"name": "Same", "popularity": 90, "genres": []},
        {"name": "Same", "popularity": 60, "genres": []},
    ]
    candidate, reason = _pick_spotify_candidate("Same", candidates)
    assert candidate["popularity"] == 90
    assert reason == "popularity"


def test_pick_spotify_candidate_ambiguous():
    candidates = [
        {"name": "Same", "popularity": 50, "genres": []},
        {"name": "Same", "popularity": 45, "genres": []},
    ]
    candidate, reason = _pick_spotify_candidate("Same", candidates)
    assert candidate is None
    assert reason == "ambiguous"


def test_pick_spotify_candidate_loose_prefix():
    candidates = [
        {"name": "The Human League", "popularity": 64, "genres": ["synthpop"]},
        {"name": "Wang Chung", "popularity": 56, "genres": ["synthpop"]},
    ]
    candidate, reason = _pick_spotify_candidate(
        "The Human League Generations Tour 2026",
        candidates,
        allow_loose=True,
    )
    assert candidate["name"] == "The Human League"
    assert reason == "loose-prefix"


def test_pick_spotify_candidate_loose_contained():
    candidates = [
        {"name": "Thornhill", "popularity": 57, "genres": ["metalcore"]},
        {"name": "Carys Thornhill", "popularity": 6, "genres": []},
    ]
    candidate, reason = _pick_spotify_candidate(
        "REVOLVER PRESENTS: THORNHILL: The Mercia Tour",
        candidates,
        allow_loose=True,
    )
    assert candidate["name"] == "Thornhill"
    assert reason.startswith("loose-contained")


def test_pick_spotify_candidate_loose_reverse_contained():
    candidates = [
        {"name": "Metalocalypse: Dethklok", "popularity": 55, "genres": ["metal"]},
    ]
    candidate, reason = _pick_spotify_candidate("Dethklok", candidates, allow_loose=True)

    assert candidate["name"] == "Metalocalypse: Dethklok"
    assert reason == "loose-reverse-contained"


def test_pick_spotify_candidate_rejects_short_reverse_contained_name():
    candidates = [
        {"name": "Static Major", "popularity": 64, "genres": []},
    ]
    candidate, reason = _pick_spotify_candidate("major", candidates, allow_loose=True)

    assert candidate is None
    assert reason == "no-loose"


def test_spotify_search_names_adds_conservative_variants():
    assert spotify_search_names("REVOLVER PRESENTS: THORNHILL: The Mercia Tour") == [
        "REVOLVER PRESENTS: THORNHILL: The Mercia Tour",
        "THORNHILL: The Mercia Tour",
        "THORNHILL",
    ]
    assert "Le Youth" in spotify_search_names("Le Youth - who are you really? - Atlanta")
    assert "MitiS" in spotify_search_names("MitiS, zensei")
    assert "zensei" in spotify_search_names("MitiS, zensei")
    assert spotify_search_names("The Strike plus special guest")[0] == "The Strike"
    assert spotify_search_names("The Hypos (Greg from Reigning Sound & Scott from Dr. Dog)") == ["The Hypos"]
    assert "Romeo Santos" in spotify_search_names("RESCHEDULED: Romeo Santos & Prince Royce")


def test_normalize_artist_name_handles_accents_and_leading_support_text():
    assert normalize_artist_name("Andrés Cepeda: Nuestra Vida En Canciones") == (
        "andres cepeda nuestra vida en canciones"
    )
    assert normalize_artist_name("with support from Will Sheff (of Okkervil River)") == "will sheff"
    assert normalize_artist_name("The Strike plus special guest") == "the strike"
    assert normalize_artist_name("RESCHEDULED: Romeo Santos & Prince Royce") == "romeo santos prince royce"


def test_should_retry_negative_cache_versions():
    assert should_retry_negative_cache({"spotify_url": None, "source": "search-none:no-results"}) is True
    assert should_retry_negative_cache({"spotify_url": None, "source": "search-none-v2:no-results"}) is True
    assert should_retry_negative_cache({"spotify_url": None, "source": "tm-attraction"}) is True
    assert should_retry_negative_cache({"spotify_url": None, "source": ""}) is True
    assert should_retry_negative_cache(
        {"spotify_url": None, "source": f"search-none-{SPOTIFY_SEARCH_SOURCE_VERSION}:no-results"}
    ) is False
    assert should_retry_negative_cache({"spotify_url": "https://open.spotify.com/artist/ABC"}) is False


def test_enrichment_retries_old_negative_cache(monkeypatch):
    monkeypatch.setattr(config, "SPOTIFY_CLIENT_ID", "client")
    monkeypatch.setattr(config, "SPOTIFY_CLIENT_SECRET", "secret")
    monkeypatch.setattr(spotify_enrichment, "_spotify_cache_loaded", True)
    monkeypatch.setattr(
        spotify_enrichment,
        "_artist_spotify_cache",
        {"by_name": {"mac demarco": {"spotify_url": None, "source": "search-none:no-results"}}},
    )
    monkeypatch.setattr(
        spotify_enrichment,
        "spotify_search_artist",
        lambda *_args, **_kwargs: ("https://open.spotify.com/artist/3Sz7ZnJQBIHsXLUSo0OQtM", "id", "exact"),
    )

    events = [
        {
            "date": "2099-05-13",
            "artists": [{"name": "Mac DeMarco"}],
        }
    ]

    enrich_events_with_spotify(events, search_limit=10, log_func=lambda *_: None)

    assert events[0]["artists"][0]["spotify_url"] == "https://open.spotify.com/artist/3Sz7ZnJQBIHsXLUSo0OQtM"


def test_enrichment_skips_current_negative_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "SPOTIFY_CLIENT_ID", "client")
    monkeypatch.setattr(config, "SPOTIFY_CLIENT_SECRET", "secret")
    monkeypatch.setattr(spotify_enrichment, "_spotify_cache_loaded", True)
    monkeypatch.setattr(
        spotify_enrichment,
        "_artist_spotify_cache",
        {
            "by_name": {
                "missing artist": {
                    "spotify_url": None,
                    "source": f"search-none-{SPOTIFY_SEARCH_SOURCE_VERSION}:no-results",
                }
            }
        },
    )
    monkeypatch.setattr(
        spotify_enrichment,
        "spotify_search_artist",
        lambda *_args, **_kwargs: calls.append("searched") or (None, None, "no-results"),
    )

    events = [
        {
            "date": "2099-05-13",
            "artists": [{"name": "Missing Artist"}],
        }
    ]

    enrich_events_with_spotify(events, search_limit=10, log_func=lambda *_: None)

    assert calls == []
    assert "spotify_url" not in events[0]["artists"][0]


def test_spotify_search_artist_handles_request_timeout(monkeypatch):
    monkeypatch.setattr(spotify_enrichment, "get_spotify_token", lambda: "token")
    monkeypatch.setattr(
        spotify_enrichment.requests,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(requests.exceptions.ReadTimeout()),
    )

    assert spotify_search_artist("Mac DeMarco") == (None, None, "error-request")


def test_enrichment_does_not_cache_transient_search_errors(monkeypatch):
    monkeypatch.setattr(config, "SPOTIFY_CLIENT_ID", "client")
    monkeypatch.setattr(config, "SPOTIFY_CLIENT_SECRET", "secret")
    monkeypatch.setattr(spotify_enrichment, "_spotify_cache_loaded", True)
    monkeypatch.setattr(spotify_enrichment, "_artist_spotify_cache", {"by_name": {}})
    monkeypatch.setattr(
        spotify_enrichment,
        "spotify_search_artist",
        lambda *_args, **_kwargs: (None, None, "error-request"),
    )

    events = [
        {
            "date": "2099-05-13",
            "artists": [{"name": "Mac DeMarco"}],
        }
    ]

    enrich_events_with_spotify(events, search_limit=10, log_func=lambda *_: None)

    assert spotify_enrichment._artist_spotify_cache == {"by_name": {}}

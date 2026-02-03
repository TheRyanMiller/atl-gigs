from scraper.spotify_enrichment import _pick_spotify_candidate


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

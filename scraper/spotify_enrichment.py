#!/usr/bin/env python3
"""
Spotify artist link enrichment utilities and standalone runner.
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scraper import config
from scraper.pipeline.r2 import download_from_r2

try:
    from tqdm import tqdm  # type: ignore
except ImportError:
    tqdm = None

# Cache for Spotify artist links (persisted to disk and R2)
_artist_spotify_cache = {"by_name": {}}
_spotify_cache_loaded = False
_spotify_token = None
_spotify_token_expires_at = 0


def load_spotify_cache():
    """Load Spotify link cache (download from R2 first if available)."""
    global _artist_spotify_cache, _spotify_cache_loaded
    download_from_r2("artist-spotify-cache.json", config.SPOTIFY_CACHE_PATH)

    try:
        if config.SPOTIFY_CACHE_PATH.exists():
            with open(config.SPOTIFY_CACHE_PATH, "r") as f:
                data = json.load(f)
                if isinstance(data, dict) and "by_name" in data:
                    _artist_spotify_cache = data
                else:
                    _artist_spotify_cache = {"by_name": {}}
                print(f"  Loaded {len(_artist_spotify_cache.get('by_name', {}))} cached Spotify links")
    except Exception as e:
        print(f"  Warning: Could not load Spotify cache: {e}")
        _artist_spotify_cache = {"by_name": {}}

    _spotify_cache_loaded = True


def save_spotify_cache():
    """Save Spotify link cache to disk."""
    try:
        config.SPOTIFY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(config.SPOTIFY_CACHE_PATH, "w") as f:
            json.dump(_artist_spotify_cache, f, indent=2)
    except Exception as e:
        print(f"  Warning: Could not save Spotify cache: {e}")


def normalize_artist_name(name):
    """Normalize artist names for cache keys and matching."""
    if not name:
        return ""
    normalized = name.lower().strip()
    normalized = re.sub(r"\([^)]*\)", " ", normalized)
    normalized = re.sub(r"(.+?)\s+\b(feat|ft|featuring|with)\b.*", r"\1", normalized)
    normalized = normalized.replace("&", " ").replace("+", " ")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def is_non_artist_name(normalized_name):
    """Return True for placeholder names that should be skipped."""
    if not normalized_name:
        return True
    return normalized_name in {
        "tba",
        "tbd",
        "unknown",
        "surprise guest",
        "surprise guests",
        "special guest",
        "guests",
    }


def extract_spotify_artist_id(url):
    """Extract Spotify artist ID from a URL or spotify: URI."""
    if not url:
        return None
    if url.startswith("spotify:artist:"):
        return url.split(":")[-1]
    match = re.search(r"open\.spotify\.com/artist/([A-Za-z0-9]+)", url)
    return match.group(1) if match else None


def normalize_spotify_url(url):
    """Normalize Spotify artist URL to canonical format."""
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("spotify:artist:"):
        artist_id = extract_spotify_artist_id(url)
        return f"https://open.spotify.com/artist/{artist_id}" if artist_id else None
    artist_id = extract_spotify_artist_id(url)
    return f"https://open.spotify.com/artist/{artist_id}" if artist_id else None


def ensure_spotify_cache_loaded():
    """Lazy-load Spotify cache."""
    if not _spotify_cache_loaded:
        load_spotify_cache()


def get_spotify_cache_entry(normalized_name):
    """Return cached Spotify entry for normalized name, if any."""
    ensure_spotify_cache_loaded()
    return _artist_spotify_cache.get("by_name", {}).get(normalized_name)


def cache_spotify_result(artist_name, spotify_url, source, updated_at=None):
    """Store Spotify lookup result (positive or negative) in cache."""
    ensure_spotify_cache_loaded()
    normalized_name = normalize_artist_name(artist_name)
    if is_non_artist_name(normalized_name):
        return
    updated_at = updated_at or datetime.utcnow().isoformat() + "Z"
    normalized_url = normalize_spotify_url(spotify_url) if spotify_url else None
    artist_id = extract_spotify_artist_id(normalized_url) if normalized_url else None
    _artist_spotify_cache.setdefault("by_name", {})[normalized_name] = {
        "spotify_url": normalized_url,
        "spotify_id": artist_id,
        "source": source,
        "updated_at": updated_at,
    }


def extract_spotify_links_from_html(html):
    """Extract Spotify artist links from HTML and return list of {url, text}."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href") or ""
        if "open.spotify.com/artist" not in href and "spotify:artist:" not in href:
            continue
        url = normalize_spotify_url(href)
        if not url:
            continue
        text = anchor.get_text(" ", strip=True) or anchor.get("aria-label") or ""
        links.append({"url": url, "text": text})

    unique = {}
    for link in links:
        unique.setdefault(link["url"], link)
    return list(unique.values())


def get_spotify_token():
    """Get (and cache) a Spotify access token using Client Credentials flow."""
    global _spotify_token, _spotify_token_expires_at
    if not config.SPOTIFY_CLIENT_ID or not config.SPOTIFY_CLIENT_SECRET:
        return None

    now = time.time()
    if _spotify_token and now < (_spotify_token_expires_at - 60):
        return _spotify_token

    try:
        resp = requests.post(
            config.SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(config.SPOTIFY_CLIENT_ID, config.SPOTIFY_CLIENT_SECRET),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _spotify_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        _spotify_token_expires_at = now + int(expires_in)
        return _spotify_token
    except Exception as e:
        print(f"  Warning: Spotify token request failed: {e}")
        return None


def _genres_overlap(genre_hint, candidate_genres):
    if not genre_hint or not candidate_genres:
        return False
    hint_tokens = set(re.split(r"[\s/,-]+", genre_hint.lower()))
    for genre in candidate_genres:
        genre_tokens = set(re.split(r"[\s/,-]+", genre.lower()))
        if hint_tokens & genre_tokens:
            return True
    return False


def _pick_spotify_candidate(artist_name, candidates, genre_hint=None):
    target = normalize_artist_name(artist_name)
    exact = [c for c in candidates if normalize_artist_name(c.get("name", "")) == target]
    if not exact:
        return None, "no-exact"
    if len(exact) == 1:
        return exact[0], "exact"

    if genre_hint:
        genre_matches = [c for c in exact if _genres_overlap(genre_hint, c.get("genres", []))]
        if len(genre_matches) == 1:
            return genre_matches[0], "genre"
        if len(genre_matches) > 1:
            exact = genre_matches

    sorted_exact = sorted(exact, key=lambda c: c.get("popularity", 0), reverse=True)
    if len(sorted_exact) >= 2:
        lead = (sorted_exact[0].get("popularity", 0) - sorted_exact[1].get("popularity", 0))
        if lead >= 20:
            return sorted_exact[0], "popularity"

    return None, "ambiguous"


def spotify_search_artist(artist_name, genre_hint=None):
    """Search Spotify for an artist and return (url, id, reason) or (None, None, reason)."""
    global _spotify_token
    token = get_spotify_token()
    if not token:
        return None, None, "no-token"

    params = {
        "type": "artist",
        "market": "US",
        "limit": 5,
        "q": f'artist:"{artist_name}"',
    }

    headers = {"Authorization": f"Bearer {token}"}

    for attempt in range(2):
        resp = requests.get(config.SPOTIFY_SEARCH_URL, headers=headers, params=params, timeout=10)
        if resp.status_code == 401 and attempt == 0:
            _spotify_token = None
            token = get_spotify_token()
            if not token:
                break
            headers["Authorization"] = f"Bearer {token}"
            continue
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            time.sleep(retry_after)
            continue
        try:
            resp.raise_for_status()
        except Exception:
            return None, None, f"error-{resp.status_code}"
        break

    if resp.status_code != 200:
        return None, None, f"error-{resp.status_code}"

    data = resp.json()
    candidates = data.get("artists", {}).get("items", [])
    if not candidates:
        return None, None, "no-results"

    candidate, reason = _pick_spotify_candidate(artist_name, candidates, genre_hint=genre_hint)
    if not candidate:
        return None, None, reason

    url = candidate.get("external_urls", {}).get("spotify")
    normalized_url = normalize_spotify_url(url)
    return normalized_url, candidate.get("id"), reason


def _parse_event_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None


def _collect_search_candidates(events):
    for event in events:
        for artist in event.get("artists", []) or []:
            if not artist.get("spotify_url"):
                yield event, artist


def enrich_events_with_spotify(events, run_timestamp=None, log_func=None, search_limit=None):
    """
    Enrich events with Spotify artist URLs using:
      1) Cached links
      2) Explicit links on info_url pages
      3) Spotify Search API (aggressive fallback)
    """
    log = log_func or print
    if not events:
        return events

    run_timestamp = run_timestamp or datetime.utcnow().isoformat() + "Z"
    ensure_spotify_cache_loaded()

    counts = {
        "cache_hit": 0,
        "cache_miss": 0,
        "cache_negative": 0,
        "html": 0,
        "search": 0,
        "search_miss": 0,
        "search_skipped_negative": 0,
        "search_skipped_limit": 0,
        "skipped_non_artist": 0,
        "skipped_ambiguous": 0,
        "skipped_past_event": 0,
    }

    for event in events:
        for artist in event.get("artists", []) or []:
            if artist.get("spotify_url"):
                cache_spotify_result(artist.get("name", ""), artist["spotify_url"], source="event", updated_at=run_timestamp)

    today = datetime.utcnow().date()
    future_events = []
    for event in events:
        date_str = event.get("date")
        event_date = _parse_event_date(date_str) if date_str else None
        if event_date and event_date >= today:
            future_events.append(event)
        else:
            counts["skipped_past_event"] += 1

    info_url_cache = {}

    for event in future_events:
        artists = event.get("artists") or []
        if not artists:
            continue

        for artist in artists:
            if artist.get("spotify_url"):
                continue
            name = artist.get("name", "")
            normalized = normalize_artist_name(name)
            if is_non_artist_name(normalized):
                counts["skipped_non_artist"] += 1
                continue
            entry = get_spotify_cache_entry(normalized)
            if entry:
                if entry.get("spotify_url"):
                    artist["spotify_url"] = entry["spotify_url"]
                    counts["cache_hit"] += 1
                else:
                    counts["cache_negative"] += 1
            else:
                counts["cache_miss"] += 1

        info_url = event.get("info_url")
        if info_url and any(not a.get("spotify_url") for a in artists):
            links = info_url_cache.get(info_url)
            if links is None:
                try:
                    resp = requests.get(info_url, headers=config.SPOTIFY_HTML_HEADERS, timeout=20)
                    if resp.ok:
                        links = extract_spotify_links_from_html(resp.text)
                    else:
                        links = []
                except Exception:
                    links = []
                info_url_cache[info_url] = links
                time.sleep(config.SPOTIFY_HTML_DELAY)

            if links:
                if len(links) == 1:
                    headliner = artists[0]
                    if headliner and not headliner.get("spotify_url"):
                        headliner["spotify_url"] = links[0]["url"]
                        cache_spotify_result(headliner.get("name", ""), links[0]["url"], source="html", updated_at=run_timestamp)
                        counts["html"] += 1
                else:
                    for artist in artists:
                        if artist.get("spotify_url"):
                            continue
                        artist_norm = normalize_artist_name(artist.get("name", ""))
                        if is_non_artist_name(artist_norm):
                            continue
                        for link in links:
                            link_text = normalize_artist_name(link.get("text", ""))
                            if link_text and link_text == artist_norm:
                                artist["spotify_url"] = link["url"]
                                cache_spotify_result(artist.get("name", ""), link["url"], source="html", updated_at=run_timestamp)
                                counts["html"] += 1
                                break

    if config.SPOTIFY_CLIENT_ID and config.SPOTIFY_CLIENT_SECRET:
        search_limit = config.SPOTIFY_SEARCH_LIMIT if search_limit is None else max(int(search_limit), 0)
        search_attempts = 0
        for event, artist in _collect_search_candidates(future_events):
            if artist.get("spotify_url"):
                continue
            name = artist.get("name", "")
            normalized = normalize_artist_name(name)
            if is_non_artist_name(normalized):
                counts["skipped_non_artist"] += 1
                continue
            entry = get_spotify_cache_entry(normalized)
            if entry:
                if entry.get("spotify_url"):
                    artist["spotify_url"] = entry["spotify_url"]
                    counts["cache_hit"] += 1
                else:
                    counts["search_skipped_negative"] += 1
                continue

            if search_attempts >= search_limit:
                counts["search_skipped_limit"] += 1
                break

            url, _, reason = spotify_search_artist(name, genre_hint=artist.get("genre"))
            search_attempts += 1
            if url:
                artist["spotify_url"] = url
                cache_spotify_result(name, url, source=f"search:{reason}", updated_at=run_timestamp)
                counts["search"] += 1
            else:
                cache_spotify_result(name, None, source=f"search-none:{reason}", updated_at=run_timestamp)
                if reason == "ambiguous":
                    counts["skipped_ambiguous"] += 1
                counts["search_miss"] += 1

        if search_attempts >= search_limit:
            log(f"  Spotify Search capped at {search_limit} artists per run")
    else:
        log("  Spotify Search skipped: missing SPOTIFY_CLIENT_ID/SECRET")

    log(
        f"  Spotify links: html={counts['html']} search={counts['search']} "
        f"cache_hit={counts['cache_hit']} cache_negative={counts['cache_negative']} "
        f"search_miss={counts['search_miss']} skipped_ambiguous={counts['skipped_ambiguous']} "
        f"skipped_past_events={counts['skipped_past_event']} search_skipped_limit={counts['search_skipped_limit']}"
    )

    return events


def run_spotify_enrichment(events_path=config.OUTPUT_PATH, search_limit=None, log_func=None):
    log = log_func or print
    if not Path(events_path).exists():
        log(f"Events file not found: {events_path}")
        return False

    with open(events_path, "r") as f:
        events = json.load(f)

    run_timestamp = datetime.utcnow().isoformat() + "Z"
    events = enrich_events_with_spotify(events, run_timestamp=run_timestamp, log_func=log, search_limit=search_limit)
    save_spotify_cache()

    with open(events_path, "w") as f:
        json.dump(events, f, indent=2)

    log(f"Spotify enrichment complete. Updated {len(events)} events.")
    return True


def main():
    run_spotify_enrichment()


if __name__ == "__main__":
    main()

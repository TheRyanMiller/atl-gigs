# Spotify Links (Aggressive Strategy + Implementation Plan)

## Goal

Add `spotify_url` to artists with a tiered strategy that favors high-confidence sources,
then aggressively fills gaps via Spotify Search, while minimizing bad matches through
strict normalization, caching, and clear fallback rules.

## Sources (priority order)

1. **Ticketmaster Attractions `externalLinks.spotify`** (authoritative when present)  
2. **Explicit Spotify links on venue event pages (`info_url`)**  
3. **Spotify Search API** (aggressive fallback)

## Implementation plan (ready to execute)

1. **Schema + UI**
   - Add `spotify_url?: string` to `Artist` in `atl-gigs/src/types.ts`.
   - Render a Spotify button/link in `EventModal` when `spotify_url` exists.

2. **Env + config**
   - Add `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` to `.env.example`.
   - Read env vars in `scrape.py` (keep optional; if missing, skip Search).

3. **Spotify cache (persisted to R2)**
   - New file: `atl-gigs/public/events/artist-spotify-cache.json`.
   - Cache structure (simple, implementation-ready):
     ```json
     {
       "by_name": {
         "normalized artist name": {
           "spotify_url": "https://open.spotify.com/artist/...",
           "spotify_id": "id",
           "source": "tm|html|search",
           "updated_at": "2026-02-03T12:34:56Z"
         }
       }
     }
     ```
   - Store negative results as:
     ```json
     {"spotify_url": null, "spotify_id": null, "source": "search-none", "updated_at": "..."}
     ```
   - Add download + upload of `artist-spotify-cache.json` in `download_from_r2()`/`upload_to_r2()`.
   - **Cache behavior (required)**:
     - **Never searched yet**: no cache entry → allowed to attempt lookup.
     - **Searched with no results**: cache entry with `spotify_url: null` → **skip** future searches.
     - **Searched with result**: cache entry with `spotify_url` set → use it, no new search.
     - Optional: re-try negative entries only if `updated_at` is older than a fixed TTL (e.g., 30 days).

4. **Normalization utilities**
   - Add `normalize_artist_name(name: str) -> str`:
     - Lowercase; trim whitespace.
     - Strip punctuation and common suffixes: `feat.`, `ft.`, `with`, `&`, `+`.
     - Collapse whitespace.
   - Skip lookup for obvious non-artists: `tba`, `tbd`, `unknown`, `surprise guest`.

5. **Ticketmaster enrichment (best source)**
   - In `scrape_tm_venue()`:
     - For each attraction, if `externalLinks.spotify` exists, set `artist["spotify_url"]`.
     - Handle both string and list forms defensively (use first URL).
   - When calling Attractions API (in `get_artist_classification()` or a new helper),
     store spotify link in cache when present.

6. **Event page extraction (explicit links)**
   - Implement `extract_spotify_links_from_html(html)`:
     - Parse HTML and collect `open.spotify.com/artist/...` links.
     - De-duplicate by artist ID.
   - For each event missing `spotify_url`:
     - Fetch `info_url` (if present).
     - If **exactly one** artist link is found, assign it to the headliner (`artists[0]`).
     - If multiple links:
       - Only assign when the link’s anchor text (or nearby text) normalizes to the artist name.
       - Otherwise skip.
   - Rate-limit requests (e.g., 250–500ms delay between pages).

7. **Spotify Search API (aggressive fallback)**
   - Token: Client Credentials flow; cache token + expiry in memory.
   - Search: `GET /v1/search` with:
     - `type=artist`, `market=US`, `limit=5`
     - `q=artist:"<name>"`
   - Matching rules:
     - Prefer exact normalized name match.
     - If multiple exact matches:
       - Use genre overlap when available.
       - Otherwise require a **popularity lead ≥ 20** over the next candidate to accept.
     - If no exact match, skip.
   - Cache result (positive or negative).
   - Respect rate limits (429 → sleep `Retry-After` + retry once).

8. **Pipeline placement (critical)**
   - Run Spotify enrichment **after `merge_events()`** and before writing `events.json`.
   - Only fill missing `spotify_url` (never overwrite existing).

9. **Validation + logging**
   - Log counts by source: `tm`, `html`, `search`, `cache-hit`, `cache-miss`, `skipped-ambiguous`.
   - Spot-check a few popular artists to confirm correct links.

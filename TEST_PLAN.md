# Test Plan

## Goals
- Ensure scraper correctness, schema compliance, and stable enrichment (TM + Spotify).
- Prevent regressions in event merging, cache behavior, and stale event handling.
- Validate frontend rendering, filtering, and user flows across devices.
- Provide a **repeatable, offline-capable** test suite for CI.

## Test Pyramid (recommended)
1. **Unit tests** (fast, offline, deterministic)
2. **Integration tests** (pipeline + IO with mocks)
3. **End-to-end tests** (Playwright against a local dev server)
4. **Optional live smoke tests** (real APIs, gated by env vars)

## Tooling
- **Python**: `pytest`, `pytest-mock`, `responses` (HTTP mocking), `freezegun` (time), `moto` (S3/R2 mocking), `beautifulsoup4` fixtures.
- **Frontend**: `vitest`, `@testing-library/react`, `@testing-library/user-event`.
- **E2E**: **Playwright** (required).

## Test Data Strategy
- **Static fixtures**: frozen HTML/JSON snapshots under `tests/fixtures/` for each scraper.
- **Golden outputs**: `tests/golden/events.json` for known stable sets.
- **Stub API responses**: Ticketmaster/Spotify JSON fixtures for deterministic enrichment.
- **Time control**: freeze time in tests that rely on `last_seen`, `first_seen`, or date filtering.

---

## Backend Test Plan (Python)

### 1) Unit Tests (pure functions)
**File(s)**: `scrape.py`, `spotify_enrichment.py`
- `normalize_time()` (AM/PM, seconds, invalid inputs)
- `normalize_price()` / `is_zero_price()` (free/zero handling)
- `generate_slug()` (stability, special chars, stage)
- `validate_event()` (required fields, artists list)
- `detect_category_from_text()` / `detect_category_from_ticket_url()` (keyword paths)
- `map_tm_classification()` (segment/genre precedence)
- Spotify helpers:
  - `normalize_artist_name()`
  - `normalize_spotify_url()` / `extract_spotify_artist_id()`
  - `_pick_spotify_candidate()` (exact match, genre overlap, popularity tie)
  - cache behavior: **negative cache entries prevent re-search**

### 2) Scraper Unit Tests (HTML/JSON parsing)
**Approach**: feed saved fixtures into parser functions, assert structured output
- Earl: HTML pages and pagination
- AEG venues: JSON API or HTML fixtures
- Live Nation venues: GraphQL fixture
- Fox Theatre: AJAX payload + date range parsing
- State Farm Arena / Mercedes-Benz / Masquerade / Center Stage

**Assertions**:
- Schema integrity
- Date format `YYYY-MM-DD`
- `doors_time` / `show_time` format
- `ticket_url` present
- Category mapping

### 3) Integration Tests (pipeline behavior)
**Key flows**:
- `merge_events()` preserves `first_seen`, `is_new`, and retains past events.
- `update_first_seen()` increments correctly with cache.
- `last_seen` updated only for scraped events.
- Spotify enrichment **runs after merge** and does not overwrite existing `spotify_url`.
- Search limit honored (`SPOTIFY_SEARCH_LIMIT`).

**I/O mocking**:
- `responses` for TM/Spotify HTTP calls.
- `moto` S3 for R2 (`download_from_r2`, `upload_to_r2`).

### 4) Snapshot / Golden File Tests
- Generate a known output from fixtures and compare to `tests/golden/events.json`.
- Assert stable ordering (sorted by date).

### 5) Error/Retry Behavior
- Simulate request timeouts and verify retry handling (Earl, Fox, etc.).
- Ensure scraper continues on per-venue failure and marks status correctly.

---

## Frontend Test Plan (React)

### 1) Component Unit Tests (Vitest + RTL)
- `EventCard`:
  - Renders date/venue/price
  - Spotify icon appears only when `spotify_url` exists
  - Multi-line headline keeps icon inline
- `EventModal`:
  - Spotify icon placement for headliner + support
  - Ticket link and info link presence
- `FilterBar`:
  - Category/venue toggles
  - Date range changes
- `Favorites`:
  - Add/remove, persists in localStorage

### 2) Hooks/Logic
- Date filtering in `Home` (time-zone correctness)
- Stale event hiding logic

---

## End-to-End (Playwright) — Required

### Setup
- Add Playwright config targeting local dev server.
- Use deterministic `events.json` via a local mock file server or stub.

### Core E2E Scenarios
1. **Load home** → events list renders, count matches fixture.
2. **Open modal** → correct event details, Spotify icon shown if present.
3. **Filters** → category/venue/date filters reduce list correctly.
4. **Search** → query finds artist/venue.
5. **Favorites flow** → add, navigate to favorites, persists refresh.
6. **Share button** → clipboard write mock.
7. **Responsive** → mobile layout snapshot check.

### Visual Regression (optional)
- Snapshot key pages: home list, modal open, favorites.

---

## CI Recommendations

### Always-on tests (offline/deterministic)
- Python unit + integration tests (mocked HTTP/S3)
- Frontend unit tests (Vitest)
- Playwright E2E against local fixtures

### Optional live smoke tests (gated)
- `TM_API_KEY` / `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` set
- Run a small subset of real calls (1–2 venues max)

---

## Proposed Test Commands

### Backend
- `pytest -q`
- `pytest -q tests/integration/test_pipeline.py`

### Frontend
- `cd atl-gigs && npm run test` (Vitest)

### E2E
- `cd atl-gigs && npx playwright test`

---

## File/Folder Layout (suggested)
```
/tests
  /unit
  /integration
  /fixtures
  /golden
atl-gigs/
  /tests
  /e2e
```

## Test Organization & Naming
- **Unit vs integration**: keep pure function tests in `/tests/unit` and any IO/mocking in `/tests/integration`.
- **Per-module files**: `tests/unit/test_<module>.py` and `tests/integration/test_<feature>.py`.
- **Fixture naming**: `venue_<name>_page.html`, `tm_events_<venue>.json`, `spotify_search_<artist>.json`.
- **Golden files**: store in `/tests/golden/` with versioned filenames (e.g., `events_v1.json`).
- **Frontend**: colocate React tests under `atl-gigs/tests` mirroring component structure.
- **E2E**: place Playwright specs in `atl-gigs/e2e/` and use `*.spec.ts`.

---

## Coverage Targets (suggested)
- Backend: 80%+ on utility + pipeline modules
- Frontend: 70%+ on components + filters
- Playwright: 6–10 happy-path + regression flows

---

## Risk Areas to Prioritize
- Category mapping + TM enrichment correctness
- `merge_events` + `last_seen` and stale filtering logic
- Spotify cache (negative results, search limit)
- Multi-line title + inline icon placement
- R2 upload/download consistency

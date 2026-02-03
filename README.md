# ATL Gigs

Atlanta event aggregator for concerts, comedy, broadway, and more.

**Live site**: [atl-gigs.info](https://atl-gigs.info)

## Quick Start

```bash
# Scraper
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your TM_API_KEY
python3 scrape.py

# Frontend
cd atl-gigs && npm install && npm run dev
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TM_API_KEY` | Optional | Ticketmaster Discovery API key for better categorization. Get free key at [developer.ticketmaster.com](https://developer.ticketmaster.com) |
| `USE_TM_API` | Optional | Set to `false` to disable TM API and use HTML scrapers (default: `true`) |
| `SPOTIFY_CLIENT_ID` | Optional | Spotify API client id for artist link enrichment |
| `SPOTIFY_CLIENT_SECRET` | Optional | Spotify API client secret for artist link enrichment |
| `SPOTIFY_SEARCH_LIMIT` | Optional | Max Spotify artist searches per run (default: `50`) |

## Architecture

```
scrape.py → events.json → React Frontend → Vercel
```

- **Scraper**: Python script fetches from 11 venues (Ticketmaster API + HTML/JSON scraping)
- **Spotify enrichment**: Adds artist Spotify URLs during scrape (future events only); can be run standalone via `spotify_enrichment.py`
- **Frontend**: React + Vite + Tailwind, client-side filtering
- **Deployment**: GitHub Actions runs daily, deploys to Vercel
- **Share links**: `/e/{slug}` routes serve dynamic OG tags for social previews

## Project Structure

```
atl-music/
├── scrape.py                     # Main scraper entrypoint
├── spotify_enrichment.py         # Standalone Spotify enrichment runner
├── requirements.txt              # Python deps (requests, beautifulsoup4)
├── AGENTS.md                     # Instructions for adding new scrapers
├── scrapers/                     # Venue scraper documentation
├── .github/workflows/scrape.yml  # Daily automation + Vercel deploy
└── atl-gigs/                     # React frontend
    ├── api/og.ts                 # Vercel serverless for OG tags
    ├── public/events/            # Generated JSON (gitignored)
    │   ├── events.json           # All events (merged with history)
    │   ├── scrape-status.json    # Scraper health status
    │   ├── seen-cache.json       # first_seen tracking
    │   ├── artist-cache.json     # TM artist classification cache
    │   └── artist-spotify-cache.json # Spotify artist cache
    └── src/
        ├── components/           # EventCard, EventModal, FilterBar
        ├── pages/                # Home
        └── types.ts              # TypeScript interfaces
```

## Event Schema

```typescript
interface Event {
  slug: string;                    // URL-safe identifier
  venue: string;
  date: string;                    // "YYYY-MM-DD"
  doors_time: string | null;       // "HH:MM" 24-hour
  show_time: string | null;
  artists: { name: string; genre?: string }[];
  price?: string;
  ticket_url: string;
  info_url?: string;
  image_url?: string;
  category: "concerts" | "comedy" | "broadway" | "sports" | "misc";
  room?: string;                 // For multi-room venues (e.g., Masquerade)
}
```

## Current Venues

| Venue | Method | Categories |
|-------|--------|------------|
| The Earl | HTML scraping | concerts |
| Tabernacle | Live Nation GraphQL | concerts, comedy |
| Coca-Cola Roxy | Live Nation GraphQL | concerts, comedy |
| Terminal West | AEG JSON API | concerts |
| The Eastern | AEG JSON API | concerts |
| Variety Playhouse | AEG JSON API | concerts |
| Fox Theatre | HTML scraping | broadway, comedy, concerts |
| State Farm Arena | Ticketmaster API | concerts, comedy, sports |
| Mercedes-Benz Stadium | HTML scraping | concerts, sports |
| The Masquerade | Ticketmaster API | concerts |
| Center Stage / The Loft / Vinyl | Ticketmaster API | concerts, comedy |

## Automation

GitHub Actions runs daily at 6 AM UTC:
1. Scrapes all venues
2. Archives past events
3. Deploys to Vercel

Manual trigger: Actions → "Scrape Events" → "Run workflow"

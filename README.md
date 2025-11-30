# ATL Gigs

Atlanta event aggregator for concerts, comedy, broadway, and more.

**Live site**: [atl-gigs.info](https://atl-gigs.info)

## Quick Start

```bash
# Scraper
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python scrape.py

# Frontend
cd atl-gigs && npm install && npm run dev
```

## Architecture

```
scrape.py → events.json → React Frontend → Vercel
              ↓
         archive.json (past events)
```

- **Scraper**: Python script fetches from 5 venues (HTML + API scraping)
- **Frontend**: React + Vite + Tailwind, client-side filtering
- **Deployment**: GitHub Actions runs daily, deploys to Vercel
- **Share links**: `/e/{slug}` routes serve dynamic OG tags for social previews

## Project Structure

```
atl-music/
├── scrape.py                     # Main scraper
├── requirements.txt              # Python deps (requests, beautifulsoup4)
├── AGENTS.md                     # Instructions for adding new scrapers
├── .github/workflows/scrape.yml  # Daily automation + Vercel deploy
└── atl-gigs/                     # React frontend
    ├── api/og.ts                 # Vercel serverless for OG tags
    ├── public/events/            # Generated JSON (gitignored)
    │   ├── events.json           # Upcoming events
    │   ├── archive.json          # Past events
    │   └── scrape-status.json    # Scraper health status
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
  category: "concerts" | "comedy" | "broadway" | "misc";
}
```

## Current Venues

| Venue | Method | Category |
|-------|--------|----------|
| The Earl | HTML scraping | concerts |
| Tabernacle | Live Nation GraphQL | concerts |
| Coca-Cola Roxy | Live Nation GraphQL | concerts |
| Terminal West | AEG JSON API | concerts |
| The Eastern | AEG JSON API | concerts |

## Automation

GitHub Actions runs daily at 6 AM UTC:
1. Scrapes all venues
2. Archives past events
3. Deploys to Vercel

Manual trigger: Actions → "Scrape Events" → "Run workflow"

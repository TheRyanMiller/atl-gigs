# ATL Music - Atlanta Concert Aggregator

A lightweight web app that aggregates concert listings from Atlanta's top music venues into a single, searchable interface.

## Architecture

```
┌─────────────────┐      ┌──────────────┐      ┌─────────────────────┐
│  Venue APIs     │      │  scrape.py   │      │  events.json        │
│  (5 sources)    │─────▶│  (Python)    │─────▶│  (static JSON)      │
└─────────────────┘      └──────────────┘      └─────────────────────┘
                                                         │
                                               ┌─────────▼─────────┐
                                               │  React Frontend   │
                                               │  (Vite + Tailwind)│
                                               └───────────────────┘
```

### Data Flow

1. **Scraping** (`scrape.py`): Python script fetches events from 5 Atlanta venues:
   - The Earl (HTML scraping via BeautifulSoup)
   - Tabernacle (Live Nation GraphQL API)
   - Coca-Cola Roxy (Live Nation GraphQL API)
   - Terminal West (AEG JSON API)
   - The Eastern (AEG JSON API)

2. **Processing**: Events are normalized (time formats, price fields) and validated

3. **Storage**: Valid events saved to `atl-gigs/public/events.json`, sorted by date

4. **Frontend**: React app fetches `/events.json` on mount, displays filterable event cards

5. **Automation**: GitHub Actions runs scraper daily at 6 AM UTC, auto-commits changes

### Key Design Decisions

- **No backend server**: Static JSON + static React build = simple deployment
- **No database**: JSON file is sufficient for ~200-500 events
- **Client-side filtering**: All filtering/sorting happens in browser
- **Error resilience**: Individual venue failures don't break the entire scrape

## Project Structure

```
atl-music/
├── scrape.py                    # Main scraper (all venues)
├── requirements.txt             # Python dependencies
├── events.json                  # Backup of scraped data
├── sources.md                   # API endpoint documentation
├── .github/workflows/scrape.yml # Daily automation
├── atl-gigs/                    # React frontend
│   ├── public/events.json       # Event data served to frontend
│   ├── src/
│   │   ├── components/          # EventCard, EventModal, FilterBar, Navigation
│   │   ├── pages/               # Home, Status
│   │   └── types.ts             # TypeScript interfaces
│   └── package.json
└── AGENTS.md                    # AI coding agent instructions
```

## Setup & Commands

### Scraper (Python)

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run scraper
python scrape.py
```

### Frontend (React)

```bash
cd atl-gigs
npm install
npm run dev      # Start dev server (http://localhost:5173)
npm run build    # Production build
npm run lint     # Run ESLint
```

## Data Schema

```typescript
interface Event {
  venue: string;
  date: string;                // "YYYY-MM-DD"
  doors_time: string | null;   // "HH:MM" (24-hour format)
  show_time: string | null;    // "HH:MM" (24-hour format)
  artists: { name: string; genre?: string }[];
  price?: string;              // Normalized: "$20 ADV / $25 DOS" or "$25.00 - $45.00"
  ticket_url: string;
  info_url?: string;
  image_url?: string;
}
```

## Automation

The scraper runs automatically via GitHub Actions:
- **Schedule**: Daily at 6 AM UTC (1 AM EST)
- **Manual trigger**: Can be run on-demand via GitHub Actions UI
- **Auto-commit**: Changes to `events.json` are committed automatically
- **Uses venv**: Creates isolated Python environment with dependencies from `requirements.txt`

To trigger manually: Go to Actions > "Scrape Events" > "Run workflow"

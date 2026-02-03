import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[1]
EVENTS_DIR = REPO_ROOT / "atl-gigs" / "public" / "events"
OUTPUT_PATH = EVENTS_DIR / "events.json"
STATUS_PATH = EVENTS_DIR / "scrape-status.json"
LOG_PATH = EVENTS_DIR / "scrape-log.txt"
SEEN_CACHE_PATH = EVENTS_DIR / "seen-cache.json"
ARTIST_CACHE_PATH = EVENTS_DIR / "artist-cache.json"
SPOTIFY_CACHE_PATH = EVENTS_DIR / "artist-spotify-cache.json"

NEW_EVENT_DAYS = 5

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = "atl-gigs-data"
R2_PUBLIC_URL = "https://pub-756023fa49674586a44105ba7bf52137.r2.dev"

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"
SPOTIFY_SEARCH_LIMIT = int(os.environ.get("SPOTIFY_SEARCH_LIMIT", "50"))
SPOTIFY_HTML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}
SPOTIFY_HTML_DELAY = 0.35

CATEGORIES = ["concerts", "comedy", "broadway", "sports", "misc"]
DEFAULT_CATEGORY = "concerts"
REQUIRED_FIELDS = ["venue", "date", "artists", "ticket_url"]

USE_TM_API = os.environ.get("USE_TM_API", "true").lower() == "true"
TM_API_KEY = os.environ.get("TM_API_KEY")
TM_BASE_URL = "https://app.ticketmaster.com/discovery/v2"

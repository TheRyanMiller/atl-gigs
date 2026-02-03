import json
import re
from datetime import datetime, timedelta

from scraper import config
from scraper.pipeline.r2 import download_from_r2


def trim_log_by_time(log_path, retention_days=14):
    """
    Remove log entries older than retention_days.
    Returns list of lines to keep.
    """
    if not log_path.exists():
        return []

    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    kept_lines = []
    current_entry_recent = False

    with open(log_path, "r") as f:
        for line in f:
            match = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
            if match:
                current_entry_recent = match.group(1) >= cutoff_str

            if current_entry_recent:
                kept_lines.append(line)

    return kept_lines


def load_existing_events():
    """
    Load existing events from R2 (or local file).
    This preserves past events that we've already scraped.
    Returns list of events.
    """
    download_from_r2("events.json", config.OUTPUT_PATH)

    try:
        if config.OUTPUT_PATH.exists():
            with open(config.OUTPUT_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def load_seen_cache():
    """Load the seen events cache (download from R2 first if available)."""
    download_from_r2("seen-cache.json", config.SEEN_CACHE_PATH)

    try:
        if config.SEEN_CACHE_PATH.exists():
            with open(config.SEEN_CACHE_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"events": {}, "last_updated": None}


def save_seen_cache(cache):
    """Save seen events cache to disk."""
    config.SEEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.SEEN_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def load_existing_status():
    """Load existing scrape status file if available."""
    download_from_r2("scrape-status.json", config.STATUS_PATH)

    try:
        if config.STATUS_PATH.exists():
            with open(config.STATUS_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"venues": {}}

#!/usr/bin/env python3
"""
Scrape concert events from multiple venues and save to JSON.
"""

import json
import time
import traceback
from datetime import datetime

from scraper import config
from scraper import spotify_enrichment
from scraper.pipeline.io import (
    trim_log_by_time,
    load_existing_events,
    load_seen_cache,
    save_seen_cache,
    load_existing_status,
)
from scraper.pipeline.merge import merge_events, update_first_seen, prune_seen_cache
from scraper.pipeline.metrics import VenueMetrics
from scraper.pipeline.r2 import upload_to_r2
from scraper.pipeline.validate import validate_event
from scraper.registry import get_scrapers
from scraper.tm import load_artist_cache, save_artist_cache, enrich_events_with_tm
from scraper.utils.events import generate_slug, normalize_price


def main():
    all_events = []
    run_timestamp = datetime.utcnow().isoformat() + "Z"
    log_lines = []  # Collect log entries

    def log(message, level="INFO"):
        """Log a message to both console and log buffer."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(message)
        log_lines.append(log_entry)

    log(f"Starting scrape run at {run_timestamp}")

    # Load existing status to preserve last_success data
    existing_status = load_existing_status()
    venue_statuses = {}
    venue_metrics = {}  # Track metrics for summary table

    scrapers = get_scrapers()

    for venue_name, scraper in scrapers.items():
        log(f"Scraping {venue_name}...")
        metrics = VenueMetrics(name=venue_name)
        start_time = time.time()

        venue_status = {
            "last_run": run_timestamp,
            "success": False,
            "event_count": 0,
            "error": None,
        }

        # Preserve last successful scrape info from existing status
        existing_venue = existing_status.get("venues", {}).get(venue_name, {})
        if existing_venue.get("last_success"):
            venue_status["last_success"] = existing_venue["last_success"]
            venue_status["last_success_count"] = existing_venue.get("last_success_count", 0)

        try:
            events = scraper()
            event_count = len(events)
            metrics.event_count = event_count
            metrics.duration_ms = (time.time() - start_time) * 1000
            log(f"  Found {event_count} events")
            all_events.extend(events)

            venue_status["success"] = True
            venue_status["event_count"] = event_count
            venue_status["last_success"] = run_timestamp
            venue_status["last_success_count"] = event_count

        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            metrics.errors = 1
            metrics.error_messages.append(error_msg)
            metrics.duration_ms = (time.time() - start_time) * 1000
            log(f"  ERROR: Failed to scrape {venue_name}: {error_msg}", "ERROR")
            log(f"  Traceback:\n{error_trace}", "ERROR")

            venue_status["success"] = False
            venue_status["error"] = error_msg
            venue_status["error_trace"] = error_trace

        venue_statuses[venue_name] = venue_status
        venue_metrics[venue_name] = metrics

    # Enrich events with TM artist classifications (for non-TM venues)
    if config.TM_API_KEY:
        log("\nEnriching events with Ticketmaster artist data...")
        load_artist_cache()
        all_events = enrich_events_with_tm(all_events)
        save_artist_cache()

    # Normalize prices, generate slugs, and validate events
    log("\nProcessing events...")
    all_events = [normalize_price(e) for e in all_events]

    # Generate slugs for each event, ensuring uniqueness
    slug_counts = {}
    for event in all_events:
        base_slug = generate_slug(event)

        # Handle duplicate slugs by appending a counter
        if base_slug in slug_counts:
            slug_counts[base_slug] += 1
            event["slug"] = f"{base_slug}-{slug_counts[base_slug]}"
        else:
            slug_counts[base_slug] = 0
            event["slug"] = base_slug

    valid_events = [e for e in all_events if validate_event(e)]
    invalid_count = len(all_events) - len(valid_events)

    if invalid_count > 0:
        log(f"  Filtered out {invalid_count} invalid events", "WARNING")

    # Set last_seen timestamp on newly scraped events (before merge)
    # Old events from R2 will keep their old last_seen (enables stale event detection)
    for event in valid_events:
        event["last_seen"] = run_timestamp

    # Load existing events from R2 and merge with new events
    log("\nMerging with existing events from R2...")
    existing_events = load_existing_events()
    log(f"  Loaded {len(existing_events)} existing events from R2")
    merged_events = merge_events(existing_events, valid_events)
    log(f"  Merged total: {len(merged_events)} events")

    # Update first_seen field for tracking new events
    seen_cache = load_seen_cache()
    merged_events, new_event_count = update_first_seen(merged_events, seen_cache)
    log(f"  {new_event_count} newly discovered events")

    # Enrich events with Spotify links (after merge to preserve existing links)
    log("\nEnriching events with Spotify links...")
    merged_events = spotify_enrichment.enrich_events_with_spotify(
        merged_events,
        run_timestamp=run_timestamp,
        log_func=log,
    )
    spotify_enrichment.save_spotify_cache()

    # Sort by date
    merged_events.sort(key=lambda x: x["date"])

    # Use merged_events as our final list
    valid_events = merged_events

    # Determine overall status
    all_success = all(v["success"] for v in venue_statuses.values())
    any_success = any(v["success"] for v in venue_statuses.values())

    # Log summary table
    log("")
    log("=" * 60)
    log("VENUE SUMMARY")
    log("=" * 60)
    log(f"{'Venue':<24} {'Events':>7} {'Errors':>7} {'Time':>10}")
    log("-" * 60)
    for name in sorted(venue_metrics.keys()):
        m = venue_metrics[name]
        time_str = f"{m.duration_ms:.0f}ms"
        log(f"{name:<24} {m.event_count:>7} {m.errors:>7} {time_str:>10}")
    log("-" * 60)
    total_events = sum(m.event_count for m in venue_metrics.values())
    total_errors = sum(m.errors for m in venue_metrics.values())
    total_time = sum(m.duration_ms for m in venue_metrics.values())
    log(f"{'TOTAL':<24} {total_events:>7} {total_errors:>7} {total_time:.0f}ms")
    log("=" * 60)

    log(f"\nTotal valid events: {len(valid_events)}")

    failed_venues = [name for name, status in venue_statuses.items() if not status["success"]]
    if failed_venues:
        log(f"WARNING: Failed to scrape: {', '.join(failed_venues)}", "ERROR")

    # Ensure events directory exists
    config.EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save all events (past and future - no more archive separation)
    with open(config.OUTPUT_PATH, "w") as f:
        json.dump(valid_events, f, indent=2)
    log(f"Events saved to {config.OUTPUT_PATH}")

    # Prune and save seen cache
    current_slugs = {e.get("slug") for e in valid_events if e.get("slug")}
    seen_cache = prune_seen_cache(seen_cache, current_slugs)
    save_seen_cache(seen_cache)
    log(f"Seen cache saved ({len(seen_cache['events'])} events tracked)")

    # Save scrape status
    status_data = {
        "last_run": run_timestamp,
        "all_success": all_success,
        "any_success": any_success,
        "total_events": len(valid_events),
        "venues": venue_statuses,
    }

    with open(config.STATUS_PATH, "w") as f:
        json.dump(status_data, f, indent=2)
    log(f"Status saved to {config.STATUS_PATH}")

    # Upload to R2 (Cloudflare object storage)
    log("\nUploading to R2...")
    if upload_to_r2(log_func=log):
        log(f"Data available at: {config.R2_PUBLIC_URL}/events.json")
    else:
        log("R2 upload failed or skipped - files only saved locally", "WARNING")

    # Save log file (time-based retention: 14 days)
    existing_log = trim_log_by_time(config.LOG_PATH, retention_days=14)

    # Add separator and new log entries
    log_content = existing_log + ["\n--- New Run ---\n"] + [line + "\n" for line in log_lines]

    with open(config.LOG_PATH, "w") as f:
        f.writelines(log_content)
    log(f"Log saved to {config.LOG_PATH}")


if __name__ == "__main__":
    main()

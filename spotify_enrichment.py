#!/usr/bin/env python3
"""
Compatibility wrapper for scraper.spotify_enrichment.
"""

from scraper.spotify_enrichment import *  # noqa: F401,F403
from scraper.spotify_enrichment import main


if __name__ == "__main__":
    main()

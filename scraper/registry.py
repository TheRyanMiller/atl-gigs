from scraper import config
from scraper.tm import (
    scrape_center_stage_tm,
    scrape_masquerade_tm,
    scrape_state_farm_arena_tm,
)
from scraper.venues.aeg import scrape_terminal_west, scrape_the_eastern, scrape_variety_playhouse
from scraper.venues.center_stage import scrape_center_stage
from scraper.venues.earl import scrape_earl
from scraper.venues.fox import scrape_fox_theatre
from scraper.venues.live_nation import scrape_tabernacle, scrape_coca_cola_roxy
from scraper.venues.masquerade import scrape_masquerade
from scraper.venues.mercedes_benz_stadium import scrape_mercedes_benz_stadium
from scraper.venues.state_farm_arena import scrape_state_farm_arena


def get_scrapers():
    """Build scraper registry, using TM API when available."""
    scrapers = {
        "The Earl": scrape_earl,
        "Tabernacle": scrape_tabernacle,
        "Terminal West": scrape_terminal_west,
        "The Eastern": scrape_the_eastern,
        "Variety Playhouse": scrape_variety_playhouse,
        "Coca-Cola Roxy": scrape_coca_cola_roxy,
        "Fox Theatre": scrape_fox_theatre,
        "Mercedes-Benz Stadium": scrape_mercedes_benz_stadium,
    }

    # Use TM API for venues that use Ticketmaster, if API key is available
    if config.USE_TM_API and config.TM_API_KEY:
        scrapers["State Farm Arena"] = scrape_state_farm_arena_tm
        scrapers["The Masquerade"] = scrape_masquerade_tm
        scrapers["Center Stage"] = scrape_center_stage_tm
    else:
        scrapers["State Farm Arena"] = scrape_state_farm_arena
        scrapers["The Masquerade"] = scrape_masquerade
        scrapers["Center Stage"] = scrape_center_stage

    return scrapers

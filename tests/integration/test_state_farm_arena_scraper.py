import pytest

responses = pytest.importorskip("responses")

from scraper.venues.state_farm_arena import STATE_FARM_ARENA_BASE, STATE_FARM_ARENA_CATEGORIES, scrape_state_farm_arena


def _event_card(title, detail_path, ticket_url):
    return f"""
    <div class="eventItem">
      <div class="title"><a href="{detail_path}">{title}</a></div>
      <div class="date">
        <div class="m-date__singleDate">
          <span class="m-date__month">May</span>
          <span class="m-date__day">2</span>
          <span class="m-date__year">2026</span>
        </div>
      </div>
      <div class="meta"><div class="time">Event Starts 7:00 PM</div></div>
      <a class="more" href="{detail_path}">More Info</a>
      <a class="tickets" href="{ticket_url}">Tickets</a>
      <div class="thumb"><img src="/images/event.jpg" /></div>
    </div>
    """


def test_scrape_state_farm_arena_uses_detected_category_for_dedupe_priority():
    detail_path = "/events/detail/stand-up-comedy-night"
    ticket_url = "https://www.ticketmaster.com/stand-up-comedy-night/event/123"
    event_html = _event_card("Stand-up Comedy Night", detail_path, ticket_url)

    with responses.RequestsMock() as rsps:
        for path in STATE_FARM_ARENA_CATEGORIES:
            body = f"<html><body>{event_html if path in ['/events/category/concerts', '/events/category/other'] else ''}</body></html>"
            rsps.add(rsps.GET, STATE_FARM_ARENA_BASE + path, body=body, status=200)

        events = scrape_state_farm_arena()

    assert len(events) == 1
    assert events[0]["category"] == "comedy"
    assert events[0]["show_time"] == "19:00"
    assert events[0]["info_url"] == f"{STATE_FARM_ARENA_BASE}{detail_path}"
    assert events[0]["image_url"] == f"{STATE_FARM_ARENA_BASE}/images/event.jpg"

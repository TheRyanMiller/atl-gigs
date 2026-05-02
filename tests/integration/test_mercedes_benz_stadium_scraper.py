import pytest

responses = pytest.importorskip("responses")

from scraper.venues.mercedes_benz_stadium import MERCEDES_BENZ_STADIUM_BASE, scrape_mercedes_benz_stadium


def test_scrape_mercedes_benz_stadium_parses_event_cards_and_team_widgets():
    html = """
    <html>
      <body>
        <div class="events--item w-dyn-item">
          <h3>Summer Concert</h3>
          <div class="events_tags--item w-dyn-item">Concert</div>
          <div class="events_feature_details_dt">May 9, 2026</div>
          <div class="events_feature_details_dt">7:30 PM</div>
          <a class="btn--1" href="https://tickets.example.com/concert">Tickets</a>
          <a class="btn--3" href="/events/summer-concert">Details</a>
          <img class="event_image" src="/images/concert.jpg" />
        </div>

        <div class="events_game--item falcons">
          <img src="https://images.example.com/falcons/AU_Primary_ignore.png" />
          <img src="https://images.example.com/falcons/falcons.png" />
          <div>NEXT HOME GAME</div>
          <div>vs. Panthers</div>
          <div>May 10, 2026</div>
          <div>1:00 pm</div>
          <a href="https://ticketmaster.example.com/falcons">Tickets</a>
        </div>

        <div class="events_game--item united">
          <div>NEXT HOME GAME</div>
          <div>vs. Charlotte FC</div>
          <div>May 11, 2026</div>
          <div>7:00 pm</div>
        </div>
      </body>
    </html>
    """

    with responses.RequestsMock() as rsps:
        rsps.add(rsps.GET, f"{MERCEDES_BENZ_STADIUM_BASE}/events", body=html, status=200)
        events = scrape_mercedes_benz_stadium()

    assert len(events) == 2
    assert events[0] == {
        "venue": "Mercedes-Benz Stadium",
        "date": "2026-05-09",
        "doors_time": None,
        "show_time": "19:30",
        "artists": [{"name": "Summer Concert"}],
        "ticket_url": "https://tickets.example.com/concert",
        "info_url": f"{MERCEDES_BENZ_STADIUM_BASE}/events/summer-concert",
        "image_url": f"{MERCEDES_BENZ_STADIUM_BASE}/images/concert.jpg",
        "category": "concerts",
    }
    assert events[1]["artists"] == [{"name": "Atlanta Falcons vs. Panthers"}]
    assert events[1]["date"] == "2026-05-10"
    assert events[1]["show_time"] == "13:00"
    assert events[1]["category"] == "sports"

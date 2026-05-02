import pytest

responses = pytest.importorskip("responses")

from scraper.venues.masquerade import MASQUERADE_BASE, scrape_masquerade, split_masquerade_support_acts


def test_split_masquerade_support_acts_cleans_leading_delimiters():
    assert split_masquerade_support_acts("Sylosis, Great American Ghost, & Life Cycles") == [
        "Sylosis",
        "Great American Ghost",
        "Life Cycles",
    ]
    assert split_masquerade_support_acts("Opener One & Opener Two and Opener Three") == [
        "Opener One",
        "Opener Two",
        "Opener Three",
    ]


def test_scrape_masquerade_parses_fixture():
    html = """
    <html>
      <body>
        <article class="event">
          <span class="js-listVenue">The Masquerade - Heaven</span>
          <span class="eventStartDate" content="May 2, 2026 6:00 pm"></span>
          <span class="time-show">Doors 6:00 pm / All Ages</span>
          <h3 class="eventHeader__title">Bleed From Within</h3>
          <p class="eventHeader__support">Sylosis, Great American Ghost, & Life Cycles</p>
          <a class="btn-purple" href="https://tickets.example.com/bleed">Tickets</a>
          <a class="wrapperLink" href="/events/bleed-from-within/">Details</a>
          <div class="event--featuredImage" style="background-image: url('https://images.example.com/bleed.jpg')"></div>
        </article>
        <article class="event">
          <span class="js-listVenue">The Eastern</span>
          <span class="eventStartDate" content="May 3, 2026 6:00 pm"></span>
          <h3 class="eventHeader__title">External Event</h3>
        </article>
      </body>
    </html>
    """

    with responses.RequestsMock() as rsps:
        rsps.add(rsps.GET, f"{MASQUERADE_BASE}/events/", body=html, status=200)
        events = scrape_masquerade()

    assert len(events) == 1
    assert events[0]["date"] == "2026-05-02"
    assert events[0]["doors_time"] == "18:00"
    assert events[0]["stage"] == "Heaven"
    assert [artist["name"] for artist in events[0]["artists"]] == [
        "Bleed From Within",
        "Sylosis",
        "Great American Ghost",
        "Life Cycles",
    ]

from bs4 import BeautifulSoup

from scraper.utils.descriptions import clean_description, extract_first_description


def test_clean_description_strips_html_and_social_links():
    raw = """
    <div>
      <h2>Artist Name</h2>
      <p>A sharp, melodic band with a new album on the way.</p>
      <a href="/artist">Read More</a>
    </div>
    """

    assert clean_description(raw, heading="Artist Name") == "A sharp, melodic band with a new album on the way."


def test_clean_description_rejects_logistics_only_text():
    raw = (
        "All ages welcome. Doors: 7PM. Show at 8PM. "
        "The floor is general admission and balcony seating is reserved. "
        "Please review bag policy, ADA, parking, and Ticketmaster mobile tickets."
    )

    assert clean_description(raw) is None


def test_extract_first_description_supports_meta_content():
    soup = BeautifulSoup(
        '<meta name="description" content="See the artist at the Fox Theatre.">',
        "html.parser",
    )

    assert extract_first_description(soup, ['meta[name="description"]']) == "See the artist at the Fox Theatre."

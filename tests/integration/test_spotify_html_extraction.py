from scraper.spotify_enrichment import extract_spotify_links_from_html


def test_extract_spotify_links_from_html_dedupes():
    html = """
    <html><body>
      <a href="https://open.spotify.com/artist/ABC123">Artist One</a>
      <a href="https://open.spotify.com/artist/ABC123">Artist One Duplicate</a>
      <a href="spotify:artist:XYZ789">Artist Two</a>
    </body></html>
    """
    links = extract_spotify_links_from_html(html)
    urls = sorted([l["url"] for l in links])
    assert urls == [
        "https://open.spotify.com/artist/ABC123",
        "https://open.spotify.com/artist/XYZ789",
    ]

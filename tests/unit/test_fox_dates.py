from scraper.venues.fox import parse_fox_date_range


def test_parse_fox_date_range_single_date():
    assert parse_fox_date_range("May 2, 2026") == ("2026-05-02", "2026-05-02")


def test_parse_fox_date_range_same_month_range():
    assert parse_fox_date_range("May 2-3, 2026") == ("2026-05-02", "2026-05-03")


def test_parse_fox_date_range_spaced_comma_markup():
    assert parse_fox_date_range("May 2 - 3 , 2026") == ("2026-05-02", "2026-05-03")


def test_parse_fox_date_range_cross_month_range():
    assert parse_fox_date_range("Jan 27-Feb 1, 2026") == ("2026-01-27", "2026-02-01")

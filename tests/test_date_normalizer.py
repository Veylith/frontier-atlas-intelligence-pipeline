"""
Unit tests for precision date normalizer and 24-hour freshness verification.
"""

from datetime import datetime, timezone, timedelta
from src.crawlers.freshness.date_normalizer import DateNormalizer


def test_iso_date_parsing():
    iso_str = "2026-09-12T14:30:00Z"
    dt = DateNormalizer.parse_iso_or_rfc(iso_str)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 12


def test_rfc2822_date_parsing():
    rfc_str = "Sat, 12 Sep 2026 10:15:00 +0000"
    dt = DateNormalizer.parse_iso_or_rfc(rfc_str)
    assert dt is not None
    assert dt.hour == 10
    assert dt.minute == 15


def test_relative_dates():
    ref_time = datetime(2026, 9, 12, 18, 0, 0, tzinfo=timezone.utc)

    # 2 hours ago
    dt1 = DateNormalizer.parse_relative_date("2 hours ago", ref_time)
    assert dt1 is not None
    assert dt1 == datetime(2026, 9, 12, 16, 0, 0, tzinfo=timezone.utc)

    # 45 mins ago
    dt2 = DateNormalizer.parse_relative_date("45 mins ago", ref_time)
    assert dt2 is not None
    assert dt2 == datetime(2026, 9, 12, 17, 15, 0, tzinfo=timezone.utc)

    # yesterday
    dt3 = DateNormalizer.parse_relative_date("yesterday", ref_time)
    assert dt3 is not None
    assert dt3 == datetime(2026, 9, 11, 18, 0, 0, tzinfo=timezone.utc)


def test_html_microdata_extraction():
    sample_html = """
    <html>
        <head>
            <meta property="article:published_time" content="2026-09-12T08:00:00Z" />
        </head>
        <body>
            <article><h1>AI Breakthrough</h1></article>
        </body>
    </html>
    """
    dt = DateNormalizer.extract_from_html(sample_html)
    assert dt is not None
    assert dt.hour == 8


def test_24_hour_freshness_boundary():
    ref_time = datetime(2026, 9, 12, 18, 0, 0, tzinfo=timezone.utc)

    # 4 hours ago (Fresh)
    fresh_date = ref_time - timedelta(hours=4)
    is_fresh, iso_str, _ = DateNormalizer.normalize_and_validate_freshness(fresh_date, ref_time=ref_time)
    assert is_fresh is True

    # 23.5 hours ago (Fresh)
    almost_stale = ref_time - timedelta(hours=23, minutes=30)
    is_fresh, iso_str, _ = DateNormalizer.normalize_and_validate_freshness(almost_stale, ref_time=ref_time)
    assert is_fresh is True

    # 26 hours ago (Stale > 24h)
    stale_date = ref_time - timedelta(hours=26)
    is_fresh, iso_str, _ = DateNormalizer.normalize_and_validate_freshness(stale_date, ref_time=ref_time)
    assert is_fresh is False

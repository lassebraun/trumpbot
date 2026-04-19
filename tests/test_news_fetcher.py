import pytest
from news.fetcher import _parse_feed, format_headlines_for_llm, Headline
from datetime import datetime, timezone

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <item>
        <title>US Economy Grows</title>
        <description>The US economy showed strong growth in Q1.</description>
        <pubDate>Mon, 20 Jan 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
        <title>Market Update</title>
        <description>&lt;p&gt;Markets are mixed today.&lt;/p&gt;</description>
        <pubDate>Mon, 20 Jan 2026 11:00:00 +0000</pubDate>
    </item>
</channel>
</rss>
"""

def test_parse_feed():
    headlines = _parse_feed("Test Source", SAMPLE_RSS)
    
    assert len(headlines) == 2
    assert headlines[0].source == "Test Source"
    assert headlines[0].title == "US Economy Grows"
    assert headlines[0].summary == "The US economy showed strong growth in Q1."
    assert isinstance(headlines[0].published, datetime)
    
    assert headlines[1].title == "Market Update"
    assert headlines[1].summary == "Markets are mixed today."

def test_format_headlines_for_llm():
    headlines = [
        Headline(source="Source A", title="Title A", summary="Summary A", published=None),
        Headline(source="Source B", title="Title B", summary=None, published=None),
    ]
    
    formatted = format_headlines_for_llm(headlines)
    
    expected = "[Source A] Title A — Summary A\n[Source B] Title B"
    assert formatted == expected

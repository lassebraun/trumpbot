import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

FEEDS = [
    {
        "name": "New York Times",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml",
        "focus": "Us markets, macroeconomics",
    },
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/news/rssindex",
        "focus": "US markets, company news, geopolitical context",
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "focus": "market sentiment",
    },
    {
        "name": "CNBC",
        "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "focus": "US markets and company news",
    },
]


@dataclass
class Headline:
    source: str
    title: str
    summary: str | None
    published: datetime | None


def _parse_feed(name: str, xml_content: str) -> list[Headline]:
    headlines = []
    try:
        root = ET.fromstring(xml_content)
        # Handle both RSS and Atom namespaces
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        for item in items[:15]:  # cap per feed

            title_el = next((child for child in item if child.tag == "title"), None)
            desc_el = next((child for child in item if child.tag == "description"), None)
            pub_el = next((child for child in item if child.tag in ("pubDate", "published")), None)

            title = title_el.text.strip() if title_el is not None and title_el.text else None
            if not title:
                continue

            summary = desc_el.text.strip() if desc_el is not None and desc_el.text else None
            # Strip HTML tags from summary if present
            if summary and "<" in summary:
                import re
                summary = re.sub(r"<[^>]+>", "", summary).strip()
            summary = summary[:300] if summary else None  # truncate



            published = None
            if pub_el is not None and pub_el.text:
                for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"):
                    try:
                        published = datetime.strptime(pub_el.text.strip(), fmt)
                        break
                    except ValueError:
                        continue

            headlines.append(Headline(source=name, title=title, summary=summary, published=published))

    except ET.ParseError as e:
        logger.warning(f"Failed to parse feed '{name}': {e}")

    return headlines


async def fetch_all_headlines() -> list[Headline]:
    all_headlines: list[Headline] = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for feed in FEEDS:
            try:
                response = await client.get(
                    feed["url"],
                    headers={"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"},
                )
                response.raise_for_status()
                headlines = _parse_feed(feed["name"], response.text)
                logger.info(f"Fetched {len(headlines)} headlines from {feed['name']}")
                all_headlines.extend(headlines)
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching {feed['name']}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error fetching {feed['name']}: {e}")

    return all_headlines


def format_headlines_for_llm(headlines: list[Headline]) -> str:
    """Format headlines into a compact string for the summarizer prompt."""
    lines = []
    for h in headlines:
        line = f"[{h.source}] {h.title}"
        if h.summary:
            line += f" — {h.summary}"
        lines.append(line)
    return "\n".join(lines)
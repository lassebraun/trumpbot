import logging
from datetime import datetime, timezone

from anthropic import AsyncAnthropic
from typing import Type

from analysis.base import BaseLLMClient
from src.news.fetcher import Headline, fetch_all_headlines, format_headlines_for_llm
from src.database.models import NewsDigest

logger = logging.getLogger(__name__)

SUMMARIZER_PROMPT = """You are a terse financial news briefing assistant.

Summarize the following news headlines into a 150-200 word briefing for a trading analyst.

Focus on:
- US economic conditions and outlook
- Trade policy, tariffs, and sanctions
- Major company news (earnings, M&A, leadership changes)
- Geopolitical tensions that could affect markets
- Central bank signals and monetary policy

Be factual and terse. Use plain prose, no bullet points. Omit fluff.
If there is nothing notable on a topic, skip it entirely.

Headlines:
{headlines}"""


async def build_digest(llm_client: BaseLLMClient) -> NewsDigest:
    """Full pipeline: fetch → summarize → return digest object."""

    logger.info("Starting news digest build...")
    headlines = await fetch_all_headlines()
    logger.info(f"Total headlines fetched: {len(headlines)}")

    if not headlines:
        logger.warning("No headlines fetched — using fallback digest.")
        return NewsDigest(
            summary="No news data available.",
            headline_count=0,
            created_at=datetime.now(timezone.utc),
        )

    _, summary = await llm_client.summarize_news(headlines=headlines)
    digest = NewsDigest(
        summary=summary,
        headline_count=len(headlines),
        created_at=datetime.now(timezone.utc),
    )
    logger.info("Digest built successfully.")
    return digest
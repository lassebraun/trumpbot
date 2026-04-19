import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlmodel import Session, select

import config
from analysis.base import BaseLLMClient
from database.db import get_engine
from database.models import NewsDigest
from news.summarizer import build_digest
from analysis.llm_clients import GemmaLocalClient

logger = logging.getLogger(__name__)

DIGEST_MAX_AGE_HOURS = 12


async def get_current_digest() -> NewsDigest | None:
    """Return the most recent digest if it's fresh enough, else None."""
    engine = get_engine()
    with Session(engine) as session:
        result = session.exec(
            select(NewsDigest).order_by(NewsDigest.created_at.desc()).limit(1)
        ).first()

    if result is None:
        return None

    age = datetime.now(timezone.utc) - result.created_at.replace(tzinfo=timezone.utc)
    if age > timedelta(hours=DIGEST_MAX_AGE_HOURS):
        logger.info(f"Digest is {age} old — needs refresh.")
        return None

    return result


async def get_or_refresh_digest() -> NewsDigest:

    """
    Returns a fresh digest. Builds a new one if stale or missing.
    Call this before running LLM analysis on a post.
    """
    digest = await get_current_digest()
    if digest:
        age = datetime.now(timezone.utc) - digest.created_at.replace(tzinfo=timezone.utc)
        if age <= timedelta(hours=config.Config.max_digest_age):
            logger.info(f"Using cached digest from {digest.created_at}")
            return digest


    logger.info("No fresh digest found — building new one.")
    digest = await build_digest(config.Config.summary_client)

    engine = get_engine()
    with Session(engine) as session:
        session.add(digest)
        session.commit()
        session.refresh(digest)

    return digest


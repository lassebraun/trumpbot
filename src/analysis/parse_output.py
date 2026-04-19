from typing import Tuple
import json
import logging

from datetime import datetime

from database.models import Posts, NewsDigest, Analyses

logger = logging.getLogger(__name__)
_expected_keys = {"impact_score", "ticker", "direction", "reasoning"}

def parse_response(model: str, model_response: str, post: Posts, news_digest: NewsDigest) -> Analyses | None:
    clean = model_response.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        data = json.loads(clean)
        if _expected_keys.issubset(data.keys()):
            return Analyses(
                post_id = post.id,
                news_summary_id = news_digest.id,
                model = model,
                impact_score = data["impact_score"],
                ticker = data["ticker"],
                direction = data["direction"],
                reasoning = data["reasoning"],
                created_at = datetime.utcnow().isoformat()
            )
        else:
            logger.warning(f"Model output does not contain expected keys {data}")
            return None
    except json.decoder.JSONDecodeError:
        logger.warning(f"Failed to parse model output: {clean}")
        return None

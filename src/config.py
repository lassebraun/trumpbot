from dataclasses import dataclass
from typing import List

from analysis.base import BaseLLMClient
from analysis.llm_clients import GemmaLocalClient

class Config:
    trump_account_id: str = "107780257626128497"
    truth_social_base_url: str = "https://truthsocial.com/api/v1"
    trump_account_page: str = "https://truthsocial.com/@realDonaldTrump"

    database_name = "database.db"

    summary_client = GemmaLocalClient()

    analysis_clients: List[BaseLLMClient] = [
        GemmaLocalClient()
    ]

    analysis_system_prompt = """You are a financial analyst specializing in political risk and market impact assessment.
You will be given a social media  post from Donald Trump and must analyze its potential impact on financial markets.

Current market context:
{news_digest}

You must respond in the following JSON format and nothing else:
{{
    "impact_score": <integer 1-10>,
    "ticker": <string, the single most affected ticker symbol, or null if none>,
    "direction": <"LONG" or "SHORT" or null if impact_score < 3>,
    "reasoning": <string, max 2 sentences explaining your assessment>
}}

Scoring guide:
1-2: No meaningful market impact expected
3-4: Minor impact, sector noise
5-6: Moderate impact, clear directional pressure
7-8: Strong impact, significant price movement likely
9-10: Extreme impact, major market event

Rules:
- Only output valid JSON, no preamble, no markdown backticks
- ticker must be a valid US exchange symbol (e.g. XOM, SPY, NVDA)
- If the post is personal, unrelated to markets or economy, score it 1-2
- Consider both direct and indirect market effects"""

    summarizer_prompt = """You are a terse financial news briefing assistant.

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

    max_digest_age = 12 # hours
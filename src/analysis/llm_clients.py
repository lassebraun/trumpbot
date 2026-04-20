import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from ollama import AsyncClient

from src import config
from src.database.models import Analyses, Posts, NewsDigest
from src.analysis.base import BaseLLMClient
from src.analysis.parse_output import parse_response
from src.news.fetcher import Headline, format_headlines_for_llm

logger = logging.getLogger(__name__)
load_dotenv()

class GemmaLocalClient(BaseLLMClient):

    def __init__(self, model: str = "gemma4:26b"):
        self._model = model

    async def analyze_post(self, post: Posts, news_digest: NewsDigest) -> Analyses | None:
        messages = [
            {'role': 'system', 'content': config.Config.analysis_system_prompt.format(news_digest=news_digest)},
            {'role': 'user', 'content': build_prompt(post.text)},
        ]
        response = await AsyncClient().chat(model=self._model, messages=messages, think=True)
        if not response.message.content:
            logger.warning(f"No response from {self._model}")
            return None
        result = parse_response(self._model, response.message.content, post, news_digest)
        return result

    async def summarize_news(self, headlines: list[Headline]) -> NewsDigest:
        formatted = format_headlines_for_llm(headlines)
        prompt = config.Config.summarizer_prompt.format(headlines=formatted)
        message = {'role': 'user', 'content': prompt}
        response = await AsyncClient().chat(model=self._model, messages=[message], think=True)
        return NewsDigest(
            model = self._model,
            summary = response.message.content,
            headline_count = len(headlines),
        )


class GeminiClient(BaseLLMClient):
    def __init__(self, model: str = "gemma-4-31b-it):
        self._model = model

    async def analyze_post(self, post: Posts, news_digest: NewsDigest) -> Analyses | None:
        _API_KEY = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=_API_KEY)
        response = await client.aio.models.generate_content(
            model = self._model,
            config = types.GenerateContentConfig(
                system_instruction=config.Config.analysis_system_prompt.format(news_digest=news_digest)),
            contents=build_prompt(post.text)
        )
        if response.text:
            result = parse_response(self._model, response.text, post, news_digest)
            return result
        return None

    async def summarize_news(self, headlines: list[Headline]) -> NewsDigest:
        _API_KEY = os.getenv("GEMINI_API_KEY")
        formatted = format_headlines_for_llm(headlines)
        prompt = config.Config.summarizer_prompt.format(headlines=formatted)
        client = genai.Client(api_key=_API_KEY)
        response = await client.aio.models.generate_content(
            model = self._model,
            contents = prompt
        )
        return NewsDigest(
            model = self._model,
            summary = response.text,
            headline_count = len(headlines),
        )


def build_prompt(post_text: str) -> str:
    return f"Analyze this post for market impact: \n\n{post_text}"
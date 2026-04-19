from abc import ABC, abstractmethod

from src.database.models import Analyses, Posts, NewsDigest
from src.news.fetcher import Headline


class BaseLLMClient(ABC):

    @abstractmethod
    async def analyze_post(self, post: Posts, news_digest: NewsDigest) -> Analyses:
        pass
    @abstractmethod
    async def summarize_news(self, headlines: list[Headline]) -> NewsDigest:
        pass

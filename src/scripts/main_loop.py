import asyncio

from src import config
from broker.trade_executor import TradeExecutor
from src.database.crud import DatabaseCrud, QueryFactory
from src.database.models import Posts
from src.news.scheduler import get_or_refresh_digest
from src.scraper.scraper import get_latest_posts


async def main_loop(crud: DatabaseCrud, trade_executor: TradeExecutor) -> None:

    while True:
        # Avoid getting rate blocked by the api
        anchor = crud.get_nth_latest(5)
        posts = get_latest_posts(since_id=anchor.id if anchor else None)
        new_posts = []

        for post in posts:
            if not crud.get_one(Posts, QueryFactory.by_id(post["id"])):
                crud.save(Posts(**post))
                new_posts.append(post)

        news_digest = await get_or_refresh_digest()

        if new_posts:
            analysis_coros = []
            for post in new_posts:
                if is_text_post(post["text"]):
                    for client in config.Config.analysis_clients:
                        analysis_coros.append(client.analyze_post(post, news_digest))
                analyses = await asyncio.gather(*analysis_coros)

                for analysis in analyses:
                    if analysis:
                        crud.save(analysis)
                        trade_executor.process_analysis(analysis)


        await asyncio.sleep(20)

def is_text_post(post_text: str) -> bool:
    if post_text.strip() == "":
        return False
    if post_text.startswith("RT: "):
        return False
    return True
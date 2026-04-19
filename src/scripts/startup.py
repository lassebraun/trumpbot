import logging
from src.broker.client import BrokerClient
from src.database import models, db
from src.database.crud import DatabaseCrud
from src.database.db import init_posts
from src.scraper import scraper
from typing import Tuple

logger = logging.getLogger(__name__)

def startup() -> Tuple[DatabaseCrud, BrokerClient]:
    engine = db.init_db()

    crud = DatabaseCrud(engine)

    posts = scraper.get_latest_posts()

    init_posts(posts, crud)

    broker = BrokerClient()
    account = broker.get_account()
    logger.info(f"Alpaca connected - buying power: {account.buying_power}")

    return crud, broker
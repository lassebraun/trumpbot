from pathlib import Path

from sqlalchemy import Engine, text
from sqlmodel import create_engine, SQLModel
import os

from src.database.models import Posts
from src.config import Config
from src.database.crud import DatabaseCrud, QueryFactory

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DATA_DIR / Config.database_name

def init_db() -> Engine:
    os.makedirs(DATA_DIR, exist_ok=True)

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
    SQLModel.metadata.create_all(engine)
    return engine

def init_posts(posts: list[dict], crud: DatabaseCrud) -> None:
    for post in posts:
        if not crud.get_one(Posts, QueryFactory.by_id(post["id"])):
            crud.save(Posts(**post))

def get_engine() -> Engine:
    engine = create_engine(f"sqlite:///{DB_PATH}",
                           connect_args={
                               "check_same_thread": False,
                                "timeout": 10})
    return engine

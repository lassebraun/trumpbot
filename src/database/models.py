from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, Integer
from datetime import datetime, timezone

class Posts(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: str = Field(default=None, primary_key=True)
    text: str
    created_at: str
    reblogs: int
    favourites: int
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class Analyses(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int = Field(default=None, sa_column=Column(Integer, primary_key=True, autoincrement=True))
    post_id: str = Field(foreign_key='posts.id')
    news_summary_id: Optional[int] = Field(default=None, foreign_key='news_digests.id')
    model: str
    impact_score: int
    ticker: str
    direction: str
    reasoning: str
    created_at: str


class Trade(SQLModel, table=True):
    __tablename__ = "trades"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, sa_column=Column(Integer, primary_key=True, autoincrement=True))
    analysis_id: int = Field(foreign_key="analyses.id")

    # Order details
    ticker: str
    direction: str  # "long" / "short"
    qty: float
    duration_minutes: int

    # Entry
    alpaca_order_id: str
    entry_price: float | None = None
    entry_time: datetime | None = None

    # Exit targets set at open
    stop_loss: float
    take_profit: float
    close_at: datetime  # scheduled time-based exit

    # Exit actuals
    exit_price: float | None = None
    exit_time: datetime | None = None
    exit_reason: str | None = None  # "stop_loss" / "take_profit" / "time" / "error"

    # Result
    pnl: float | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

class NewsDigest(SQLModel, table=True):
    __tablename__ = "news_digests"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, sa_column=Column(Integer, primary_key=True, autoincrement=True))
    model: str
    summary: str
    headline_count: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
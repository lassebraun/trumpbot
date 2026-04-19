from sqlmodel import Field, SQLModel

class Posts(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    text: str
    created_at: str
    reblogs: int
    favourites: int
    scraped_at: str


class Analyses(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    post_id: str
    model: str
    impact_score: int
    ticker: str
    direction: str
    reasoning: str
    created_at: str


class Trades(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    analysis_id: str
    ticker: str
    option_type: str
    strike: str
    expiry: str
    contracts: str
    entry_price: str
    entry_time: str
    exit_price: str
    exit_time: str
    pnl: str
from datetime import datetime
from typing import TypeVar, Type, Callable, Any, Sequence

from sqlalchemy import Engine
from sqlmodel import SQLModel, select, Session

from src.database.models import Posts

T = TypeVar("T", bound=SQLModel)

class QueryFactory:
    @staticmethod
    def by_id(id: str | int):
        return lambda m: m.id == id

    @staticmethod
    def by_field(field: str, value):
        return lambda m: getattr(m, field) == value

    @staticmethod
    def unfilled_trades():
        return lambda m: (m.entry_price == None) & (m.exit_time == None)

    @staticmethod
    def overdue_trades():
        return lambda m: (m.entry_price != None) & (m.exit_time == None) & (m.close_at < datetime.utcnow())

    @staticmethod
    def unclosed_trades():
        return lambda m: (m.entry_price != None) & (m.exit_time == None) & (m.exit_price == None)

    @staticmethod
    def open_trades():
        return lambda m: m.exit_time == None

class DatabaseCrud:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    # ------------- Generic Read -------------------------

    def get_one(
            self,
            model: Type[T],
            rule: Callable = None,

    ) -> T | None:
        with Session(self.engine) as session:
            query = select(model)
            if rule:
                query = query.where(rule(model))
            return session.exec(query).first()

    def get_many(
            self,
            model: Type[T],
            rule: Callable = None,
    ) -> Sequence[Any]:
        with Session(self.engine) as session:
            query = select(model)
            if rule:
                query = query.where(rule(model))
            return session.exec(query).all()

    def get_nth_latest(
            self,
            n: int = 5) -> T | None:
        with Session(self.engine) as session:
            model = Posts
            query = select(model).order_by(model.scraped_at.desc()).offset(n - 1).limit(1)
            return session.exec(query).first()


    # ---------------------- Generic write ---------------------


    def save(self, record: SQLModel) -> SQLModel:
        with Session(self.engine) as session:
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def save_many(self, records: list[SQLModel]) -> None:
        with Session(self.engine) as session:
            for record in records:
                session.add(record)
            session.commit()

    def update(self, record: SQLModel, changes: dict) -> type[SQLModel] | None:
        with Session(self.engine) as session:
            db_record = session.get(type(record), record.id)
            for key, value in changes.items():
                setattr(db_record, key, value)
            session.add(db_record)
            session.commit()
            session.refresh(db_record)
            return db_record


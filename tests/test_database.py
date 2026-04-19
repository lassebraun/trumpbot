import pytest
from sqlmodel import SQLModel, create_engine, Session
from database.crud import DatabaseCrud, QueryFactory
from database.models import Posts, NewsDigest, Analyses
from datetime import datetime

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine

def test_save_and_get_post(session):
    crud = DatabaseCrud(session)
    post = Posts(id="123", text="Hello world", created_at="2026-01-01", reblogs=0, favourites=0)
    
    saved_post = crud.save(post)
    assert saved_post.id == "123"
    
    retrieved_post = crud.get_one(Posts, QueryFactory.by_id("123"))
    assert retrieved_post is not None
    assert retrieved_post.text == "Hello world"

def test_get_many_posts(session):
    crud = DatabaseCrud(session)
    crud.save(Posts(id="1", text="Post 1", created_at="2026-01-01", reblogs=0, favourites=0))
    crud.save(Posts(id="2", text="Post 2", created_at="2026-01-02", reblogs=0, favourites=0))
    
    posts = crud.get_many(Posts)
    assert len(posts) == 2

def test_update_post(session):
    crud = DatabaseCrud(session)
    post = Posts(id="1", text="Old text", created_at="2026-01-01", reblogs=0, favourites=0)
    crud.save(post)
    
    updated_post = crud.update(post, {"text": "New text"})
    assert updated_post.text == "New text"
    
    retrieved_post = crud.get_one(Posts, QueryFactory.by_id("1"))
    assert retrieved_post.text == "New text"

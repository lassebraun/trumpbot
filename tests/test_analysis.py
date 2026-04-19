import pytest
from analysis.parse_output import parse_response
from database.models import Posts, NewsDigest, Analyses

def test_parse_response_valid_json():
    model = "gpt-4o"
    model_response = '```json {"impact_score": 8, "ticker": "TSLA", "direction": "long", "reasoning": "Positive outlook"} ```'
    post = Posts(id="1", text="Some tweet", created_at="2026-01-01", reblogs=0, favourites=0)
    news_digest = NewsDigest(id=1, model="gpt-4o", summary="News summary", headline_count=5)
    
    result = parse_response(model, model_response, post, news_digest)
    
    assert result is not None
    assert result.impact_score == 8
    assert result.ticker == "TSLA"
    assert result.direction == "long"
    assert result.reasoning == "Positive outlook"
    assert result.post_id == "1"
    assert result.news_summary_id == 1

def test_parse_response_missing_keys():
    model = "gpt-4o"
    model_response = '{"ticker": "TSLA", "direction": "long"}'
    post = Posts(id=1, content="Some tweet", author="Elon")
    news_digest = NewsDigest(id=1, summary="News summary", headline_count=5)
    
    result = parse_response(model, model_response, post, news_digest)
    
    assert result is None

def test_parse_response_invalid_json():
    model = "gpt-4o"
    model_response = "Not a JSON string"
    post = Posts(id=1, content="Some tweet", author="Elon")
    news_digest = NewsDigest(id=1, summary="News summary", headline_count=5)
    
    result = parse_response(model, model_response, post, news_digest)
    
    assert result is None

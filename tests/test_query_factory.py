import pytest
from database.crud import QueryFactory
from database.models import Trade
from datetime import datetime, timedelta

def test_query_factory_unfilled_trades():
    rule = QueryFactory.unfilled_trades()
    # unfilled_trades: entry_price == None and exit_time == None
    
    trade1 = Trade(entry_price=None, exit_time=None, analysis_id=1, ticker="AAPL", direction="long", qty=1, duration_minutes=5, alpaca_order_id="abc", stop_loss=100, take_profit=110, close_at=datetime.now())
    trade2 = Trade(entry_price=150, exit_time=None, analysis_id=1, ticker="AAPL", direction="long", qty=1, duration_minutes=5, alpaca_order_id="abc", stop_loss=100, take_profit=110, close_at=datetime.now())
    
    assert rule(trade1) == True
    assert rule(trade2) == False

def test_query_factory_overdue_trades():
    rule = QueryFactory.overdue_trades()
    # overdue_trades: entry_price != None and exit_time == None and close_at < now
    
    now = datetime.utcnow()
    past = now - timedelta(minutes=10)
    future = now + timedelta(minutes=10)
    
    trade_overdue = Trade(entry_price=100, exit_time=None, close_at=past, analysis_id=1, ticker="AAPL", direction="long", qty=1, duration_minutes=5, alpaca_order_id="abc", stop_loss=90, take_profit=110)
    trade_not_overdue = Trade(entry_price=100, exit_time=None, close_at=future, analysis_id=1, ticker="AAPL", direction="long", qty=1, duration_minutes=5, alpaca_order_id="abc", stop_loss=90, take_profit=110)
    trade_no_entry = Trade(entry_price=None, exit_time=None, close_at=past, analysis_id=1, ticker="AAPL", direction="long", qty=1, duration_minutes=5, alpaca_order_id="abc", stop_loss=90, take_profit=110)
    
    assert rule(trade_overdue) == True
    assert rule(trade_not_overdue) == False
    assert rule(trade_no_entry) == False

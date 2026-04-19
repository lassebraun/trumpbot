import logging
from typing import Tuple

from alpaca.data import DataFeed

from src.broker.client import BrokerClient, TradingDirection
from src.database.crud import DatabaseCrud, QueryFactory
from src.database.models import Trade, Analyses

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, broker: BrokerClient, crud: DatabaseCrud):
        self.broker = broker
        self.crud = crud

    def process_analysis(self, analysis: Analyses) -> str | None:
        if not self._should_trade(analysis):
            return None
        qty = self._calculate_qty(analysis.impact_score, analysis.ticker)
        stop_loss, take_profit, duration = self._calculate_exits(analysis.impact_score, analysis.ticker, TradingDirection(analysis.direction.upper()))

        order = self.broker.open_positions(
            ticker=analysis.ticker,
            qty=qty,
            direction=TradingDirection(analysis.direction.upper()),
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        trade = Trade(
            ticker = analysis.ticker,
            direction = analysis.direction.upper(),
            qty = qty,
            duration_minutes = duration,

            alpaca_order_id = order,

            stop_loss = stop_loss,
            take_profit = take_profit,
        )

        self.crud.save(trade)
        return order





    def run_scheduler_tick(self):
        """
        Called every ~60 seconds by the scheduler loop.
        Order matters: fill entries first, then close overdue, then sync exits.
        """
        self._sync_filled_entries()
        self._close_overdue_trades()
        self._sync_closed_exits()

    def _sync_filled_entries(self) -> None:
        """
        For trades where the order was accepted but entry_price is not yet recorded,
        check if Alpaca has filled them and update the DB.
        """
        unfilled = self.crud.get_many(Trade, QueryFactory.unfilled_trades())
        for trade in unfilled:
            result = self.broker.get_order_fill(trade.alpaca_order_id)
            if result is None:
                continue
            fill_price, fill_time = result

            exit_time = trade.entry_time + trade.duration_minutes

            self.crud.update(trade,{
                "entry_price": fill_price,
                "entry_time": fill_time,
                "exit_time": exit_time,
            })
            logger.info(f"Recorded fill for trade {trade.id} on {trade.ticker}: {fill_price} at {fill_time}")

    def _close_overdue_trades(self) -> None:
        """
        For trades that are filled, still open, and past their close_at window,
        submit a market close to Alpaca.
        """
        overdue = self.crud.get_many(Trade, QueryFactory.overdue_trades())
        for trade in overdue:
            success = self.broker.close_position(trade.ticker)
            if success:
                logger.info(f"Submitted time-based close for trade {trade.id} on {trade.ticker}")
            else:
                logger.error(f"Failed to close overdue trade ´{trade.id} on {trade.ticker}")

    def _sync_closed_exits(self) -> None:
        """
        For trades that are filled but exit not yet recorded,
        check if Alpaca closed them (via bracket stop/take profit or our market close)
        and record the exit details + P&L.
        """
        unclosed = self.crud.get_many(Trade, QueryFactory.unclosed_trades())
        for trade in unclosed:
            result = self.broker.get_closed_position(trade.alpaca_order_id)
            if result is None:
                continue
            exit_price, exit_time, exit_reason = result
            pnl = self._calculate_pnl(trade, exit_price)

            self.crud.update(trade,{
                "exit_price": exit_price,
                "exit_time": exit_time,
                "exit_reason": exit_reason,
                "pnl": pnl,
            })

            logger.info(
                f"Closed trade {trade.id} on {trade.ticker} | "
                f"reason={exit_reason} | entry={trade.entry_price} exit={exit_price} | pnl={pnl:+.2f}"
            )


    def _should_trade(self, analysis: Analyses) -> bool:
        if not analysis.impact_score > 5:
            return False
        if not self._is_market_open():
            return False
        if self._is_momentum_saturated(analysis.ticker, TradingDirection(analysis.direction.upper())):
            return False
        return True

    def _is_market_open(self) -> bool:
        clock = self.broker.client.get_clock()
        return clock.is_open

    def _calculate_pnl(self, trade: Trade, exit_price: float) -> float:
        """Calculate Profit/Loss in dollars based on direction and qty"""
        if trade.entry_price is None:
            return 0.0
        diff = exit_price - trade.entry_price
        if trade.direction.upper() == TradingDirection.SHORT:
            diff = -diff
        return round(diff * trade.qty, 4)

    def _is_momentum_saturated(self, ticker: str, direction: TradingDirection) -> bool:
        movement = self.broker.get_recent_movement(ticker)
        threshold = 1.0
        if direction == TradingDirection.LONG and movement >= threshold:
            return True
        if direction == TradingDirection.SHORT and movement <= -threshold:
            return True
        return False

    def _calculate_qty(self, impact_score: float, ticker: str) -> float:
        """Size position as a percentage of buying power based on impact score"""
        account = self.broker.get_account()
        buying_power = float(account.buying_power)

        # 0.5% per impact point above threshold
        pct = (impact_score -5) * 0.005
        dollar_amount = round(buying_power + pct, 2)

        current_price = self._get_current_price(ticker)
        if not current_price:
            return 0.0

        qty = dollar_amount / current_price
        return round(qty, 2)


    def _calculate_exits(self, impact_score: float, ticker: str, direction: TradingDirection) -> Tuple[float, float, int] | None:
        """Returns (stop_loss, take_profit, duration) prices based on impact score and current price."""
        current_price = self._get_current_price(ticker)
        duration = lambda s: 7.5 * s - 15
        if not current_price:
            return None

        stop_pct = 0.03 + (impact_score - 5) * 0.004
        target_pct = stop_pct * 1.6

        if direction == TradingDirection.LONG:
            stop_loss = current_price * (1-stop_pct)
            take_profit = current_price * (1 + stop_pct)
        else:
            stop_loss = current_price * (1+stop_pct)
            take_profit = current_price * (1-target_pct)

        return round(stop_loss, 2), round(take_profit, 2), duration(impact_score)

    def _get_current_price(self, ticker) -> float | None:
        try:
            from alpaca.data.requests import StockLatestQuoteRequest
            request = StockLatestQuoteRequest(symbol_or_symbols=ticker, feed=DataFeed.IEX)
            quote = self.broker.data_client.get_stock_latest_quote(request)
            return float(quote[ticker].ask_price)
        except Exception as e:
            logger.error(f"Failed to get current price for ticker {ticker}: {e}")
            return None
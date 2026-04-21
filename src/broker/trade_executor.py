import logging
import math
from datetime import timedelta
from typing import Tuple

from alpaca.data import DataFeed
from alpaca.data.requests import StockLatestQuoteRequest

from src.broker.client import BrokerClient, TradingDirection
from src.database.crud import DatabaseCrud, QueryFactory
from src.database.models import Trade, Analyses

logger = logging.getLogger(__name__)


class TradeExecutor:
    def __init__(self, broker: BrokerClient, crud: DatabaseCrud):
        self.broker = broker
        self.crud = crud

    def process_analysis(self, analysis: Analyses) -> str | None:
        logger.info(f"Processing analysis for {analysis.ticker} (score: {analysis.impact_score}, direction: {analysis.direction})")
        if not self._should_trade(analysis):
            return None

        try:
            direction = TradingDirection(analysis.direction.upper())
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid direction '{analysis.direction}' for {analysis.ticker}: {e}")
            return None

        # Fetch price once and pass through to avoid duplicate API calls
        current_price = self._get_current_price(analysis.ticker)
        if not current_price:
            logger.error(f"Could not fetch price for {analysis.ticker}, skipping trade")
            return None

        qty = self._calculate_qty(analysis.impact_score, current_price)
        if qty <= 0:
            logger.warning(f"Calculated qty <= 0 for {analysis.ticker} (price: {current_price}, score: {analysis.impact_score}), skipping trade")
            return None

        stop_loss, take_profit, duration = self._calculate_exits(
            analysis.impact_score, current_price, direction
        )

        try:
            logger.info(f"Attempting to open {direction.value} position for {analysis.ticker}: qty={qty}, stop={stop_loss}, tp={take_profit}")
            order = self.broker.open_positions(
                ticker=analysis.ticker,
                qty=qty,
                direction=direction,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
            if not order:
                logger.error(f"Broker returned empty order ID for {analysis.ticker}")
                return None

            trade = Trade(
                analysis_id=analysis.id,
                ticker=analysis.ticker,
                direction=direction.value,
                qty=qty,
                duration_minutes=duration,
                alpaca_order_id=order,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
            self.crud.save(trade)
            logger.info(
                f"Trade SUCCESS: {analysis.ticker} | id={order} | score={analysis.impact_score} "
                f"qty={qty} stop={stop_loss} target={take_profit} duration={duration}min"
            )
            return order
        except Exception as e:
            logger.error(f"Failed to open position {analysis.ticker}: {e}", exc_info=True)
            return None

    # ---------------------- Scheduler entrypoint ----------------------

    async def run_scheduler_tick(self):
        """
        Called every ~60 seconds by the scheduler loop.
        Order matters: fill entries first, then close overdue, then sync exits.
        """
        self._sync_filled_entries()
        await self._close_overdue_trades()
        self._sync_closed_exits()

    # ---------------------- Scheduler steps ----------------------

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
            close_at = fill_time + timedelta(minutes=trade.duration_minutes)

            self.crud.update(trade, {
                "entry_price": fill_price,
                "entry_time": fill_time,
                "close_at": close_at,
            })
            logger.info(
                f"Recorded fill for trade {trade.id} on {trade.ticker}: "
                f"{fill_price} at {fill_time}, close_at={close_at}"
            )

    async def _close_overdue_trades(self) -> None:
        """
        For trades that are filled, still open, and past their close_at window,
        submit a market close to Alpaca.
        """
        overdue = self.crud.get_many(Trade, QueryFactory.overdue_trades())
        for trade in overdue:
            success = await self.broker.close_position(trade.ticker, trade.alpaca_order_id)
            if success:
                logger.info(f"Submitted time-based close for trade {trade.id} on {trade.ticker}")
            else:
                logger.error(f"Failed to close overdue trade {trade.id} on {trade.ticker}")

    def _sync_closed_exits(self) -> None:
        """
        For trades that are filled but exit not yet recorded,
        check if Alpaca closed them via bracket stop/take profit or our market close
        and record the exit details + P&L.
        """
        unclosed = self.crud.get_many(Trade, QueryFactory.unclosed_trades())
        for trade in unclosed:
            result = self.broker.get_closed_position(trade.alpaca_order_id)
            if result is None:
                continue
            exit_price, exit_time, exit_reason = result
            pnl = self._calculate_pnl(trade, exit_price)

            self.crud.update(trade, {
                "exit_price": exit_price,
                "exit_time": exit_time,
                "exit_reason": exit_reason,
                "pnl": pnl,
            })
            logger.info(
                f"Closed trade {trade.id} on {trade.ticker} | "
                f"reason={exit_reason} | entry={trade.entry_price} exit={exit_price} | pnl={pnl:+.2f}"
            )

    # ---------------------- Decision logic ----------------------

    def _should_trade(self, analysis: Analyses) -> bool:
        if analysis.impact_score <= 5:
            logger.info(f"Skipping {analysis.ticker}: Impact score {analysis.impact_score} <= 5 threshold")
            return False
        
        if not self._is_market_open():
            logger.warning(f"Skipping {analysis.ticker}: Market is currently closed")
            return False
            
        open_trades = self.crud.get_many(Trade, QueryFactory.open_trades())
        if len(open_trades) > 0:
            logger.info(f"Skipping {analysis.ticker}: Already have {len(open_trades)} open trade(s)")
            return False
            
        direction_str = analysis.direction.upper() if analysis.direction else "UNKNOWN"
        try:
            direction = TradingDirection(direction_str)
            if self._is_momentum_saturated(analysis.ticker, direction):
                logger.warning(f"Skipping {analysis.ticker}: Momentum saturated for {direction_str}")
                return False
        except ValueError:
            logger.error(f"Skipping {analysis.ticker}: Invalid direction '{direction_str}'")
            return False
            
        return True

    def _is_market_open(self) -> bool:
        clock = self.broker.client.get_clock()
        return clock.is_open

    def _is_momentum_saturated(self, ticker: str, direction: TradingDirection) -> bool:
        movement = self.broker.get_recent_movement(ticker)
        threshold = 1.0
        if direction == TradingDirection.LONG and movement >= threshold:
            return True
        if direction == TradingDirection.SHORT and movement <= -threshold:
            return True
        return False

    # ---------------------- Calculation helpers ----------------------

    def _calculate_qty(self, impact_score: float, current_price: float) -> int:
        """Size position as a percentage of buying power based on impact score."""
        account = self.broker.get_account()
        buying_power = float(account.buying_power)

        # 0.5% of buying power per impact point above threshold (score 6 → 0.5%, 10 → 2.5%)
        pct = (impact_score - 5) * 0.005
        dollar_amount = buying_power * pct

        qty = math.floor(dollar_amount / current_price)
        return qty

    def _calculate_exits(
        self, impact_score: float, current_price: float, direction: TradingDirection
    ) -> Tuple[float, float, int]:
        """Returns (stop_loss, take_profit, duration_minutes) based on impact score and current price."""
        # Stop widens with impact score: score 6 → 3.4%, score 10 → 5%
        stop_pct = 0.03 + (impact_score - 5) * 0.004
        target_pct = stop_pct * 1.6  # constant 1.6 reward/risk ratio

        if direction == TradingDirection.LONG:
            stop_loss = current_price * (1 - stop_pct)
            take_profit = current_price * (1 + target_pct)
        else:
            stop_loss = current_price * (1 + stop_pct)
            take_profit = current_price * (1 - target_pct)

        # Duration scales from 30min (score 5) to 60min (score 10)
        duration = int(30 + (impact_score - 5) * 6)

        return round(stop_loss, 2), round(take_profit, 2), duration

    def _calculate_pnl(self, trade: Trade, exit_price: float) -> float:
        """Calculates P&L in dollars based on direction and qty."""
        if trade.entry_price is None:
            return 0.0
        diff = exit_price - trade.entry_price
        if trade.direction.upper() == TradingDirection.SHORT.value:
            diff = -diff
        return round(diff * trade.qty, 4)

    def _get_current_price(self, ticker: str) -> float | None:
        """Fetches latest ask price via the data client."""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=ticker, feed=DataFeed.IEX)
            quote = self.broker.data_client.get_stock_latest_quote(request)
            return float(quote[ticker].ask_price)
        except Exception as e:
            logger.error(f"Failed to get current price for ticker {ticker}: {e}")
            return None
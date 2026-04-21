import logging
import os
import asyncio
from datetime import datetime, timezone, timedelta
from enum import Enum

from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading import StopLossRequest, TakeProfitRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus, OrderClass
from alpaca.trading.requests import MarketOrderRequest
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class TradingDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NULL = "NULL"


class BrokerClient:
    def __init__(self):
        self.client = TradingClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
            paper=True
        )
        self.data_client = StockHistoricalDataClient(
            api_key=os.getenv("ALPACA_API_KEY"),
            secret_key=os.getenv("ALPACA_SECRET_KEY"),
        )

    def open_positions(
            self,
            ticker: str,
            qty: float,
            direction: TradingDirection,
            stop_loss: float,
            take_profit: float,
    ) -> str | None:
        """Opens a bracket order. Returns alpaca order ID or None on failure."""
        try:
            side = OrderSide.BUY if direction == TradingDirection.LONG else OrderSide.SELL
            request_params = {
                "symbol": ticker,
                "qty": qty,
                "side": side,
                "time_in_force": TimeInForce.DAY,
                "order_class": OrderClass.BRACKET,
                "stop_loss": StopLossRequest(stop_price=round(stop_loss, 2)),
                "take_profit": TakeProfitRequest(limit_price=round(take_profit, 2)),
            }
            request = MarketOrderRequest(**request_params)
            order = self.client.submit_order(request)
            logger.info(f"Opened {direction} position on {ticker}: order {order.id}")
            return str(order.id)
        except Exception as e:
            logger.error(f"Failed to open position on {ticker}: {e}")
            return None

    async def close_position(self, ticker: str, order_id) -> bool:
        """Closes entire open position for a ticker. Returns success bool."""
        try:
            parent_order = self.client.get_order_by_id(order_id)
            for leg in parent_order.legs:
                try:
                    self.client.cancel_order_by_id(leg.id)
                    logger.info(f"Cancelled child order {leg.id} for {ticker}")
                except Exception:
                    pass  # leg may already be filled/cancelled

            await asyncio.sleep(0.5)

            self.client.close_position(ticker)
            logger.info(f"Closed position on {ticker}")
            return True
        except Exception as e:
            logger.error(f"Failed to close position on {ticker}: {e}")
            return False

    def get_order_fill(self, alpaca_order_id: str) -> tuple[float, datetime] | None:
        """Returns (fill_price, fill_time) if the entry order is filled, None otherwise."""
        try:
            order = self.client.get_order_by_id(alpaca_order_id)
            if order.status == OrderStatus.FILLED and order.filled_avg_price:
                return float(order.filled_avg_price), order.filled_at
            return None
        except Exception as e:
            logger.error(f"Failed to get order fill for {alpaca_order_id}: {e}")
            return None

    def get_closed_position(self, alpaca_order_id: str, ticker: str, entry_time: datetime) -> tuple[
                                                                                                  float, datetime, str] | None:
        """
        Checks if a position has been closed either via bracket legs or a manual market close.
        Returns (exit_price, exit_time, exit_reason) or None if still open.
        """
        try:
            # check bracket legs first (stop loss / take profit)
            order = self.client.get_order_by_id(alpaca_order_id)
            if order.legs:
                for leg in order.legs:
                    if leg.status == OrderStatus.FILLED and leg.filled_avg_price:
                        reason = self._classify_exit_reason(leg)
                        return float(leg.filled_avg_price), leg.filled_at, reason

            # check for a separate market close order (time-based exit)
            activities = self.client.get_portfolio_history  # wrong, use orders instead
            close_orders = self.client.get_orders(
                filter=GetOrdersRequest(
                    status=QueryOrderStatus.CLOSED,
                    symbols=[ticker],
                    after=entry_time,
                )
            )
            for o in close_orders:
                # skip the original entry order
                if str(o.id) == alpaca_order_id:
                    continue
                if (
                        o.status == OrderStatus.FILLED
                        and o.side == OrderSide.SELL
                        and o.filled_avg_price
                ):
                    return float(o.filled_avg_price), o.filled_at, "time_exit"

            return None
        except Exception as e:
            logger.error(f"Failed to get closed position for {alpaca_order_id}: {e}")
            return None

    def get_recent_movement(self, ticker: str, minutes: int = 15) -> float:
        """Returns price change as percentage over the last N minutes."""
        try:
            now = datetime.now(timezone.utc)
            request_params = {
                "symbol_or_symbols": ticker,
                "timeframe": TimeFrame.Minute,
                "start": now - timedelta(minutes=minutes),
                "end": now,
                "feed": DataFeed.IEX
            }
            request = StockBarsRequest(**request_params)
            response = self.data_client.get_stock_bars(request)
            bars = response.data.get(ticker, [])

            if not bars or len(bars) < 2:
                return 0.0

            change = (bars[-1].close - bars[0].open) / bars[0].open * 100
            return round(change, 4)
        except Exception as e:
            logger.error(f"Failed to get recent movement for {ticker}: {e}")
            return 0.0

    def get_account(self):
        """Sanity check. Call on startup."""
        return self.client.get_account()

    def _classify_exit_reason(self, leg) -> str:
        """Infers exit reason from bracket order leg type."""
        order_type = str(leg.order_type).lower()
        if "stop" in order_type:
            return "stop_loss"
        if "limit" in order_type:
            return "take_profit"
        return "time"
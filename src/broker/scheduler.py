import logging
import time

from broker.client import BrokerClient
from broker.trade_executor import TradeExecutor
from database.crud import DatabaseCrud

logger = logging.getLogger(__name__)

def scheduler_loop(executor: TradeExecutor):
    while True:
        try:
            executor.run_scheduler_tick()
        except Exception as e:
            logger.error(f"Scheduler tick failed: {e}")
        time.sleep(60)

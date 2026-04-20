import logging
import time

from src.broker.trade_executor import TradeExecutor

logger = logging.getLogger(__name__)

def scheduler_loop(executor: TradeExecutor):
    logger.info('Stared broker scheduler loop')
    while True:
        try:
            executor.run_scheduler_tick()
        except Exception as e:
            logger.error(f"Scheduler tick failed: {e}")
        time.sleep(60)

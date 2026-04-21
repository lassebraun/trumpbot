import logging
import asyncio

from src.broker.trade_executor import TradeExecutor

logger = logging.getLogger(__name__)

async def scheduler_loop(executor: TradeExecutor):
    logger.info('Stared broker scheduler loop')
    while True:
        try:
            await executor.run_scheduler_tick()
        except Exception as e:
            logger.error(f"Scheduler tick failed: {e}")
        await asyncio.sleep(60)

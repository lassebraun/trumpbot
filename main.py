import sys
import time
import logging
import asyncio

from src.database.crud import DatabaseCrud
from src.broker.trade_executor import TradeExecutor
from src.scripts.main_loop import main_loop
from src.broker.scheduler import scheduler_loop
from src.scripts import startup
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/trumbot.log")
    ]
)

logger = logging.getLogger(__name__)

def handle_shutdown(signum, frame):
    logger.info("Shutting down...")
    print("Received signal {}".format(signum))
    raise KeyboardInterrupt

def run_main_loop(crud: DatabaseCrud, trade_executor: TradeExecutor):
    asyncio.run(main_loop(crud, trade_executor))

def main() -> None:
    logger.info("Starting up...")
    crud, broker = startup.startup()
    trade_executor = TradeExecutor(broker, crud)

    main_thread = threading.Thread(target=run_main_loop, args=(crud, trade_executor), daemon=True)
    scheduler_thread = threading.Thread(target=scheduler_loop, args=(trade_executor, ), daemon=True)

    main_thread.start()
    scheduler_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == "__main__":
    main()
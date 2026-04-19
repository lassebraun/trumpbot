import time

from src.broker.trade_executor import TradeExecutor
from src.scripts.main_loop import main_loop
from src.broker.scheduler import scheduler_loop
from src.scripts import startup
import threading

def handle_shutdown(signum, frame):
    print("Received signal {}".format(signum))
    raise KeyboardInterrupt

def main() -> None:
    crud, broker = startup.startup()
    trade_executor = TradeExecutor(broker, crud)

    main_thread = threading.Thread(target=main_loop, args=(crud, trade_executor), daemon=True)
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

import time
from datetime import datetime, timezone

def run_bot():
    print("Binance Momentum Bot started")
    print("Mode: PAPER TRADING - No real orders")
    print("Market: Binance Spot")

    while True:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Bot is running - scanning market...")
        time.sleep(60)

if __name__ == "__main__":
    run_bot()

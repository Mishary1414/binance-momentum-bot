
import json
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.binance.com"

START_BALANCE = 530.0
RESERVE = 130.0
MAX_POSITIONS = 3
MAX_PER_TRADE = 130.0

STOP_LOSS = 0.025
TAKE_PROFIT = 0.05
FEE = 0.001

balance = START_BALANCE
positions = {}
closed_trades = 0


def api(path):
    req = urllib.request.Request(
        BASE + path,
        headers={"User-Agent": "MomentumBot/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def ema(values, period):
    result = values[0]
    alpha = 2 / (period + 1)
    for value in values[1:]:
        result = value * alpha + result * (1 - alpha)
    return result


def get_candidates():
    tickers = api("/api/v3/ticker/24hr")

    excluded = (
        "UPUSDT", "DOWNUSDT", "BULLUSDT",
        "BEARUSDT", "USDCUSDT", "FDUSDUSDT",
        "TUSDUSDT", "USDPUSDT", "EURUSDT"
    )

    valid = [
        t for t in tickers
        if t["symbol"].endswith("USDT")
        and t["symbol"] not in excluded
        and float(t["quoteVolume"]) > 2_000_000
        and 2 <= float(t["priceChangePercent"]) <= 18
    ]

    return sorted(
        valid,
        key=lambda x: float(x["quoteVolume"]),
        reverse=True
    )[:25]


def get_signal(symbol):
    candles = api(
        f"/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
    )

    # Use the last completed candle
    candles = candles[:-1]

    closes = [float(c[4]) for c in candles]
    volumes = [float(c[5]) for c in candles]
    highs = [float(c[2]) for c in candles]

    if len(closes) < 25:
        return None

    fast = ema(closes[-30:], 9)
    slow = ema(closes[-30:], 21)

    last_close = closes[-1]
    last_volume = volumes[-1]
    average_volume = sum(volumes[-21:-1]) / 20

    previous_high = max(highs[-21:-1])

    if (
        fast > slow
        and last_close > fast
        and last_close > previous_high
        and last_volume > average_volume * 1.5
    ):
        return {
            "price": last_close,
            "volume_ratio": last_volume / average_volume
        }

    return None


def buy(symbol, signal):
    global balance

    if len(positions) >= MAX_POSITIONS:
        return

    if symbol in positions:
        return

    spend = min(MAX_PER_TRADE, balance - RESERVE)

    if spend <= 0:
        return

    price = signal["price"]
    quantity = spend / price

    balance -= spend

    positions[symbol] = {
        "entry": price,
        "quantity": quantity,
        "invested": spend,
        "time": datetime.now(timezone.utc).isoformat()
    }

    print(
        f"BUY PAPER | {symbol} | "
        f"Price: {price} | "
        f"Amount: {spend:.2f} USDT | "
        f"Volume ratio: {signal['volume_ratio']:.2f}"
    )


def sell(symbol, price, reason):
    global balance, closed_trades

    position = positions[symbol]

    gross = position["quantity"] * price
    fee = gross * FEE

    net = gross - fee
    entry_cost = position["invested"] * (1 + FEE)

    profit = net - entry_cost

    balance += gross - fee
    closed_trades += 1

    print(
        f"SELL PAPER | {symbol} | "
        f"Reason: {reason} | "
        f"Net P/L: {profit:.3f} USDT | "
        f"Balance: {balance:.2f}"
    )

    del positions[symbol]


def manage_positions():
    for symbol in list(positions):
        try:
            data = api(
                f"/api/v3/ticker/price?symbol={symbol}"
            )
            price = float(data["price"])

            entry = positions[symbol]["entry"]
            change = (price - entry) / entry

            if change <= -STOP_LOSS:
                sell(symbol, price, "STOP LOSS")

            elif change >= TAKE_PROFIT:
                sell(symbol, price, "TAKE PROFIT")

        except Exception as error:
            print("Position check error:", symbol, error)


def run():
    print("BINANCE MOMENTUM BOT STARTED")
    print("MODE: PAPER TRADING")
    print("REAL ORDERS: DISABLED")

    while True:
        try:
            manage_positions()

            candidates = get_candidates()

            for ticker in candidates:
                symbol = ticker["symbol"]

                if symbol in positions:
                    continue

                if len(positions) >= MAX_POSITIONS:
                    break

                if balance <= RESERVE:
                    break

                try:
                    signal = get_signal(symbol)

                    if signal:
                        buy(symbol, signal)

                    time.sleep(0.3)

                except Exception as error:
                    print("Scan error:", symbol, error)

            print(
                f"SCAN COMPLETE | "
                f"Candidates: {len(candidates)} | "
                f"Open trades: {len(positions)} | "
                f"Closed trades: {closed_trades} | "
                f"Cash: {balance:.2f} USDT"
            )

            time.sleep(60)

        except Exception as error:
            print("MAIN ERROR:", error)
            time.sleep(30)


if __name__ == "__main__":
    run()

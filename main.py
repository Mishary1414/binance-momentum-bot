
import json
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.kraken.com/0/public"

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
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def get_candidates():
    data = api("/Ticker?pair=XXBTZUSD,XETHZUSD,SOLUSD,XRPUSD,ADAUSD,DOGEUSD,LINKUSD,AVAXUSD")
    result = data["result"]
    candidates = []

    for pair, item in result.items():
        price = float(item["c"][0])
        volume = float(item["v"][1])
        change = ((price / float(item["o"])) - 1) * 100

        if volume > 100 and 0.5 < change < 15:
            candidates.append({
                "symbol": pair,
                "price": price,
                "volume": volume,
                "change": change
            })

    return sorted(candidates, key=lambda x: x["volume"], reverse=True)


def get_signal(pair):
    data = api(f"/OHLC?pair={pair}&interval=5")
    result = data["result"]

    key = next(k for k in result if k != "last")
    candles = result[key][:-1]

    closes = [float(c[4]) for c in candles]
    volumes = [float(c[6]) for c in candles]

    if len(closes) < 25:
        return None

    fast = sum(closes[-9:]) / 9
    slow = sum(closes[-21:]) / 21

    average_volume = sum(volumes[-21:-1]) / 20

    if fast > slow and closes[-1] > fast and volumes[-1] > average_volume * 1.5:
        return closes[-1]

    return None


def buy(symbol, price):
    global balance

    if symbol in positions or len(positions) >= MAX_POSITIONS:
        return

    spend = min(MAX_PER_TRADE, balance - RESERVE)

    if spend <= 0:
        return

    balance -= spend

    positions[symbol] = {
        "entry": price,
        "quantity": spend / price,
        "invested": spend
    }

    print(f"BUY PAPER | {symbol} | Price: {price} | Amount: {spend:.2f}")


def sell(symbol, price, reason):
    global balance, closed_trades

    p = positions[symbol]
    gross = p["quantity"] * price
    net = gross * (1 - FEE)
    cost = p["invested"] * (1 + FEE)
    profit = net - cost

    balance += net
    closed_trades += 1

    print(
        f"SELL PAPER | {symbol} | {reason} | "
        f"P/L: {profit:.3f} USD | Balance: {balance:.2f}"
    )

    del positions[symbol]


def manage_positions():
    for symbol in list(positions):
        try:
            data = api(f"/Ticker?pair={symbol}")
            item = next(iter(data["result"].values()))
            price = float(item["c"][0])

            entry = positions[symbol]["entry"]
            change = (price - entry) / entry

            if change <= -STOP_LOSS:
                sell(symbol, price, "STOP LOSS")
            elif change >= TAKE_PROFIT:
                sell(symbol, price, "TAKE PROFIT")

        except Exception as e:
            print("Position error:", symbol, e)


def run():
    print("KRAKEN DATA MOMENTUM BOT STARTED")
    print("MODE: PAPER TRADING")
    print("REAL ORDERS: DISABLED")

    while True:
        try:
            manage_positions()
            candidates = get_candidates()

            for item in candidates:
                if len(positions) >= MAX_POSITIONS:
                    break

                symbol = item["symbol"]

                if symbol in positions:
                    continue

                signal = get_signal(symbol)

                if signal:
                    buy(symbol, signal)

                time.sleep(1)

            print(
                f"SCAN COMPLETE | Candidates: {len(candidates)} | "
                f"Open: {len(positions)} | Closed: {closed_trades} | "
                f"Cash: {balance:.2f} USD"
            )

            time.sleep(60)

        except Exception as e:
            print("MAIN ERROR:", repr(e))
            time.sleep(30)


if __name__ == "__main__":
    run()


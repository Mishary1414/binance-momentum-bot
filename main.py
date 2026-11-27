
import json
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.kraken.com/0/public"
WATCHLIST = [
    "XXBTZUSD", "XETHZUSD", "SOLUSD", "XRPUSD",
    "ADAUSD", "DOGEUSD", "LINKUSD", "AVAXUSD",
    "DOTUSD", "LTCUSD", "TRXUSD", "ATOMUSD",
    "NEARUSD", "UNIUSD", "ETCUSD", "BCHUSD",
    "AAVEUSD", "FILUSD", "APTUSD", "INJUSD"
]

def api(path):
    request = urllib.request.Request(
        BASE + path,
        headers={"User-Agent": "MomentumBot/2.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read())

def ticker_data(pair):
    data = api("/Ticker?pair=" + pair)
    if data.get("error"):
        raise Exception(data["error"])
    item = next(iter(data["result"].values()))
    price = float(item["c"][0])
    opening = float(item["o"])
    volume = float(item["v"][1])
    change = (price / opening - 1) * 100
    return price, volume, change

def analyze(pair):
    data = api("/OHLC?pair=" + pair + "&interval=5")
    result = data["result"]
    key = next(k for k in result if k != "last")
    candles = result[key][:-1]

    if len(candles) < 25:
        return None

    closes = [float(c[4]) for c in candles]
    volumes = [float(c[6]) for c in candles]

    fast = sum(closes[-9:]) / 9
    slow = sum(closes[-21:]) / 21
    avg_volume = sum(volumes[-21:-1]) / 20

    last_volume = volumes[-1]
    last_price = closes[-1]

    if avg_volume <= 0:
        return None

    volume_ratio = last_volume / avg_volume
    trend = fast > slow and last_price > fast

    score = 0
    if trend:
        score += 40
    if volume_ratio >= 1.5:
        score += 35
    elif volume_ratio >= 1.2:
        score += 20
    if last_price > max(closes[-6:-1]):
        score += 25

    return {
        "score": score,
        "volume_ratio": volume_ratio,
        "trend": trend,
        "price": last_price
    }

def run():
    print("MOMENTUM SCANNER 2.0 STARTED")
    print("MARKET DATA: KRAKEN")
    print("MODE: ANALYSIS ONLY - NO REAL ORDERS")

    while True:
        rows = []

        for pair in WATCHLIST:
            try:
                price, volume, change = ticker_data(pair)
                signal = analyze(pair)

                if signal:
                    rows.append({
                        "pair": pair,
                        "price": price,
                        "volume": volume,
                        "change": change,
                        **signal
                    })

                time.sleep(1)

            except Exception as error:
                print("PAIR ERROR:", pair, str(error))

        rows.sort(key=lambda x: x["score"], reverse=True)

        print("\n" + "=" * 45)
        print("TOP 5 MOMENTUM CANDIDATES")
        print(datetime.now(timezone.utc).isoformat())

        for row in rows[:5]:
            print(
                f"{row['pair']} | Score: {row['score']}/100 | "
                f"24h: {row['change']:.2f}% | "
                f"Volume: {row['volume']:.2f} | "
                f"5m Volume Ratio: {row['volume_ratio']:.2f} | "
                f"Trend: {row['trend']}"
            )

        print("COINS ANALYZED:", len(rows))
        print("NEXT SCAN IN 60 SECONDS")
        time.sleep(60)

if __name__ == "__main__":
    while True:
        try:
            run()
        except Exception as error:
            print("MAIN ERROR:", repr(error))
            time.sleep(30)


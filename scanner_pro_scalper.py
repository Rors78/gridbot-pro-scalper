import subprocess
import sys

# Auto-update dependencies before launch
subprocess.run([
    sys.executable, '-m', 'pip', 'install', '--upgrade', '-r', 'requirements.txt'
], check=True)

import os
import time
import json
from datetime import datetime
from binance.client import Client

# -------- API Credentials (from environment) --------
# Set these in your environment or .env file:
# export BINANCE_API_KEY='your_key_here'
# export BINANCE_API_SECRET='your_secret_here'
API_KEY = os.environ.get('BINANCE_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_API_SECRET', '')

if not API_KEY or not API_SECRET:
    print("ERROR: BINANCE_API_KEY and BINANCE_API_SECRET must be set in environment")
    sys.exit(1)

client = Client(API_KEY, API_SECRET, tld='us')

# -------- Configuration --------
REFRESH_INTERVAL = 10    # seconds
RISK_USDT = 20           # USDT per trade
POSITIONS_FILE = 'positions.json'

# -------- Persistence --------
if os.path.exists(POSITIONS_FILE):
    with open(POSITIONS_FILE) as f:
        positions = json.load(f)
else:
    positions = {}

def save_positions():
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f)

# -------- Indicators --------
def ema(series, period):
    alpha = 2 / (period + 1)
    ema_val = series[0]
    for price in series[1:]:
        ema_val = alpha * price + (1 - alpha) * ema_val
    return ema_val

def rsi(series, period=14):
    """Calculate RSI (Relative Strength Index) for a price series."""
    if len(series) < period + 1:
        return 50  # Not enough data, return neutral

    # Calculate price changes
    deltas = [series[i] - series[i-1] for i in range(1, len(series))]

    # Use the last 'period' deltas
    recent_deltas = deltas[-period:]

    # Separate gains and losses (keeping zeros for days with no movement)
    gains = [d if d > 0 else 0 for d in recent_deltas]
    losses = [-d if d < 0 else 0 for d in recent_deltas]

    # Calculate averages
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Handle edge case: no losses = RSI is 100
    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def fetch_pairs():
    info = client.get_exchange_info()
    return [s['symbol'] for s in info['symbols']
            if s['quoteAsset']=='USDT' and s['status']=='TRADING']

def fetch_klines(symbol, interval='1m', limit=50):
    return client.get_klines(symbol=symbol, interval=interval, limit=limit)

def calculate_ATR(candles):
    highs = [float(c[2]) for c in candles]
    lows  = [float(c[3]) for c in candles]
    tr = [h-l for h, l in zip(highs, lows)]
    return sum(tr)/len(tr) if tr else 0

def dynamic_tp(candles):
    atr = calculate_ATR(candles)
    last = float(candles[-1][4])
    return [round(last + m*atr, 2) for m in (0.5,1.0,1.5,2.0)]

# -------- Main Loop --------
def main():
    print("=== GridBot Pro Scalper Live ===")
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pairs = fetch_pairs()
        signal_found = False
        for sym in pairs:
            kl = fetch_klines(sym)
            closes = [float(c[4]) for c in kl]
            vols = [float(c[5]) for c in kl]
            # Indicators
            ema_fast = ema(closes[-5:], 5)
            ema_slow = ema(closes[-20:], 20)
            r = rsi(closes[-15:])
            vol_spike = vols[-1] >= 2 * (sum(vols[-11:-1])/10)
            # Entry condition
            if ema_fast>ema_slow and r>50 and vol_spike:
                if sym not in positions:
                    # Place market buy
                    price = float(client.get_symbol_ticker(symbol=sym)['price'])
                    qty = round(RISK_USDT/price, 6)
                    client.order_market_buy(symbol=sym, quantity=qty)
                    # Place TPs
                    tps = dynamic_tp(kl)
                    share = round(qty/len(tps), 6)
                    for tp in tps:
                        client.order_limit_sell(symbol=sym, quantity=share, price=str(tp))
                    positions[sym] = {'qty': qty, 'tps': tps}
                    save_positions()
                    print(f"[{now}] Bought {sym} qty={qty}, set TPs={tps}")
                    signal_found = True
                break
        if not signal_found:
            print(f"[{now}] No entry signal found.")
        time.sleep(REFRESH_INTERVAL)

if __name__=="__main__":
    main()

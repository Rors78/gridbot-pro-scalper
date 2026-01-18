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

# -------- Configuration --------
PAPER_TRADING = True     # Set to False for live trading
REFRESH_INTERVAL = 10    # seconds
RISK_USDT = 20           # USDT per trade
POSITIONS_FILE = 'positions.json'
PAPER_TRADES_FILE = 'paper_trades.json'

# -------- Paper Trading State --------
paper_balance = 1000.0   # Starting paper balance in USDT
paper_trades = []        # Trade history

def load_paper_state():
    global paper_balance, paper_trades
    if os.path.exists(PAPER_TRADES_FILE):
        with open(PAPER_TRADES_FILE) as f:
            data = json.load(f)
            paper_balance = data.get('balance', 1000.0)
            paper_trades = data.get('trades', [])

def save_paper_state():
    with open(PAPER_TRADES_FILE, 'w') as f:
        json.dump({'balance': paper_balance, 'trades': paper_trades}, f, indent=2)

# -------- Initialize --------
if PAPER_TRADING:
    load_paper_state()
    print("=" * 50)
    print("🧻 PAPER TRADING MODE - NO REAL MONEY AT RISK")
    print(f"   Starting balance: ${paper_balance:.2f} USDT")
    print("=" * 50)
    # Still need API for price data (read-only)
    if API_KEY and API_SECRET:
        client = Client(API_KEY, API_SECRET, tld='us')
    else:
        print("Note: Using public endpoints for price data")
        client = Client("", "", tld='us')
else:
    if not API_KEY or not API_SECRET:
        print("ERROR: BINANCE_API_KEY and BINANCE_API_SECRET must be set for live trading")
        sys.exit(1)
    client = Client(API_KEY, API_SECRET, tld='us')
    print("=" * 50)
    print("⚠️  LIVE TRADING MODE - REAL MONEY AT RISK")
    print("=" * 50)

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

# -------- Trading Functions --------
def execute_buy(symbol, qty, price):
    """Execute a buy order (paper or live)."""
    global paper_balance

    if PAPER_TRADING:
        cost = qty * price
        if cost > paper_balance:
            print(f"[PAPER] Insufficient balance: need ${cost:.2f}, have ${paper_balance:.2f}")
            return False
        paper_balance -= cost
        paper_trades.append({
            'time': datetime.now().isoformat(),
            'type': 'BUY',
            'symbol': symbol,
            'qty': qty,
            'price': price,
            'cost': cost
        })
        save_paper_state()
        print(f"[PAPER] BUY {symbol}: {qty} @ ${price:.4f} (cost: ${cost:.2f})")
        return True
    else:
        client.order_market_buy(symbol=symbol, quantity=qty)
        return True

def execute_sell(symbol, qty, price):
    """Execute a sell order (paper or live)."""
    global paper_balance

    if PAPER_TRADING:
        revenue = qty * price
        paper_balance += revenue
        paper_trades.append({
            'time': datetime.now().isoformat(),
            'type': 'SELL',
            'symbol': symbol,
            'qty': qty,
            'price': price,
            'revenue': revenue
        })
        save_paper_state()
        print(f"[PAPER] SELL {symbol}: {qty} @ ${price:.4f} (revenue: ${revenue:.2f})")
        return True
    else:
        client.order_limit_sell(symbol=symbol, quantity=qty, price=str(price))
        return True

def check_tp_hits():
    """Check if any take-profit levels have been hit (paper mode only)."""
    global paper_balance

    if not PAPER_TRADING:
        return  # Live mode handles this via exchange orders

    to_remove = []
    for sym, pos in positions.items():
        try:
            current_price = float(client.get_symbol_ticker(symbol=sym)['price'])
            hit_tps = [tp for tp in pos['tps'] if current_price >= tp]

            if hit_tps:
                # Calculate shares per TP level
                share = pos['qty'] / len(pos['tps'])
                for tp in hit_tps:
                    execute_sell(sym, share, tp)
                    pos['tps'].remove(tp)
                    pos['qty'] -= share

                if not pos['tps']:  # All TPs hit
                    to_remove.append(sym)
                    print(f"[PAPER] Position {sym} fully closed!")

                save_positions()
        except Exception as e:
            print(f"Error checking {sym}: {e}")

    for sym in to_remove:
        del positions[sym]

    if to_remove:
        save_positions()

# -------- Main Loop --------
def main():
    mode = "PAPER" if PAPER_TRADING else "LIVE"
    print(f"=== GridBot Pro Scalper ({mode}) ===")

    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check for TP hits in paper mode
        if PAPER_TRADING and positions:
            check_tp_hits()

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
            if ema_fast > ema_slow and r > 50 and vol_spike:
                if sym not in positions:
                    price = float(client.get_symbol_ticker(symbol=sym)['price'])
                    qty = round(RISK_USDT / price, 6)

                    if execute_buy(sym, qty, price):
                        tps = dynamic_tp(kl)

                        if not PAPER_TRADING:
                            # Place limit sell orders on exchange
                            share = round(qty / len(tps), 6)
                            for tp in tps:
                                client.order_limit_sell(symbol=sym, quantity=share, price=str(tp))

                        positions[sym] = {'qty': qty, 'tps': tps, 'entry': price}
                        save_positions()
                        print(f"[{now}] Bought {sym} qty={qty}, TPs={tps}")
                        signal_found = True
                break

        if not signal_found:
            if PAPER_TRADING:
                print(f"[{now}] No signal | Balance: ${paper_balance:.2f} | Positions: {len(positions)}")
            else:
                print(f"[{now}] No entry signal found.")

        time.sleep(REFRESH_INTERVAL)

if __name__ == "__main__":
    main()

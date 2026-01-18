# GridBot Pro Scalper

Automated grid scalping bot with dynamic ATR-based profit targets and EMA/RSI entry signals.

## 🇺🇸 USA Regulatory Compliant

**MADE FOR US TRADERS - FULLY COMPLIANT**

This bot is specifically designed to meet US regulatory requirements:
- ✅ **SPOT TRADING ONLY** (no futures, no derivatives)
- ✅ **LONG POSITIONS ONLY** (no shorting)
- ✅ **NO LEVERAGE** (100% compliant with US regulations)
- ✅ **US EXCHANGES ONLY** (Binance US)
- ✅ **Regulatory Compliant** for US retail traders

**Hard to find USA-compliant grid bots?** Most grid bots use leverage - this one doesn't!

---

## Features

- **Paper Trading Mode** - Test strategies with $1000 virtual balance before going live
- Auto-updates dependencies on launch
- EMA crossover + RSI + volume spike entry logic
- Dynamic TP levels based on ATR (0.5x, 1x, 1.5x, 2x)
- Position persistence across restarts
- Live Binance.US integration

## Paper Trading Mode

The bot defaults to paper trading mode so you can test without risking real money.

```
==================================================
🧻 PAPER TRADING MODE - NO REAL MONEY AT RISK
   Starting balance: $1000.00 USDT
==================================================
```

**Features:**
- Starts with $1000 virtual USDT
- Simulates buys/sells at real market prices
- Tracks your paper P&L in `paper_trades.json`
- Checks take-profit levels automatically
- No API keys required (uses public price data)

**To switch to live trading:**
```python
PAPER_TRADING = False  # Change this in scanner_pro_scalper.py
```

## Setup

```bash
pip install -r requirements.txt
```

**For paper trading (no API keys needed):**
```bash
python scanner_pro_scalper.py
```

**For live trading:**
```bash
export BINANCE_API_KEY='your_key'
export BINANCE_API_SECRET='your_secret'
# Edit scanner_pro_scalper.py and set PAPER_TRADING = False
python scanner_pro_scalper.py
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `PAPER_TRADING` | `True` | Set to `False` for live trading |
| `REFRESH_INTERVAL` | `10` | Scan frequency in seconds |
| `RISK_USDT` | `20` | Position size per trade |
| `paper_balance` | `1000.0` | Starting paper balance |

## How It Works

1. **Scans** all USDT pairs on Binance US
2. **Entry Signal** triggers when:
   - EMA(5) crosses above EMA(20)
   - RSI > 50 (bullish momentum)
   - Volume spike (2x average)
3. **Places buy** at market price
4. **Sets 4 take-profit levels** based on ATR:
   - TP1: Entry + 0.5x ATR
   - TP2: Entry + 1.0x ATR
   - TP3: Entry + 1.5x ATR
   - TP4: Entry + 2.0x ATR
5. **Sells portions** as each TP is hit

## Files

| File | Purpose |
|------|---------|
| `scanner_pro_scalper.py` | Main bot script |
| `positions.json` | Active positions (persists across restarts) |
| `paper_trades.json` | Paper trading history and balance |
| `.env.example` | Example environment variables |

## ⚠️ Warning

This is a live trading bot - use at your own risk! Always:
- Start with paper trading mode
- Use read-only API keys when possible
- Never invest more than you can afford to lose
- Test thoroughly before going live

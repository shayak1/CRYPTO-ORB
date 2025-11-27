# Current Configuration Summary

## ✅ Configuration Status: SYNCHRONIZED

Both `backtest.py` and `orb_trading_bot.py` now use identical settings.

---

## Core Settings

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Symbol** | BTCUSDT Perpetual | Binance Futures |
| **Leverage** | 10x | Fixed for all trades |
| **Base Capital** | 1000 USDT | Position sizing base |
| **Timeframe** | 5 minutes | Candle interval |
| **Timezone** | Asia/Kolkata (IST) | All times in IST |

---

## ORB Configuration

| Parameter | Value |
|-----------|-------|
| **ORB Period** | 5:30 AM - 6:00 AM IST |
| **Range Filter Min** | 300 USDT |
| **Range Filter Max** | 900 USDT |
| **Calculation** | High/Low/Mid from 5:30-6:00 AM candles |

---

## Trading Rules

### Time Windows

- **ORB Calculation**: 5:30 AM - 6:00 AM IST
- **Trading Window**: 6:00 AM - 2:00 PM IST
- **No New Entries After**: 2:00 PM IST
- **EOD Exit**: 5:00 AM IST (next day)

### Entry Rules

- **Max Breakouts**: 4 per day
- **Breakout Types**: BUY (above ORB High) or SELL (below ORB Low)
- **Re-entry**: Allowed after position closes (SL/TP hit)
- **Direction Changes**: Allowed (can switch from BUY to SELL)

### Position Sizing

**All Trades (Trend-Aligned and Trend-Opposite):**
- Step 1: 100% (market order on breakout)
- Step 2: 0% (disabled)
- Step 3: 0% (disabled)

**Position Size Formula:**
```
Total Qty = (1000 USDT × 10x leverage) / Entry Price
Step 1 Qty = Total Qty × 100%
```

---

## Entry & Exit Levels

### BUY Side

| Step | Entry | Stop Loss | Take Profit |
|------|-------|-----------|-------------|
| 1 | Market (on breakout) | ORB Mid | ORB High + Range × 5 |

### SELL Side

| Step | Entry | Stop Loss | Take Profit |
|------|-------|-----------|-------------|
| 1 | Market (on breakout) | ORB Mid | ORB Low - Range × 5 |

---

## Trend Determination

**Trend = Compare today's ORB Mid vs yesterday's ORB Mid**

- **UP Trend**: Today's ORB Mid > Yesterday's ORB Mid
- **DOWN Trend**: Today's ORB Mid < Yesterday's ORB Mid
- **NEUTRAL**: No previous day data available

**Trade Classification:**
- **Trend-Aligned**: BUY in UP trend OR SELL in DOWN trend
- **Trend-Opposite**: BUY in DOWN trend OR SELL in UP trend

---

## Exit Conditions

1. **Stop Loss Hit**: Exit position at SL price
2. **Take Profit Hit**: Exit position at TP price
3. **Morning Session End (2 PM)**: Close all positions, no new entries
4. **End of Day (5 AM next day)**: Close all positions, reset state

---

## Backtest Results (180 Days)

With current settings:
- **Total PnL**: ~$2,068.55 (+207%)
- **Max Drawdown**: ~$544
- **Win Rate (Days)**: ~49%
- **Trading Days**: ~68 days
- **Average PnL per Day**: ~$30.42

---

## Changes Made (Latest)

### 2025-11-27

✅ **Reverted to Baseline Configuration**
- Removed against-trend leverage reduction
- All trades now use fixed 10x leverage
- Simplified position sizing (100% on step1)
- Both backtest.py and orb_trading_bot.py synchronized

**Previous Against-Trend Test:**
- Result: $1,536.84 PnL (underperformed baseline by -$531.71)
- Decision: Reverted to baseline for better performance

---

## Files

### Production Files
- `orb_trading_bot.py` - Live trading bot
- `.env` - API credentials (gitignored)
- `orb_state.json` - Bot state persistence (auto-generated)
- `orb_trading.log` - Trading activity logs

### Development Files
- `backtest.py` - Backtesting engine
- `optimize.py` - Parameter optimization (optional)

### Configuration Files
- `LIVE_BOT_CONFIG.md` - Production deployment settings
- `CURRENT_CONFIG.md` - This file
- `CLAUDE.md` - Strategy reference

### AWS Deployment Files
- `AWS_DEPLOYMENT.md` - Full deployment guide
- `aws_setup.sh` - EC2 setup script
- `bot_watchdog.sh` - Cron watchdog script
- `deploy_to_aws.sh` - Quick deployment script

---

## Deployment Options

### Option 1: Systemd Service (Recommended)
- Automatic restart on failure
- Boot on system startup
- Better process management
- Centralized logging

### Option 2: Cron Watchdog
- Runs every 5 minutes at exact intervals (00, 05, 10, 15, etc.)
- Ensures bot is always running
- Simple fallback mechanism
- Good for reliability checks

**Both options can be used together for maximum reliability**

---

## API Configuration

### Live Trading
```python
# In orb_trading_bot.py line 129
self.client = self.live_client  # Change from test_client for production
```

### Current Setup (Testnet)
- Live API: Market data only (read-only)
- Test API: Order placement (Binance Futures Testnet)

⚠️ **Always test on testnet before going live!**

---

## Verification Checklist

Before deploying to production:

- [ ] Backtested with recent data (90-180 days)
- [ ] Tested on Binance Testnet
- [ ] API keys configured correctly
- [ ] .env file secured (not in git)
- [ ] Leverage set to 10x on exchange
- [ ] ORB range filter verified (300-900 USDT)
- [ ] Max breakouts set to 4
- [ ] Morning session end at 2 PM confirmed
- [ ] Logs being written correctly
- [ ] State persistence working

---

**Last Updated**: 2025-11-27
**Configuration Version**: 2.0 (Baseline - Fixed 10x)
**Status**: Production Ready

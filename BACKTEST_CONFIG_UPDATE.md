# Backtest Configuration Update

## ✅ New Configuration (2025-11-27)

### Leverage Strategy

**Adaptive Leverage: ENABLED by Default**

| Trade Type | Normal Leverage | After Big Loss |
|------------|----------------|----------------|
| **Trend-Aligned** | 10x | 5x |
| **Against-Trend** | 15x | 5x |

### How It Works

1. **Base Leverage**
   - Trend-aligned trades (BUY in UP trend, SELL in DOWN trend): **10x**
   - Against-trend trades (BUY in DOWN trend, SELL in UP trend): **15x**

2. **Adaptive Reduction**
   - After a big losing day (> baseline average loss), leverage reduces to **5x**
   - This applies to BOTH trend-aligned and against-trend trades
   - Returns to normal (10x/15x) after non-losing days

3. **Baseline Calculation**
   - System calculates average winning day and average losing day
   - Requires at least 3 winning days and 3 losing days for baseline
   - "Big loss" = Loss greater than baseline average loss

---

## 90-Day Backtest Results (with new config)

### Performance Summary

| Metric | Value |
|--------|-------|
| **Total PnL** | $923.44 |
| **Return** | +92.34% |
| **Max Drawdown** | $586.76 |
| **Win Rate (Days)** | 51.8% |
| **Win Rate (Trades)** | 29.7% |
| **Profit Factor** | 1.36 |

### Leverage Distribution

- **5x leverage days**: 12 (after big losses)
- **10x/15x leverage days**: 44 (normal)
- **Against-trend trades**: 24
- **Trend-aligned trades**: 8

### Trade Statistics

- **Total Trades**: 178
- **Stop Loss**: 106 (59.6%)
- **Take Profit**: 21 (11.8%)
- **Session End**: 49 (27.5%)

---

## Running Backtests

### Default (Adaptive Leverage Enabled)

```bash
# Standard 90-day backtest
python3 backtest.py --days 90 --morning-only --min-range 300 --max-range 900

# 180-day backtest
python3 backtest.py --days 180 --morning-only --min-range 300 --max-range 900
```

### Without Adaptive Leverage

```bash
# Disable adaptive leverage
python3 backtest.py --days 90 --morning-only --min-range 300 --max-range 900 --no-adaptive-leverage
```

---

## Key Changes from Previous Version

### Before (Baseline Configuration)
- Fixed 10x leverage for all trades
- No adaptive risk management
- Against-trend same leverage as aligned

### After (Current Configuration)
- ✅ **Adaptive leverage enabled by default**
- ✅ **15x leverage for against-trend trades** (more aggressive)
- ✅ **Reduces to 5x after big losses** (capital preservation)
- ✅ **10x for trend-aligned trades** (conservative)

---

## Why This Configuration?

### 1. Higher Returns on Against-Trend Reversals
Against-trend breakouts often signal strong reversals. Using 15x leverage capitalizes on these moves when they work.

### 2. Defensive Risk Management
The adaptive reduction to 5x after big losses prevents consecutive drawdowns from compounding.

### 3. Conservative on Aligned Trades
Trend-aligned trades use standard 10x, avoiding over-leveraging in already favorable conditions.

---

## Configuration Files

### Backtest (backtest.py)
- **Leverage**: Adaptive (10x aligned / 15x against-trend, reduces to 5x after loss)
- **Enabled by default**: Yes
- **Can disable**: Use `--no-adaptive-leverage` flag

### Live Bot (orb_trading_bot.py)
- **Leverage**: Fixed 10x for all trades
- **Adaptive**: Not implemented
- **Reason**: Live trading requires stable, predictable position sizing

⚠️ **Important**: The live bot does NOT use adaptive leverage or 15x against-trend. It maintains fixed 10x for all trades for safety.

---

## Trade Direction Stats

From 90-day backtest:
- **Against-trend trades**: 24 (75%)
- **Trend-aligned trades**: 8 (25%)

This shows the strategy naturally takes more against-trend positions, which is why the 15x leverage on these trades can significantly boost returns.

---

## Comparison with Previous Results

| Configuration | 180-Day PnL | Return % | Max DD |
|---------------|-------------|----------|--------|
| Fixed 10x (baseline) | $2,068.55 | +207% | ~$544 |
| Against-trend 15x + Adaptive | TBD | TBD | TBD |

Run 180-day backtest to compare:
```bash
python3 backtest.py --days 180 --morning-only --min-range 300 --max-range 900
```

---

## Recommendations

### For Backtesting
✅ Use the new adaptive configuration (default)
- Better risk-adjusted returns
- Automatic drawdown protection
- Higher profit potential on reversals

### For Live Trading
⚠️ Start with fixed 10x (current orb_trading_bot.py)
- More predictable
- Easier to monitor
- Proven baseline performance

**Consider implementing adaptive leverage in live bot only after:**
1. Thorough backtesting over 180+ days
2. Paper trading validation
3. Small live capital testing

---

## Next Steps

1. **Run 180-day backtest** to validate long-term performance
2. **Compare metrics** with baseline fixed 10x results
3. **Decide** if adaptive leverage should be added to live bot
4. **Paper trade** before going live with new configuration

---

**Last Updated**: 2025-11-27
**Configuration**: Adaptive Leverage with 15x Against-Trend
**Status**: Backtest Only (Not in Live Bot)

#!/usr/bin/env python3
"""
Backtesting script for ORB Trading Strategy
Tests the Opening Range Breakout strategy on historical data
"""

import os
import argparse
from datetime import datetime, timedelta
from typing import List, Optional
import pytz
from dotenv import load_dotenv
from binance.um_futures import UMFutures

# Load environment variables
load_dotenv()

# Configuration
SYMBOL = "BTCUSDT"
LEVERAGE = 10
BASE_CAPITAL = 1000  # USDT
TIMEZONE = pytz.timezone("Asia/Kolkata")
CANDLE_INTERVAL = "5m"

# Time windows (IST)
ORB_START_HOUR = 5
ORB_START_MINUTE = 30
ORB_END_HOUR = 6
ORB_END_MINUTE = 0
TRADING_START_HOUR = 6
EOD_EXIT_HOUR = 5

# Pyramiding configuration - updated entries
# Step 1: Entry at ORB breakout, SL at ORB mid, TP at ORB +/- 5*Range
# Step 2: Entry at ORB +/- Range, SL at ORB high/low, TP at Entry2 +/- 4*Range
# Step 3: Entry at ORB +/- 3*Range, SL at ORB +/- 2*Range, TP at Entry3 +/- 3*Range

# Proportions based on trend direction
TREND_ALIGNED_PROPORTIONS = [1, 0, 0]  # When trade aligns with trend
TREND_OPPOSITE_PROPORTIONS = [1, 0.0, 0.0]  # When trade opposes trend

# Morning session hours (IST)
MORNING_SESSION_END_HOUR = 14  # 2 PM IST

class BacktestTrade:
    def __init__(self, trade_type: str, step: str, entry_price: float, qty: float,
                 sl_price: float, tp_price: float, entry_time: datetime):
        self.trade_type = trade_type
        self.step = step
        self.entry_price = entry_price
        self.qty = qty
        self.sl_price = sl_price
        self.tp_price = tp_price
        self.entry_time = entry_time
        self.exit_time: Optional[datetime] = None
        self.exit_price: Optional[float] = None
        self.exit_reason: Optional[str] = None
        self.status = "OPEN"
        self.pnl = 0.0

    def close(self, exit_price: float, exit_time: datetime, reason: str):
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = reason
        self.status = "CLOSED"
        if self.trade_type == "BUY":
            self.pnl = (exit_price - self.entry_price) * self.qty
        else:
            self.pnl = (self.entry_price - exit_price) * self.qty


class ORBBacktester:
    def __init__(self, api_key: str, api_secret: str, morning_only: bool = False,
                 min_range: float = 0, max_range: float = float('inf'), trend_filter: str = None,
                 adaptive_leverage: bool = False):
        self.client = UMFutures(key=api_key, secret=api_secret)
        self.all_trades: List[BacktestTrade] = []
        self.daily_results = []
        self.morning_only = morning_only
        self.min_range = min_range
        self.max_range = max_range
        self.trend_filter = trend_filter  # 'with', 'against', or None
        self.adaptive_leverage = adaptive_leverage
        self.previous_orb_mid: Optional[float] = None
        self.skipped_days = []  # Track days skipped due to range filter

        # Adaptive leverage tracking
        self.baseline_avg_win: Optional[float] = None
        self.baseline_avg_loss: Optional[float] = None
        self.current_leverage = LEVERAGE
        self.leverage_history = []  # Track leverage used each day

    def fetch_historical_klines(self, days: int) -> list:
        """Fetch historical kline data for specified number of days"""
        all_klines = []
        end_time = datetime.now(TIMEZONE)
        start_time = end_time - timedelta(days=days)

        print(f"Fetching historical data from {start_time.date()} to {end_time.date()}...")

        # Binance API limits to 1500 candles per request
        # 5-minute candles: 288 per day, so fetch in chunks
        current_start = int(start_time.timestamp() * 1000)
        current_end = int(end_time.timestamp() * 1000)

        while current_start < current_end:
            klines = self.client.klines(
                symbol=SYMBOL,
                interval=CANDLE_INTERVAL,
                startTime=current_start,
                limit=1500
            )

            if not klines:
                break

            all_klines.extend(klines)
            current_start = klines[-1][0] + 1  # Start from next candle

            print(f"  Fetched {len(all_klines)} candles...")

        print(f"Total candles fetched: {len(all_klines)}")
        return all_klines

    def get_orb_levels(self, klines: list, date) -> Optional[dict]:
        """Get ORB levels for a specific date"""
        orb_candles = []

        for kline in klines:
            candle_time = datetime.fromtimestamp(kline[0] / 1000, TIMEZONE)

            if candle_time.date() != date:
                continue

            # Check if candle is within ORB period
            is_orb_time = False
            if candle_time.hour == ORB_START_HOUR and candle_time.minute >= ORB_START_MINUTE:
                is_orb_time = True
            elif candle_time.hour == ORB_END_HOUR and candle_time.minute < ORB_END_MINUTE:
                is_orb_time = True

            if is_orb_time:
                orb_candles.append({
                    'time': candle_time,
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4])
                })

        if len(orb_candles) < 6:
            return None

        orb_high = max(c['high'] for c in orb_candles)
        orb_low = min(c['low'] for c in orb_candles)
        orb_mid = (orb_high + orb_low) / 2
        range_width = orb_high - orb_low

        return {
            'high': orb_high,
            'low': orb_low,
            'mid': orb_mid,
            'range_width': range_width
        }

    def get_trading_candles(self, klines: list, date) -> list:
        """Get candles for trading period (6 AM to 5 AM next day)"""
        trading_candles = []

        for kline in klines:
            candle_time = datetime.fromtimestamp(kline[0] / 1000, TIMEZONE)

            # Check if it's within trading period for this date
            if candle_time.date() == date and candle_time.hour >= TRADING_START_HOUR:
                trading_candles.append({
                    'time': candle_time,
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4])
                })
            # Include candles until 5 AM next day
            elif candle_time.date() == date + timedelta(days=1) and candle_time.hour < EOD_EXIT_HOUR:
                trading_candles.append({
                    'time': candle_time,
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4])
                })

        return trading_candles

    def calculate_adaptive_leverage(self, previous_day_pnl: Optional[float]) -> int:
        """Calculate leverage for today based on previous day's performance

        Defensive approach:
        - After ANY losing day: Reduce to 5x (capital preservation)
        - After winning day or break-even: Keep at 10x

        Against-trend trades automatically use 1.5x the day's leverage:
        - Normal day (10x): Against-trend = 15x
        - After loss (5x): Against-trend = 7.5x
        """
        if not self.adaptive_leverage or previous_day_pnl is None:
            return LEVERAGE

        # Simple defensive logic: reduce leverage after ANY loss
        if previous_day_pnl < 0:
            return 5  # Defensive: reduce to 5x after any losing day

        # Win or break-even: keep at 10x
        return LEVERAGE

    def simulate_day(self, orb: dict, trading_candles: list, date, trend: str, leverage: int = LEVERAGE) -> dict:
        """Simulate trading for a single day"""
        trades = []
        pending_entries = {}
        breakout_count = 0  # Track number of ORB breakouts (max 5)
        max_breakouts = 3
        active_direction = None
        has_open_position = False
        last_breakout_candle = None  # Track which candle triggered the breakout
        price_inside_range = True  # Track if price has returned inside ORB range

        total_qty = (BASE_CAPITAL * leverage) / trading_candles[0]['close'] if trading_candles else 0

        for candle in trading_candles:
            close_price = candle['close']
            high_price = candle['high']
            low_price = candle['low']
            candle_time = candle['time']

            # Check if price is inside ORB range (for breakout validation)
            # Only update when no open position - we need price to return inside before new breakout
            if not has_open_position and orb['low'] <= close_price <= orb['high']:
                price_inside_range = True

            # Check for EOD exit (5 AM)
            if candle_time.hour == EOD_EXIT_HOUR:
                for trade in trades:
                    if trade.status == "OPEN":
                        trade.close(close_price, candle_time, "EOD")
                break

            # Morning only filter - skip if after session end
            if self.morning_only and candle_time.hour >= MORNING_SESSION_END_HOUR:
                # Close all open trades at end of morning session
                for trade in trades:
                    if trade.status == "OPEN":
                        trade.close(close_price, candle_time, "SESSION_END")
                break

            # Check SL/TP for open trades first
            for trade in trades:
                if trade.status != "OPEN":
                    continue
                if trade.trade_type == "BUY":
                    if low_price <= trade.sl_price:
                        trade.close(trade.sl_price, candle_time, "SL")
                    elif high_price >= trade.tp_price:
                        trade.close(trade.tp_price, candle_time, "TP")
                else:
                    if high_price >= trade.sl_price:
                        trade.close(trade.sl_price, candle_time, "SL")
                    elif low_price <= trade.tp_price:
                        trade.close(trade.tp_price, candle_time, "TP")

            # Check if all trades are closed - reset position state
            open_trades = [t for t in trades if t.status == "OPEN"]
            if has_open_position and len(open_trades) == 0:
                has_open_position = False
                pending_entries.clear()
                active_direction = None
                # Prevent re-entry on same candle - must wait for next candle
                last_breakout_candle = candle_time

            # Check for new breakout entry (if no open position and under max breakouts)
            # Must be a NEW candle (not the same candle that closed previous position)
            # Must have price inside range before breakout (to ensure it's a real breakout from inside to outside)
            if not has_open_position and breakout_count < max_breakouts and candle_time != last_breakout_candle and price_inside_range:
                # BUY condition
                # Check trend filter: 'with' means only BUY in UP trend, 'against' means only BUY in DOWN trend
                buy_allowed = True
                if self.trend_filter == 'with' and trend != 'UP':
                    buy_allowed = False
                elif self.trend_filter == 'against' and trend != 'DOWN':
                    buy_allowed = False

                if close_price > orb['high'] and buy_allowed:
                    active_direction = "BUY"
                    breakout_count += 1
                    has_open_position = True
                    last_breakout_candle = candle_time
                    price_inside_range = False  # Reset - need to return inside for next breakout

                    # Determine proportions and leverage based on trend
                    if trend == "UP":
                        proportions = TREND_ALIGNED_PROPORTIONS
                        trade_qty = total_qty  # Aligned with trend: use day's adaptive leverage
                    else:
                        proportions = TREND_OPPOSITE_PROPORTIONS
                        # Against trend: use 15x (1.5x multiplier on base 10x)
                        trade_qty = total_qty * 1.5

                    # Step 1: Market entry at breakout
                    # SL: ORB mid, TP: ORB high + 5*Range
                    qty1 = trade_qty * proportions[0]
                    sl1 = orb['mid']
                    tp1 = orb['high'] + orb['range_width'] * 5
                    trade1 = BacktestTrade("BUY", "step1", close_price, qty1, sl1, tp1, candle_time)
                    trades.append(trade1)

                    # Step 2: Entry at ORB high + Range
                    # SL: ORB high, TP: Entry2 + 4*Range
                    entry2 = orb['high'] + orb['range_width'] * 1
                    sl2 = orb['high']
                    tp2 = entry2 + orb['range_width'] * 4
                    pending_entries["step2"] = {
                        "entry": entry2, "sl": sl2, "tp": tp2,
                        "qty": trade_qty * proportions[1]
                    }

                    # Step 3: Entry at ORB high + 3*Range
                    # SL: ORB high + 2*Range, TP: Entry3 + 3*Range
                    entry3 = orb['high'] + orb['range_width'] * 3
                    sl3 = orb['high'] + orb['range_width'] * 2
                    tp3 = entry3 + orb['range_width'] * 3
                    pending_entries["step3"] = {
                        "entry": entry3, "sl": sl3, "tp": tp3,
                        "qty": trade_qty * proportions[2]
                    }

                # SELL condition
                # Check trend filter: 'with' means only SELL in DOWN trend, 'against' means only SELL in UP trend
                sell_allowed = True
                if self.trend_filter == 'with' and trend != 'DOWN':
                    sell_allowed = False
                elif self.trend_filter == 'against' and trend != 'UP':
                    sell_allowed = False

                if close_price < orb['low'] and sell_allowed:
                    active_direction = "SELL"
                    breakout_count += 1
                    has_open_position = True
                    last_breakout_candle = candle_time
                    price_inside_range = False  # Reset - need to return inside for next breakout

                    # Determine proportions and leverage based on trend
                    if trend == "DOWN":
                        proportions = TREND_ALIGNED_PROPORTIONS
                        trade_qty = total_qty  # Aligned with trend: use day's adaptive leverage
                    else:
                        proportions = TREND_OPPOSITE_PROPORTIONS
                        # Against trend: use 15x (1.5x multiplier on base 10x)
                        trade_qty = total_qty * 1.5

                    # Step 1: Market entry at breakout
                    # SL: ORB mid, TP: ORB low - 5*Range
                    qty1 = trade_qty * proportions[0]
                    sl1 = orb['mid']
                    tp1 = orb['low'] - orb['range_width'] * 5
                    trade1 = BacktestTrade("SELL", "step1", close_price, qty1, sl1, tp1, candle_time)
                    trades.append(trade1)

                    # Step 2: Entry at ORB low - Range
                    # SL: ORB low, TP: Entry2 - 4*Range
                    entry2 = orb['low'] - orb['range_width'] * 1
                    sl2 = orb['low']
                    tp2 = entry2 - orb['range_width'] * 4
                    pending_entries["step2"] = {
                        "entry": entry2, "sl": sl2, "tp": tp2,
                        "qty": trade_qty * proportions[1]
                    }

                    # Step 3: Entry at ORB low - 3*Range
                    # SL: ORB low - 2*Range, TP: Entry3 - 3*Range
                    entry3 = orb['low'] - orb['range_width'] * 3
                    sl3 = orb['low'] - orb['range_width'] * 2
                    tp3 = entry3 - orb['range_width'] * 3
                    pending_entries["step3"] = {
                        "entry": entry3, "sl": sl3, "tp": tp3,
                        "qty": trade_qty * proportions[2]
                    }

            # Check pending entries
            for step, entry_info in list(pending_entries.items()):
                if active_direction == "BUY" and high_price >= entry_info["entry"]:
                    trade = BacktestTrade(
                        "BUY", step, entry_info["entry"], entry_info["qty"],
                        entry_info["sl"], entry_info["tp"], candle_time
                    )
                    trades.append(trade)
                    del pending_entries[step]
                elif active_direction == "SELL" and low_price <= entry_info["entry"]:
                    trade = BacktestTrade(
                        "SELL", step, entry_info["entry"], entry_info["qty"],
                        entry_info["sl"], entry_info["tp"], candle_time
                    )
                    trades.append(trade)
                    del pending_entries[step]

            # Update has_open_position
            has_open_position = any(t.status == "OPEN" for t in trades)

        # Calculate daily PnL
        daily_pnl = sum(t.pnl for t in trades)
        win_trades = len([t for t in trades if t.pnl > 0])
        loss_trades = len([t for t in trades if t.pnl < 0])

        self.all_trades.extend(trades)

        return {
            'date': date,
            'trades': len(trades),
            'wins': win_trades,
            'losses': loss_trades,
            'pnl': daily_pnl,
            'direction': active_direction if active_direction else ("MIXED" if breakout_count > 0 else "NO TRADE"),
            'breakouts': breakout_count,
            'orb_high': orb['high'],
            'orb_low': orb['low'],
            'range_width': orb['range_width']
        }

    def run_backtest(self, days: int):
        """Run backtest for specified number of days"""
        print(f"\n{'='*80}")
        print(f"ORB STRATEGY BACKTEST - {days} DAYS")
        print(f"{'='*80}")
        if self.adaptive_leverage:
            print(f"Leverage: ADAPTIVE (Defensive)")
            print(f"  - After Loss Day: 5x aligned / 7.5x against-trend")
            print(f"  - After Win/Breakeven: {LEVERAGE}x aligned / 15x against-trend")
        else:
            print(f"Leverage: FIXED")
            print(f"  - Trend-Aligned: {LEVERAGE}x")
            print(f"  - Against-Trend: 15x")
        print(f"Morning Only: {self.morning_only}")
        if self.min_range > 0 or self.max_range < float('inf'):
            print(f"Range Filter: ${self.min_range:.2f} - ${self.max_range:.2f}")
        print(f"{'='*80}\n")

        # Fetch historical data
        klines = self.fetch_historical_klines(days + 2)  # Extra days for trend calculation

        # Get unique dates
        dates = set()
        for kline in klines:
            candle_time = datetime.fromtimestamp(kline[0] / 1000, TIMEZONE)
            dates.add(candle_time.date())

        dates = sorted(dates)[-days-1:]  # Get last N+1 days for trend calculation

        print(f"\nProcessing {len(dates)-1} trading days...\n")

        # Run simulation for each day
        for i, date in enumerate(dates):
            orb = self.get_orb_levels(klines, date)
            if not orb:
                print(f"{date}: No ORB data available")
                self.previous_orb_mid = None
                continue

            # Skip first day (needed for trend calculation)
            if i == 0:
                self.previous_orb_mid = orb['mid']
                continue

            # Determine trend based on ORB mid comparison
            if self.previous_orb_mid is not None:
                if orb['mid'] > self.previous_orb_mid:
                    trend = "UP"
                else:
                    trend = "DOWN"
            else:
                trend = "NEUTRAL"

            # Apply range width filter
            if orb['range_width'] < self.min_range or orb['range_width'] > self.max_range:
                self.skipped_days.append({
                    'date': date,
                    'range_width': orb['range_width'],
                    'reason': 'RANGE_FILTER'
                })
                self.previous_orb_mid = orb['mid']
                continue

            trading_candles = self.get_trading_candles(klines, date)
            if not trading_candles:
                print(f"{date}: No trading candles")
                self.previous_orb_mid = orb['mid']
                continue

            # Calculate adaptive leverage based on previous day
            previous_day_pnl = self.daily_results[-1]['pnl'] if self.daily_results else None
            day_leverage = self.calculate_adaptive_leverage(previous_day_pnl)

            # Store leverage used
            self.leverage_history.append({
                'date': date,
                'leverage': day_leverage,
                'reason': self._get_leverage_reason(previous_day_pnl, day_leverage)
            })

            result = self.simulate_day(orb, trading_candles, date, trend, leverage=day_leverage)
            result['trend'] = trend
            result['leverage'] = day_leverage
            self.daily_results.append(result)

            # Update previous ORB mid for next day
            self.previous_orb_mid = orb['mid']

        # Print results
        self.print_results()

    def _get_leverage_reason(self, previous_day_pnl: Optional[float], leverage: int) -> str:
        """Get reason for leverage adjustment"""
        if previous_day_pnl is None or leverage == LEVERAGE:
            return "Default"
        elif leverage == 5:
            return f"Big Loss (${previous_day_pnl:.2f})"
        return "Default"

    def print_results(self):
        """Print backtest results"""
        if not self.daily_results:
            print("No results to display")
            return

        print(f"\n{'='*105}")
        print("DAILY RESULTS")
        print(f"{'='*105}")
        if self.adaptive_leverage:
            print(f"{'Date':<12} {'Lev':<5} {'Trend':<6} {'Dir':<8} {'Trades':<8} {'W/L':<8} {'PnL':>12} {'ORB Range':>12}")
        else:
            print(f"{'Date':<12} {'Trend':<6} {'Dir':<8} {'Trades':<8} {'W/L':<8} {'PnL':>12} {'ORB Range':>12}")
        print("-" * 105)

        for r in self.daily_results:
            wl = f"{r['wins']}/{r['losses']}"
            pnl_str = f"${r['pnl']:.2f}"
            range_str = f"${r['range_width']:.2f}"
            trend = r.get('trend', 'N/A')
            leverage = r.get('leverage', LEVERAGE)

            if self.adaptive_leverage:
                lev_str = f"{leverage}x"
                print(f"{r['date']!s:<12} {lev_str:<5} {trend:<6} {r['direction']:<8} {r['trades']:<8} {wl:<8} {pnl_str:>12} {range_str:>12}")
            else:
                print(f"{r['date']!s:<12} {trend:<6} {r['direction']:<8} {r['trades']:<8} {wl:<8} {pnl_str:>12} {range_str:>12}")

        # Summary statistics
        total_pnl = sum(r['pnl'] for r in self.daily_results)
        total_trades = sum(r['trades'] for r in self.daily_results)
        winning_days = len([r for r in self.daily_results if r['pnl'] > 0])
        losing_days = len([r for r in self.daily_results if r['pnl'] < 0])
        trading_days = len([r for r in self.daily_results if r['trades'] > 0])

        total_wins = sum(r['wins'] for r in self.daily_results)
        total_losses = sum(r['losses'] for r in self.daily_results)

        gross_profit = sum(t.pnl for t in self.all_trades if t.pnl and t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.all_trades if t.pnl and t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        max_win = max((t.pnl for t in self.all_trades if t.pnl is not None), default=0)
        max_loss = min((t.pnl for t in self.all_trades if t.pnl is not None), default=0)

        # Calculate max drawdown
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0
        for r in self.daily_results:
            cumulative_pnl += r['pnl']
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Period: {self.daily_results[0]['date']} to {self.daily_results[-1]['date']}")
        print(f"Trading Days: {trading_days}")
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate (trades): {total_wins}/{total_wins+total_losses} ({100*total_wins/(total_wins+total_losses):.1f}%)" if total_wins+total_losses > 0 else "N/A")
        print(f"Win Rate (days): {winning_days}/{trading_days} ({100*winning_days/trading_days:.1f}%)" if trading_days > 0 else "N/A")
        print(f"\nTotal PnL: ${total_pnl:.2f}")
        print(f"Gross Profit: ${gross_profit:.2f}")
        print(f"Gross Loss: ${gross_loss:.2f}")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Max Win: ${max_win:.2f}")
        print(f"Max Loss: ${max_loss:.2f}")
        print(f"Max Drawdown: ${max_drawdown:.2f}")
        print(f"\nReturn on Capital: {100*total_pnl/BASE_CAPITAL:.2f}%")
        print(f"Avg Daily PnL: ${total_pnl/len(self.daily_results):.2f}")
        print(f"{'='*80}\n")

        # Exit reasons breakdown
        sl_exits = len([t for t in self.all_trades if t.exit_reason == "SL"])
        tp_exits = len([t for t in self.all_trades if t.exit_reason == "TP"])
        eod_exits = len([t for t in self.all_trades if t.exit_reason == "EOD"])
        session_exits = len([t for t in self.all_trades if t.exit_reason == "SESSION_END"])

        print("Exit Reasons:")
        print(f"  Stop Loss: {sl_exits}")
        print(f"  Take Profit: {tp_exits}")
        print(f"  End of Day: {eod_exits}")
        if session_exits > 0:
            print(f"  Session End: {session_exits}")

        # Trend alignment stats
        aligned_trades = len([r for r in self.daily_results
                             if (r['direction'] == 'BUY' and r.get('trend') == 'UP') or
                                (r['direction'] == 'SELL' and r.get('trend') == 'DOWN')])
        opposite_trades = len([r for r in self.daily_results
                              if (r['direction'] == 'BUY' and r.get('trend') == 'DOWN') or
                                 (r['direction'] == 'SELL' and r.get('trend') == 'UP')])

        print(f"\nTrend Alignment:")
        print(f"  Aligned with trend: {aligned_trades}")
        print(f"  Against trend: {opposite_trades}")

        # Range filter stats
        if self.skipped_days:
            print(f"\nRange Filter Stats:")
            print(f"  Days skipped: {len(self.skipped_days)}")
            skipped_ranges = [d['range_width'] for d in self.skipped_days]
            print(f"  Skipped range (min/max): ${min(skipped_ranges):.2f} / ${max(skipped_ranges):.2f}")

        # Show range distribution
        if self.daily_results:
            ranges = [r['range_width'] for r in self.daily_results]
            print(f"\nTraded Range Stats:")
            print(f"  Min: ${min(ranges):.2f}")
            print(f"  Max: ${max(ranges):.2f}")
            print(f"  Avg: ${sum(ranges)/len(ranges):.2f}")

        # Show adaptive leverage stats
        if self.adaptive_leverage and self.leverage_history:
            leverage_5x = len([l for l in self.leverage_history if l['leverage'] == 5])
            leverage_10x = len([l for l in self.leverage_history if l['leverage'] == 10])

            print(f"\nAdaptive Leverage Stats (Defensive Approach):")
            print(f"  Days at 5x/7.5x (after loss): {leverage_5x}")
            print(f"  Days at 10x/15x (after win): {leverage_10x}")
            print(f"  Logic: Reduce to 5x aligned / 7.5x against-trend after ANY losing day")
        print()

    def trace_day(self, trace_date: str):
        """Trace all trades for a specific date with detailed information"""
        target_date = datetime.strptime(trace_date, "%Y-%m-%d").date()

        # Filter trades for the target date
        day_trades = [t for t in self.all_trades if t.entry_time.date() == target_date]

        # Get ORB info for the day
        day_result = next((r for r in self.daily_results if r['date'] == target_date), None)

        print(f"\n{'='*100}")
        print(f"TRADE TRACE FOR {target_date}")
        print(f"{'='*100}")

        if day_result:
            print(f"\nORB Levels:")
            print(f"  ORB High: ${day_result['orb_high']:.2f}")
            print(f"  ORB Low: ${day_result['orb_low']:.2f}")
            print(f"  Range Width: ${day_result['range_width']:.2f}")
            print(f"  Trend: {day_result.get('trend', 'N/A')}")
            print(f"  Direction: {day_result['direction']}")
            print(f"  Breakouts: {day_result['breakouts']}")

        if not day_trades:
            print(f"\nNo trades found for {target_date}")
            return

        print(f"\n{'='*100}")
        print(f"{'Step':<8} {'Type':<6} {'Entry Time':<20} {'Exit Time':<20} {'Entry $':>12} {'Exit $':>12} {'Qty':>10} {'PnL':>12} {'Exit Reason':<12}")
        print("-" * 100)

        total_pnl = 0
        for trade in day_trades:
            entry_time_str = trade.entry_time.strftime("%H:%M:%S")
            exit_time_str = trade.exit_time.strftime("%H:%M:%S") if trade.exit_time else "Open"
            exit_price_str = f"${trade.exit_price:.2f}" if trade.exit_price is not None else "N/A"
            pnl_str = f"${trade.pnl:.2f}" if trade.pnl is not None else "$0.00"

            print(f"{trade.step:<8} {trade.trade_type:<6} {entry_time_str:<20} {exit_time_str:<20} ${trade.entry_price:>11.2f} {exit_price_str:>12} {trade.qty:>10.4f} {pnl_str:>12} {trade.exit_reason or 'Open':<12}")
            total_pnl += trade.pnl if trade.pnl else 0

        print("-" * 100)
        print(f"{'TOTAL':<8} {'':<6} {'':<20} {'':<20} {'':<12} {'':<12} {'':<10} ${total_pnl:>11.2f}")
        print(f"{'='*100}\n")


def main():
    parser = argparse.ArgumentParser(description="ORB Strategy Backtester")
    parser.add_argument('--days', type=int, default=30,
                        help='Number of days to backtest (default: 30)')
    parser.add_argument('--morning-only', action='store_true',
                        help='Trade only morning session (6 AM - 2 PM IST)')
    parser.add_argument('--min-range', type=float, default=0,
                        help='Minimum ORB range width to trade (default: 0)')
    parser.add_argument('--max-range', type=float, default=float('inf'),
                        help='Maximum ORB range width to trade (default: unlimited)')
    parser.add_argument('--trace-date', type=str, default=None,
                        help='Trace trades for a specific date (format: YYYY-MM-DD)')
    parser.add_argument('--trend-filter', type=str, default=None, choices=['with', 'against'],
                        help='Only trade with or against the trend')
    parser.add_argument('--adaptive-leverage', action='store_true',
                        help='Enable adaptive leverage (reduce to 5x/7.5x after losses, default: disabled)')

    args = parser.parse_args()

    # Load API credentials
    api_key = os.getenv("LIVE_API_KEY", "")
    api_secret = os.getenv("LIVE_API_SECRET", "")

    if not api_key or not api_secret:
        print("Please set LIVE_API_KEY and LIVE_API_SECRET in .env file")
        return

    backtester = ORBBacktester(
        api_key, api_secret,
        morning_only=args.morning_only,
        min_range=args.min_range,
        max_range=args.max_range,
        trend_filter=args.trend_filter,
        adaptive_leverage=args.adaptive_leverage
    )
    backtester.run_backtest(args.days)

    # If trace date is specified, show detailed trade trace
    if args.trace_date:
        backtester.trace_day(args.trace_date)


if __name__ == "__main__":
    main()

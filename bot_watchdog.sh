#!/bin/bash
# ORB Trading Bot Watchdog Script
# Runs every 5 minutes to ensure bot is active
# Place in /home/ubuntu/orb-trading-bot/bot_watchdog.sh

APP_DIR="/home/ubuntu/orb-trading-bot"
PID_FILE="$APP_DIR/orb_bot.pid"
LOG_FILE="$APP_DIR/watchdog.log"
PYTHON_BIN="$APP_DIR/venv/bin/python3"
BOT_SCRIPT="$APP_DIR/orb_trading_bot.py"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> $LOG_FILE
}

cd $APP_DIR

# Check if bot is running
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null 2>&1; then
        log "Bot is running (PID: $PID)"
        exit 0
    else
        log "Stale PID file found, removing..."
        rm -f $PID_FILE
    fi
fi

# Bot is not running, start it
log "Bot is not running, starting..."
cd $APP_DIR
source venv/bin/activate
nohup $PYTHON_BIN $BOT_SCRIPT start >> $LOG_FILE 2>&1 &

# Wait a moment and verify it started
sleep 3
if [ -f "$PID_FILE" ]; then
    NEW_PID=$(cat $PID_FILE)
    if ps -p $NEW_PID > /dev/null 2>&1; then
        log "Bot started successfully (PID: $NEW_PID)"
    else
        log "ERROR: Bot failed to start"
    fi
else
    log "ERROR: PID file not created, bot may have failed to start"
fi

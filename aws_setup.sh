#!/bin/bash
# AWS EC2 Setup Script for ORB Trading Bot
# Run this script on a fresh Ubuntu 22.04 LTS instance

set -e  # Exit on error

echo "========================================="
echo "ORB Trading Bot - AWS Setup"
echo "========================================="

# Update system packages
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3 and pip
echo "Installing Python 3 and dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv

# Install git (if needed)
sudo apt-get install -y git

# Create application directory
echo "Creating application directory..."
APP_DIR="/home/ubuntu/orb-trading-bot"
mkdir -p $APP_DIR
cd $APP_DIR

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install --upgrade pip
pip install binance-futures-connector>=4.1.0
pip install pytz>=2025.2
pip install python-dotenv>=1.2.1

# Create .env file template (you need to fill this with your API keys)
echo "Creating .env file template..."
cat > .env << 'EOF'
# Binance API Keys
# LIVE keys for market data (read-only recommended)
LIVE_API_KEY=your_live_api_key_here
LIVE_API_SECRET=your_live_api_secret_here

# TEST keys for order placement (Binance Testnet)
TEST_API_KEY=your_test_api_key_here
TEST_API_SECRET=your_test_api_secret_here

# For production trading, use LIVE keys for both data and orders
# Make sure to update orb_trading_bot.py to use live_client for trading
EOF

echo ""
echo "========================================="
echo "IMPORTANT: Edit .env file with your API keys"
echo "========================================="
echo "Run: nano $APP_DIR/.env"
echo ""

# Create systemd service file
echo "Creating systemd service..."
sudo tee /etc/systemd/system/orb-bot.service > /dev/null << EOF
[Unit]
Description=ORB Trading Bot for BTC/USDT
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python3 $APP_DIR/orb_trading_bot.py start
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/orb-bot.log
StandardError=append:/var/log/orb-bot-error.log

[Install]
WantedBy=multi-user.target
EOF

# Create log files with proper permissions
sudo touch /var/log/orb-bot.log
sudo touch /var/log/orb-bot-error.log
sudo chown ubuntu:ubuntu /var/log/orb-bot.log
sudo chown ubuntu:ubuntu /var/log/orb-bot-error.log

# Reload systemd
sudo systemctl daemon-reload

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next Steps:"
echo "1. Copy your trading bot files to: $APP_DIR"
echo "   - orb_trading_bot.py"
echo "   - requirements.txt (optional)"
echo ""
echo "2. Edit .env file with your API keys:"
echo "   nano $APP_DIR/.env"
echo ""
echo "3. Test the bot manually:"
echo "   cd $APP_DIR"
echo "   source venv/bin/activate"
echo "   python3 orb_trading_bot.py status"
echo ""
echo "4. Start the bot as a service:"
echo "   sudo systemctl start orb-bot"
echo ""
echo "5. Enable auto-start on boot:"
echo "   sudo systemctl enable orb-bot"
echo ""
echo "6. Check bot status:"
echo "   sudo systemctl status orb-bot"
echo ""
echo "7. View logs:"
echo "   tail -f /var/log/orb-bot.log"
echo "   tail -f orb_trading.log"
echo ""
echo "========================================="

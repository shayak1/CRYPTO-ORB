# AWS Deployment Guide for ORB Trading Bot

## Prerequisites

- AWS EC2 instance (Ubuntu 22.04 LTS recommended)
- Instance Type: t3.small or larger (2GB+ RAM)
- Security Group: Allow SSH (port 22)
- Binance API Keys (Live for data, Test for orders)

---

## Quick Deployment

### Step 1: Launch EC2 Instance

1. Launch Ubuntu 22.04 LTS instance on AWS
2. Choose instance type: `t3.small` or `t3.medium`
3. Configure security group (SSH access)
4. Download your SSH key pair

### Step 2: Connect to EC2

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### Step 3: Upload Files to EC2

On your **local machine**, run:

```bash
# Create deployment package
cd "/Users/tradershaven/Desktop/BTC trade"

# Copy files to EC2
scp -i your-key.pem orb_trading_bot.py ubuntu@your-ec2-ip:/home/ubuntu/
scp -i your-key.pem aws_setup.sh ubuntu@your-ec2-ip:/home/ubuntu/
scp -i your-key.pem bot_watchdog.sh ubuntu@your-ec2-ip:/home/ubuntu/
scp -i your-key.pem .env ubuntu@your-ec2-ip:/home/ubuntu/
```

### Step 4: Run Setup Script

On **EC2 instance**:

```bash
cd /home/ubuntu
chmod +x aws_setup.sh
./aws_setup.sh
```

### Step 5: Move Files to App Directory

```bash
mv orb_trading_bot.py /home/ubuntu/orb-trading-bot/
mv bot_watchdog.sh /home/ubuntu/orb-trading-bot/
mv .env /home/ubuntu/orb-trading-bot/
cd /home/ubuntu/orb-trading-bot
chmod +x bot_watchdog.sh
```

### Step 6: Configure API Keys

```bash
nano /home/ubuntu/orb-trading-bot/.env
```

Update with your Binance API keys:
```
LIVE_API_KEY=your_actual_live_api_key
LIVE_API_SECRET=your_actual_live_api_secret
TEST_API_KEY=your_actual_test_api_key
TEST_API_SECRET=your_actual_test_api_secret
```

Save (Ctrl+O, Enter) and exit (Ctrl+X).

---

## Running the Bot

### Option 1: Using Systemd (Recommended)

**Advantages**: Automatic restart on failure, boot on startup, better process management

```bash
# Start the bot
sudo systemctl start orb-bot

# Enable auto-start on boot
sudo systemctl enable orb-bot

# Check status
sudo systemctl status orb-bot

# Stop the bot
sudo systemctl stop orb-bot

# View logs
tail -f /var/log/orb-bot.log
tail -f /home/ubuntu/orb-trading-bot/orb_trading.log
```

### Option 2: Using Cron Watchdog

**Advantages**: Runs at exact 5-minute intervals, ensures bot is always alive

**Setup Cron:**

```bash
# Edit crontab
crontab -e

# Add this line (runs every 5 minutes at :00, :05, :10, :15, etc.)
*/5 * * * * /home/ubuntu/orb-trading-bot/bot_watchdog.sh
```

**View watchdog logs:**
```bash
tail -f /home/ubuntu/orb-trading-bot/watchdog.log
```

---

## Bot Management Commands

### Manual Control

```bash
cd /home/ubuntu/orb-trading-bot
source venv/bin/activate

# Start bot
python3 orb_trading_bot.py start

# Stop bot
python3 orb_trading_bot.py stop

# Check status
python3 orb_trading_bot.py status

# Restart bot
python3 orb_trading_bot.py restart
```

---

## Monitoring

### View Real-time Logs

```bash
# Bot trading logs
tail -f /home/ubuntu/orb-trading-bot/orb_trading.log

# System service logs
sudo journalctl -u orb-bot -f

# Watchdog logs (if using cron)
tail -f /home/ubuntu/orb-trading-bot/watchdog.log
```

### Check Bot State

```bash
cat /home/ubuntu/orb-trading-bot/orb_state.json
```

### Monitor System Resources

```bash
# CPU and memory usage
htop

# Install htop if not available
sudo apt-get install htop
```

---

## Maintenance

### Update Bot Code

```bash
# On EC2, stop the bot first
sudo systemctl stop orb-bot
# OR
cd /home/ubuntu/orb-trading-bot && python3 orb_trading_bot.py stop

# Upload new version from local machine
scp -i your-key.pem orb_trading_bot.py ubuntu@your-ec2-ip:/home/ubuntu/orb-trading-bot/

# Start bot again
sudo systemctl start orb-bot
```

### Backup Trading Data

```bash
# Backup state file and logs
cd /home/ubuntu/orb-trading-bot
tar -czf backup-$(date +%Y%m%d).tar.gz orb_state.json orb_trading.log

# Download backup to local machine
scp -i your-key.pem ubuntu@your-ec2-ip:/home/ubuntu/orb-trading-bot/backup-*.tar.gz .
```

### Log Rotation

Create log rotation config:

```bash
sudo nano /etc/logrotate.d/orb-bot
```

Add:
```
/home/ubuntu/orb-trading-bot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 ubuntu ubuntu
    sharedscripts
}

/var/log/orb-bot*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 ubuntu ubuntu
}
```

---

## Troubleshooting

### Bot Won't Start

```bash
# Check for errors in logs
tail -50 /var/log/orb-bot-error.log
tail -50 /home/ubuntu/orb-trading-bot/orb_trading.log

# Check if PID file is stale
rm -f /home/ubuntu/orb-trading-bot/orb_bot.pid

# Check Python environment
cd /home/ubuntu/orb-trading-bot
source venv/bin/activate
python3 orb_trading_bot.py status
```

### API Connection Issues

```bash
# Test API connectivity
cd /home/ubuntu/orb-trading-bot
source venv/bin/activate
python3 -c "from binance.um_futures import UMFutures; import os; from dotenv import load_dotenv; load_dotenv(); c = UMFutures(key=os.getenv('LIVE_API_KEY'), secret=os.getenv('LIVE_API_SECRET')); print(c.ping())"
```

### Bot Crashes After Deploy

```bash
# Check systemd logs
sudo journalctl -u orb-bot -n 100 --no-pager

# Check for missing dependencies
cd /home/ubuntu/orb-trading-bot
source venv/bin/activate
pip list
```

---

## Security Best Practices

1. **API Keys**: Use read-only keys for live data, testnet keys for orders
2. **Firewall**: Configure EC2 security group to only allow SSH from your IP
3. **SSH**: Disable password authentication, use key-based auth only
4. **Updates**: Regularly update system packages
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

5. **Monitoring**: Set up CloudWatch alerts for CPU/memory usage

---

## Cost Optimization

### EC2 Instance Recommendations

| Instance Type | vCPUs | RAM | Monthly Cost (approx) | Use Case |
|---------------|-------|-----|----------------------|----------|
| t3.micro | 2 | 1GB | $7.50 | Testing only |
| t3.small | 2 | 2GB | $15 | Production (Recommended) |
| t3.medium | 2 | 4GB | $30 | High-frequency trading |

### Use Reserved Instances

Save up to 70% by purchasing 1-year or 3-year reserved instances for production.

---

## Trading Schedule

The bot automatically follows IST timezone schedule:

- **5:30 AM - 6:00 AM**: ORB calculation period (no trading)
- **6:00 AM - 2:00 PM**: Active trading window
  - Max 4 breakouts per day
  - ORB range filter: 300-900 USDT
  - 10x leverage
  - Re-entry allowed after position closes
- **2:00 PM - 5:00 AM next day**: Monitoring only (no new entries)
- **5:00 AM next day**: EOD exit, all positions closed, state reset

---

## Performance Monitoring

### Expected Resource Usage

- **CPU**: 5-10% average
- **Memory**: 100-200 MB
- **Disk I/O**: Minimal (logs + state file)
- **Network**: Low (API calls every 10 seconds)

### Alert Setup (Optional)

Configure AWS CloudWatch to alert you if:
- CPU > 50% for 5 minutes (possible issue)
- Instance becomes unreachable
- Disk usage > 80%

---

## FAQ

**Q: Should I use systemd or cron?**
A: Use **systemd** for simplicity and automatic restarts. Use **cron watchdog** if you want guaranteed checks every 5 minutes.

**Q: Can I run multiple bots on one instance?**
A: Yes, create separate directories and systemd services for each bot.

**Q: How do I switch from testnet to live trading?**
A: Update `orb_trading_bot.py` line 129 to use `live_client` instead of `test_client` for trading operations. ⚠️ **Test thoroughly on testnet first!**

**Q: What if EC2 instance restarts?**
A: If using `systemctl enable orb-bot`, the bot will auto-start on boot. State is persisted in `orb_state.json`.

---

## Support

- Check logs: `/var/log/orb-bot.log` and `orb_trading.log`
- Review state: `cat orb_state.json`
- Test connectivity: Verify API keys and network access to Binance

**Last Updated**: 2025-11-27

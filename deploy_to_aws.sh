#!/bin/bash
# Quick deployment script for ORB Trading Bot to AWS EC2
# Usage: ./deploy_to_aws.sh your-key.pem ec2-user@your-ec2-ip

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

if [ "$#" -ne 2 ]; then
    echo -e "${RED}Usage: $0 <path-to-key.pem> <user@ec2-ip>${NC}"
    echo "Example: $0 ~/my-key.pem ubuntu@1.2.3.4"
    exit 1
fi

SSH_KEY=$1
EC2_HOST=$2

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}ORB Trading Bot - AWS Deployment${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

# Verify files exist
echo -e "${YELLOW}Checking required files...${NC}"
REQUIRED_FILES=(
    "orb_trading_bot.py"
    "aws_setup.sh"
    "bot_watchdog.sh"
    ".env"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}ERROR: $file not found!${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} $file"
done

echo ""
echo -e "${YELLOW}Uploading files to EC2...${NC}"

# Upload files
scp -i $SSH_KEY orb_trading_bot.py $EC2_HOST:/home/ubuntu/
scp -i $SSH_KEY aws_setup.sh $EC2_HOST:/home/ubuntu/
scp -i $SSH_KEY bot_watchdog.sh $EC2_HOST:/home/ubuntu/
scp -i $SSH_KEY .env $EC2_HOST:/home/ubuntu/

echo -e "${GREEN}✓ Files uploaded successfully${NC}"
echo ""

# Run setup on EC2
echo -e "${YELLOW}Running setup on EC2...${NC}"
ssh -i $SSH_KEY $EC2_HOST << 'ENDSSH'
cd /home/ubuntu
chmod +x aws_setup.sh
./aws_setup.sh
ENDSSH

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. SSH into EC2:"
echo "   ssh -i $SSH_KEY $EC2_HOST"
echo ""
echo "2. Move files and configure:"
echo "   cd /home/ubuntu/orb-trading-bot"
echo "   nano .env  # Update your API keys"
echo ""
echo "3. Start the bot:"
echo "   sudo systemctl start orb-bot"
echo "   sudo systemctl enable orb-bot"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status orb-bot"
echo "   tail -f orb_trading.log"
echo ""
echo -e "${GREEN}See AWS_DEPLOYMENT.md for full documentation${NC}"

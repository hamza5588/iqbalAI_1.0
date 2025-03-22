#!/bin/bash
set -e

# Colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting deployment process...${NC}"

# Update system packages
echo -e "${GREEN}Updating system packages...${NC}"
apt-get update && apt-get upgrade -y

# Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo -e "${GREEN}Installing Docker...${NC}"
    apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get install -y docker-ce
fi

# Install Docker Compose if not installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}Installing Docker Compose...${NC}"
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Install Certbot for SSL certificates
if ! command -v certbot &> /dev/null; then
    echo -e "${GREEN}Installing Certbot...${NC}"
    apt-get install -y certbot python3-certbot-nginx
fi

# Create app directory if it doesn't exist
APP_DIR="/opt/flask-app"
if [ ! -d "$APP_DIR" ]; then
    echo -e "${GREEN}Creating application directory...${NC}"
    mkdir -p $APP_DIR
fi

# Create SSL directory if it doesn't exist
SSL_DIR="/etc/nginx/ssl"
if [ ! -d "$SSL_DIR" ]; then
    echo -e "${GREEN}Creating SSL directory...${NC}"
    mkdir -p $SSL_DIR
fi

# Move to app directory
cd $APP_DIR

# Pull latest code if git repository exists, otherwise prompt for files
if [ -d ".git" ]; then
    echo -e "${GREEN}Pulling latest code from git...${NC}"
    git pull
else
    echo -e "${YELLOW}No git repository found. Please make sure your application files are in ${APP_DIR}${NC}"
    echo -e "${YELLOW}Required files: docker-compose.yml, Dockerfile, Dockerfile.nginx, nginx.conf, requirements.txt, run.py and your Flask application code${NC}"
    read -p "Press enter to continue once files are in place..."
fi

# Ensure static directory exists
mkdir -p $APP_DIR/static

# Set proper permissions
echo -e "${GREEN}Setting proper permissions...${NC}"
chmod +x $APP_DIR/run.py

# Check if SSL certificates exist
if [ ! -f "$SSL_DIR/iqbalai.com.crt" ] || [ ! -f "$SSL_DIR/iqbalai.com.key" ]; then
    echo -e "${YELLOW}SSL certificates not found. Obtaining new certificates...${NC}"
    certbot certonly --standalone -d iqbalai.com -d www.iqbalai.com --non-interactive --agree-tos --email your-email@example.com
    
    # Copy certificates to the correct location
    cp /etc/letsencrypt/live/iqbalai.com/fullchain.pem $SSL_DIR/iqbalai.com.crt
    cp /etc/letsencrypt/live/iqbalai.com/privkey.pem $SSL_DIR/iqbalai.com.key
    
    # Set proper permissions
    chmod 600 $SSL_DIR/iqbalai.com.key
    chmod 644 $SSL_DIR/iqbalai.com.crt
fi

# Configure firewall
echo -e "${GREEN}Configuring firewall...${NC}"
ufw allow 80
ufw allow 443
ufw allow 22

# Build and start the containers
echo -e "${GREEN}Building and starting containers...${NC}"
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check if containers are running
echo -e "${GREEN}Checking container status...${NC}"
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}Deployment successful! Application is running.${NC}"
    echo -e "${GREEN}You can access your application at:${NC}"
    echo -e "${GREEN}https://iqbalai.com${NC}"
    echo -e "${GREEN}https://www.iqbalai.com${NC}"
else
    echo -e "${RED}Deployment failed. Containers are not running properly.${NC}"
    echo -e "${YELLOW}Check logs with: docker-compose logs${NC}"
fi

# Set up automatic SSL renewal
echo -e "${GREEN}Setting up automatic SSL renewal...${NC}"
(crontab -l 2>/dev/null | grep -v "certbot renew") | crontab -
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -

echo -e "${YELLOW}Deployment process completed.${NC}"


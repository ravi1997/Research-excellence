#!/bin/bash

# Deployment script for Research Excellence Portal

set -e

echo "Starting deployment of Research Excellence Portal..."

# Check if we're running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

# Create application directory
APP_DIR="/opt/research-excellence"
echo "Creating application directory at $APP_DIR..."
mkdir -p $APP_DIR

# Copy application files
echo "Copying application files..."
cp -r . $APP_DIR/

# Change to application directory
cd $APP_DIR

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install

# Build CSS
echo "Building CSS assets..."
npm run build-css

# Set permissions
echo "Setting permissions..."
chown -R www-data:www-data $APP_DIR
chmod +x $APP_DIR/deploy.sh

# Copy systemd service file
echo "Installing systemd service..."
cp $APP_DIR/research-excellence.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable research-excellence.service

# Start the service
echo "Starting the application..."
systemctl start research-excellence.service

echo "Deployment completed successfully!"
echo "The application is now running and will start automatically on boot."
echo "You can check the status with: systemctl status research-excellence.service"
#!/bin/bash

# Update script for Research Excellence Portal

set -e

echo "Starting update of Research Excellence Portal..."

# Check if we're running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

# Application directory
APP_DIR="/opt/research-excellence"

# Check if application is installed
if [ ! -d "$APP_DIR" ]; then
  echo "Application not found at $APP_DIR. Please run deploy.sh first."
  exit 1
fi

# Stop the service
echo "Stopping the application..."
systemctl stop research-excellence.service

# Backup current version
echo "Creating backup..."
BACKUP_DIR="/opt/research-excellence-backup-$(date +%Y%m%d-%H%M%S)"
cp -r $APP_DIR $BACKUP_DIR

# Update application files
echo "Updating application files..."
cd $APP_DIR
git pull origin main  # Assuming you're using git for deployment

# Activate virtual environment
source venv/bin/activate

# Update Python dependencies
echo "Updating Python dependencies..."
pip install -r requirements.txt

# Update Node.js dependencies
echo "Updating Node.js dependencies..."
npm install

# Build CSS
echo "Building CSS assets..."
npm run build-css

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Set permissions
echo "Setting permissions..."
chown -R www-data:www-data $APP_DIR

# Start the service
echo "Starting the application..."
systemctl start research-excellence.service

echo "Update completed successfully!"
echo "Backup created at: $BACKUP_DIR"
#!/bin/bash
set -e

# Deployment script for Planning Engine on Ubuntu VM
# Run this script from the repo directory after pulling latest changes
# Usage: sudo bash deploy/deploy.sh

APP_DIR="/opt/planning-engine"
DATA_DIR="/var/lib/planning-engine"
USER="planning-engine"
VENV_DIR="$APP_DIR/venv"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================="
echo "Planning Engine - Deployment"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Verify we're in the repo directory
if [ ! -f "$REPO_DIR/pyproject.toml" ]; then
    echo "ERROR: Must run from planning-engine repository directory"
    exit 1
fi

echo "✓ Deploying from: $REPO_DIR"

# Check if repo is at the expected location
if [ "$REPO_DIR" = "$APP_DIR/repo" ]; then
    echo "✓ Deploying from cloned repository at $APP_DIR/repo"
    # No need to sync, we'll work directly from the repo
    WORK_DIR="$APP_DIR/repo"
else
    echo "ERROR: Script must be run from $APP_DIR/repo"
    exit 1
fi

# Stop services before updating
echo "✓ Stopping services..."
systemctl stop planning-engine-api || true
systemctl stop planning-engine-web || true

# Ensure data directory exists and is linked
mkdir -p "$DATA_DIR/workspace"
if [ ! -L "$WORK_DIR/data" ]; then
    ln -sf "$DATA_DIR" "$WORK_DIR/data"
fi

# Set ownership
chown -R "$USER:$USER" "$WORK_DIR"
chown -R "$USER:$USER" "$DATA_DIR"

# Setup Python virtual environment
echo "✓ Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    sudo -u "$USER" python3 -m venv "$VENV_DIR"
fi

# Install/update Python dependencies
echo "✓ Installing Python dependencies..."
sudo -u "$USER" "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u "$USER" "$VENV_DIR/bin/pip" install -e "$WORK_DIR"

# Build Vue.js frontend
echo "✓ Building Vue.js frontend..."
cd "$WORK_DIR/apps/web"
sudo -u "$USER" npm install
sudo -u "$USER" npm run build

# Install systemd service files
echo "✓ Installing systemd services..."
cp "$WORK_DIR/deploy/systemd/planning-engine-api.service" /etc/systemd/system/
cp "$WORK_DIR/deploy/systemd/planning-engine-web.service" /etc/systemd/system/

# Install nginx configuration
echo "✓ Installing nginx configuration..."
cp "$WORK_DIR/deploy/nginx/planning-engine.conf" /etc/nginx/sites-available/planning-engine
ln -sf /etc/nginx/sites-available/planning-engine /etc/nginx/sites-enabled/planning-engine

# Test nginx configuration
echo "✓ Testing nginx configuration..."
nginx -t

# Reload systemd and restart services
echo "✓ Restarting services..."
systemctl daemon-reload
systemctl enable planning-engine-api
systemctl enable planning-engine-web
systemctl restart planning-engine-api
systemctl restart planning-engine-web
systemctl reload nginx

# Wait a moment for services to start
sleep 2

# Check service status
echo ""
echo "=========================================="
echo "Service Status"
echo "=========================================="
systemctl status planning-engine-api --no-pager || true
echo ""
systemctl status planning-engine-web --no-pager || true

echo ""
echo "=========================================="
echo "Deployment completed successfully!"
echo "=========================================="
echo ""
echo "Access the application:"
echo "  Web Interface: http://YOUR_VM_IP/"
echo "  API Docs: http://YOUR_VM_IP/api/docs"
echo ""
echo "Useful commands:"
echo "  Check API status:  sudo systemctl status planning-engine-api"
echo "  Check Web status:  sudo systemctl status planning-engine-web"
echo "  View API logs:     sudo journalctl -u planning-engine-api -f"
echo "  View Web logs:     sudo journalctl -u planning-engine-web -f"
echo "  Restart API:       sudo systemctl restart planning-engine-api"
echo "  Restart Web:       sudo systemctl restart planning-engine-web"
echo ""

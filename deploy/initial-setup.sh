#!/bin/bash
set -e

# Initial Setup Script for Planning Engine on Ubuntu VM
# Run this ONCE on the VM to set up the environment
# Usage: sudo bash initial-setup.sh

APP_DIR="/opt/planning-engine"
DATA_DIR="/var/lib/planning-engine"
USER="planning-engine"

echo "=========================================="
echo "Planning Engine - Initial Setup"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Create application user if it doesn't exist
if ! id "$USER" &>/dev/null; then
    echo "✓ Creating application user: $USER"
    useradd -r -s /bin/bash -d "$APP_DIR" -m "$USER"
else
    echo "✓ User $USER already exists"
fi

# Create directories
echo "✓ Creating application directories..."
mkdir -p "$APP_DIR"
mkdir -p "$DATA_DIR/workspace"
mkdir -p /var/log/planning-engine

# Set ownership
chown -R "$USER:$USER" "$APP_DIR"
chown -R "$USER:$USER" "$DATA_DIR"
chown -R "$USER:$USER" /var/log/planning-engine

# Install system dependencies
echo "✓ Installing system dependencies..."
apt-get update
apt-get install -y python3-pip python3-venv nodejs npm nginx git rsync

# Create symlink for data directory in app directory
ln -sf "$DATA_DIR" "$APP_DIR/data"

echo ""
echo "=========================================="
echo "Initial setup completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Clone the repository:"
echo "   sudo -u $USER git clone https://github.com/YOUR_USERNAME/planning-engine.git $APP_DIR/repo"
echo ""
echo "2. Run the deployment script:"
echo "   cd $APP_DIR/repo && sudo bash deploy/deploy.sh"
echo ""

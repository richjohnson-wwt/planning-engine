#!/bin/bash
set -e

# Quick Update Script for Planning Engine
# This pulls latest changes and redeploys
# Usage: sudo bash update.sh

REPO_DIR="/opt/planning-engine/repo"
USER="planning-engine"

echo "=========================================="
echo "Planning Engine - Quick Update"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Check if repo exists
if [ ! -d "$REPO_DIR" ]; then
    echo "ERROR: Repository not found at $REPO_DIR"
    echo "Please run initial setup first"
    exit 1
fi

# Pull latest changes
echo "✓ Pulling latest changes from GitHub..."
cd "$REPO_DIR"
sudo -u "$USER" git fetch origin
sudo -u "$USER" git pull origin main

# Run deployment script
echo "✓ Running deployment script..."
bash "$REPO_DIR/deploy/deploy.sh"

# Planning Engine - VM Deployment Guide

This guide covers deploying the Planning Engine application to your Ubuntu VM in OpenShift.

## Architecture

- **Backend**: FastAPI running on port 8000 (systemd service)
- **Frontend**: Vue.js/Vite preview server on port 3000 (systemd service)
- **Reverse Proxy**: Nginx on port 80
  - `/` → Frontend (port 3000)
  - `/api/` → Backend (port 8000)

## Prerequisites

- Ubuntu VM with Python 3.12+ and Node.js
- SSH access via `ssh route-planning`
- Root/sudo access on the VM
- Company VPN connection

## Initial Setup (First Time Only)

1. **SSH into the VM:**
   ```bash
   ssh route-planning
   ```

2. **Run the initial setup script:**
   ```bash
   # Download and run the setup script
   curl -o /tmp/initial-setup.sh https://raw.githubusercontent.com/YOUR_USERNAME/planning-engine/main/deploy/initial-setup.sh
   sudo bash /tmp/initial-setup.sh
   ```

   Or manually:
   ```bash
   # Create user and directories
   sudo useradd -r -s /bin/bash -d /opt/planning-engine -m planning-engine
   sudo mkdir -p /var/lib/planning-engine/workspace
   sudo chown -R planning-engine:planning-engine /opt/planning-engine /var/lib/planning-engine
   
   # Install dependencies
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-venv nodejs npm nginx git rsync
   ```

3. **Clone the repository:**
   ```bash
   sudo -u planning-engine git clone https://github.com/YOUR_USERNAME/planning-engine.git /opt/planning-engine/repo
   ```

4. **Run the deployment script:**
   ```bash
   cd /opt/planning-engine/repo
   sudo bash deploy/deploy.sh
   ```

## Regular Deployments (Updates)

When you want to deploy new changes:

1. **SSH into the VM:**
   ```bash
   ssh route-planning
   ```

2. **Pull latest changes and deploy:**
   ```bash
   cd /opt/planning-engine/repo
   sudo -u planning-engine git pull origin main
   sudo bash deploy/deploy.sh
   ```

   Or use the quick update script:
   ```bash
   sudo bash /opt/planning-engine/repo/deploy/update.sh
   ```

## Service Management

### Check Service Status
```bash
sudo systemctl status planning-engine-api
sudo systemctl status planning-engine-web
sudo systemctl status nginx
```

### View Logs
```bash
# API logs
sudo journalctl -u planning-engine-api -f

# Web logs
sudo journalctl -u planning-engine-web -f

# Nginx logs
sudo tail -f /var/log/nginx/planning-engine-access.log
sudo tail -f /var/log/nginx/planning-engine-error.log
```

### Restart Services
```bash
sudo systemctl restart planning-engine-api
sudo systemctl restart planning-engine-web
sudo systemctl reload nginx
```

### Stop Services
```bash
sudo systemctl stop planning-engine-api
sudo systemctl stop planning-engine-web
```

## File Locations

- **Application**: `/opt/planning-engine/`
- **Repository**: `/opt/planning-engine/repo/`
- **Data/Workspaces**: `/var/lib/planning-engine/workspace/`
- **Python venv**: `/opt/planning-engine/venv/`
- **Logs**: 
  - Systemd: `journalctl -u planning-engine-api` or `-u planning-engine-web`
  - Nginx: `/var/log/nginx/planning-engine-*.log`

## Accessing the Application

Once deployed, access the application at:
- **Web Interface**: `http://YOUR_VM_IP/`
- **API Documentation**: `http://YOUR_VM_IP/api/docs`

## Troubleshooting

### Services won't start
```bash
# Check service status and logs
sudo systemctl status planning-engine-api
sudo journalctl -u planning-engine-api -n 50

# Check if ports are in use
sudo netstat -tlnp | grep -E ':(80|3000|8000)'
```

### Nginx configuration errors
```bash
# Test nginx config
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Python dependency issues
```bash
# Reinstall dependencies
cd /opt/planning-engine
sudo -u planning-engine /opt/planning-engine/venv/bin/pip install --upgrade pip
sudo -u planning-engine /opt/planning-engine/venv/bin/pip install -e .
```

### Frontend build issues
```bash
# Rebuild frontend
cd /opt/planning-engine/apps/web
sudo -u planning-engine npm install
sudo -u planning-engine npm run build
```

## Data Persistence

Workspace data is stored in `/var/lib/planning-engine/workspace/` and persists across deployments. This includes:
- Parsed Excel files
- Geocoding cache
- Cluster data
- Route planning outputs

## Security Notes

- The application runs as the `planning-engine` user (non-root)
- Data directory is separate from application code
- Nginx handles all external traffic
- Services auto-restart on failure

## Uninstalling

To completely remove the application:

```bash
# Stop and disable services
sudo systemctl stop planning-engine-api planning-engine-web
sudo systemctl disable planning-engine-api planning-engine-web
sudo rm /etc/systemd/system/planning-engine-*.service
sudo systemctl daemon-reload

# Remove nginx config
sudo rm /etc/nginx/sites-enabled/planning-engine
sudo rm /etc/nginx/sites-available/planning-engine
sudo systemctl reload nginx

# Remove application files (WARNING: This deletes all data!)
sudo rm -rf /opt/planning-engine
sudo rm -rf /var/lib/planning-engine

# Remove user
sudo userdel planning-engine
```

### Output from console on deploy:

```
==========================================
Deployment completed successfully!
==========================================

Access the application:
  Web Interface: http://10.254.181.18/
  API Docs: http://10.254.181.18/api/docs

Useful commands:
  Check API status:  sudo systemctl status planning-engine-api
  Check Web status:  sudo systemctl status planning-engine-web
  View API logs:     sudo journalctl -u planning-engine-api -f
  View Web logs:     sudo journalctl -u planning-engine-web -f
  Restart API:       sudo systemctl restart planning-engine-api
  Restart Web:       sudo systemctl restart planning-engine-web
```

    http://10.254.181.18:3000/

    ubuntu@route-planning:/opt/planning-engine/repo$

    ubuntu@route-planning:/opt/planning-engine/repo$ ls data/workspace/
foo

### Deploy steps

    ssh route-planning
   cd /opt/planning-engine/repo
   sudo bash deploy/update.sh
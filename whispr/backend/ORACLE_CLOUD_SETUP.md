# Oracle Cloud Free Tier Setup Guide
**Complete guide to deploy your SPX ATR Level Tracking system on Oracle Cloud**

## 🎯 **Step 1: Create Oracle Cloud Account**

1. **Go to**: https://www.oracle.com/cloud/free/
2. **Click**: "Start for free"
3. **Fill out**: Account details (use real info - they verify)
4. **Credit Card**: Required for verification (won't be charged)
5. **Verification**: Phone + email verification
6. **Wait**: 5-15 minutes for account activation

## 🖥️ **Step 2: Create ARM64 Instance (Always Free)**

### Instance Configuration:
1. **Navigate**: Compute → Instances → Create Instance
2. **Name**: `spx-atr-tracker`
3. **Image**: 
   - Click "Change Image"
   - Select **Ubuntu 22.04 (Canonical)**
   - Architecture: **Arm-based**
4. **Shape**: 
   - Click "Change Shape"
   - Select **VM.Standard.A1.Flex**
   - **4 OCPUs, 24GB RAM** (maximum free tier)
5. **Networking**: Keep defaults (creates new VCN)
6. **SSH Keys**:
   - Generate new key pair OR upload your existing `~/.ssh/id_rsa.pub`
   - **SAVE THE PRIVATE KEY** - you'll need it to connect

### Security List Setup:
1. **Go to**: Networking → Virtual Cloud Networks → Your VCN → Security Lists
2. **Add Ingress Rules**:
   ```
   Port 22 (SSH): 0.0.0.0/0
   Port 8000 (API): 0.0.0.0/0  
   Port 3000 (UI): 0.0.0.0/0
   ```

## 🔑 **Step 3: Connect to Your Instance**

### Get Instance IP:
1. **Compute** → **Instances** → Your instance
2. **Copy** the **Public IP Address**

### SSH Connection:
```bash
# If you generated new keys, use the downloaded private key
chmod 600 ~/Downloads/ssh-key-XXXX.key
ssh -i ~/Downloads/ssh-key-XXXX.key ubuntu@YOUR_PUBLIC_IP

# If using existing keys
ssh ubuntu@YOUR_PUBLIC_IP
```

## 🐍 **Step 4: Server Setup**

### Install Dependencies:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install -y python3.11 python3.11-pip python3.11-venv git curl

# Install Node.js (for UI)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2 for process management
sudo npm install -g pm2

# Install SQLite (for database)
sudo apt install -y sqlite3

# Install system dependencies for Python packages
sudo apt install -y build-essential libssl-dev libffi-dev python3.11-dev
```

### Create Application Directory:
```bash
# Create app directory
sudo mkdir -p /opt/spx-atr
sudo chown ubuntu:ubuntu /opt/spx-atr
cd /opt/spx-atr

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.11+
```

## 📁 **Step 5: Deploy Your Code**

### Option A: Git Clone (Recommended)
```bash
cd /opt/spx-atr
git clone https://github.com/your-username/tradingATR.ai.git .
```

### Option B: File Transfer (if no Git)
```bash
# From your local machine:
scp -r -i ~/path/to/key whispr/ ubuntu@YOUR_PUBLIC_IP:/opt/spx-atr/
```

### Install Python Dependencies:
```bash
cd /opt/spx-atr/whispr/backend
source /opt/spx-atr/venv/bin/activate
pip install -r requirements.txt

# If missing aiohttp, install it
pip install aiohttp aiosqlite pandas requests
```

## 🔐 **Step 6: Setup Environment & Credentials**

### Create Environment File:
```bash
cd /opt/spx-atr/whispr/backend
nano .env
```

### Add Your Credentials:
```env
# Schwab API Credentials
SCHWAB_CLIENT_ID=aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1
SCHWAB_CLIENT_SECRET=0dG11fLY8qF7iYz3
SCHWAB_REDIRECT_URI=https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback

# Database
DATABASE_PATH=/opt/spx-atr/data/spx_tracking.db

# Logging
LOG_LEVEL=INFO
```

### Create Data Directory:
```bash
sudo mkdir -p /opt/spx-atr/data
sudo chown ubuntu:ubuntu /opt/spx-atr/data
```

### Transfer Schwab Tokens:
```bash
# From your local machine (copy your working tokens):
scp -i ~/path/to/key ~/.schwab_tokens.json ubuntu@YOUR_PUBLIC_IP:/home/ubuntu/
```

## 🚀 **Step 7: Create Production Deployment**

### Create Production Runner Script:
```bash
cd /opt/spx-atr/whispr/backend
nano start_production.py
```

### Production Script Content:
```python
#!/usr/bin/env python3
"""
Production SPX ATR Level Tracking Server
Runs continuously and logs all level hits to database.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/spx-atr/logs/spx_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import our system
from atr_system import get_atr_system

class ProductionTracker:
    def __init__(self):
        self.running = True
        self.system = None
        
    async def start(self):
        """Start the production tracking system"""
        logger.info("🚀 Starting SPX ATR Production Tracker...")
        
        try:
            self.system = await get_atr_system()
            logger.info("✅ ATR System initialized")
            
            # Start processing
            hit_count = 0
            async for hit in self.system.start_real_time_processing():
                hit_count += 1
                logger.info(f"🎯 LEVEL HIT #{hit_count}: {hit.timeframe} {hit.level_name} @ ${hit.current_price:.2f}")
                
                if not self.running:
                    break
                    
        except Exception as e:
            logger.error(f"❌ Production tracker error: {e}")
            raise
            
    def stop(self):
        """Stop the tracker gracefully"""
        logger.info("🛑 Stopping production tracker...")
        self.running = False

# Global tracker instance
tracker = ProductionTracker()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"📡 Received signal {signum}")
    tracker.stop()

if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create logs directory
    Path("/opt/spx-atr/logs").mkdir(exist_ok=True)
    
    # Start the tracker
    try:
        asyncio.run(tracker.start())
    except KeyboardInterrupt:
        logger.info("🛑 Tracker stopped by user")
    except Exception as e:
        logger.error(f"❌ Tracker failed: {e}")
        sys.exit(1)
```

### Make Script Executable:
```bash
chmod +x start_production.py
```

## 📊 **Step 8: Setup Process Management with PM2**

### Create PM2 Configuration:
```bash
cd /opt/spx-atr/whispr/backend
nano ecosystem.config.js
```

### PM2 Config Content:
```javascript
module.exports = {
  apps: [{
    name: 'spx-atr-tracker',
    script: '/opt/spx-atr/venv/bin/python',
    args: '/opt/spx-atr/whispr/backend/start_production.py',
    cwd: '/opt/spx-atr/whispr/backend',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      PYTHONPATH: '/opt/spx-atr/whispr/backend',
      NODE_ENV: 'production'
    },
    log_file: '/opt/spx-atr/logs/pm2.log',
    out_file: '/opt/spx-atr/logs/pm2-out.log',
    error_file: '/opt/spx-atr/logs/pm2-error.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
```

### Start with PM2:
```bash
# Create logs directory
mkdir -p /opt/spx-atr/logs

# Start the application
pm2 start ecosystem.config.js

# Setup auto-startup
pm2 startup
pm2 save

# Monitor
pm2 status
pm2 logs spx-atr-tracker
```

## 🔍 **Step 9: Test Your Deployment**

### Test Connection:
```bash
cd /opt/spx-atr/whispr/backend
source /opt/spx-atr/venv/bin/activate
python -c "
import asyncio
from atr_system import get_spx_system_status

async def test():
    status = await get_spx_system_status()
    print(f'System Status: {status}')

asyncio.run(test())
"
```

### Check Logs:
```bash
# PM2 logs
pm2 logs spx-atr-tracker

# Application logs
tail -f /opt/spx-atr/logs/spx_tracker.log

# Database verification
sqlite3 /opt/spx-atr/data/spx_tracking.db "SELECT COUNT(*) FROM level_hits;"
```

## 🎯 **Step 10: Monitoring & Maintenance**

### Useful Commands:
```bash
# Check system status
pm2 status

# Restart application
pm2 restart spx-atr-tracker

# View real-time logs
pm2 logs spx-atr-tracker --lines 100

# Check database size
du -sh /opt/spx-atr/data/spx_tracking.db

# System resources
htop
```

### Setup Log Rotation:
```bash
sudo nano /etc/logrotate.d/spx-atr
```

### Log Rotation Config:
```
/opt/spx-atr/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        pm2 reload spx-atr-tracker
    endscript
}
```

## 🔒 **Security Notes**

1. **Change SSH Port** (optional):
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Change Port 22 to Port 2222
   sudo systemctl restart ssh
   ```

2. **Setup Firewall**:
   ```bash
   sudo ufw enable
   sudo ufw allow 22/tcp
   sudo ufw allow 8000/tcp
   sudo ufw allow 3000/tcp
   ```

3. **Keep System Updated**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## 🎉 **Success!**

Your SPX ATR tracking system is now running 24/7 on Oracle Cloud Free Tier!

- **Real-time**: Level hits logged to database
- **Persistent**: Survives reboots with PM2
- **Monitored**: Logs and process management
- **Free**: Forever (Oracle Free Tier)

### Next Steps:
- Setup API endpoints for data access
- Create monitoring dashboard
- Setup alerts for specific level hits

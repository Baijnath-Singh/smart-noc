# Phase 0: Environment Setup

**Duration**: 1 day  
**Difficulty**: Easy  
**Goal**: Prepare your Windows 11 laptop for smart NOC development

---

## 📋 What You'll Set Up

- ✅ WSL2 with Ubuntu 22.04
- ✅ Docker Desktop
- ✅ Development tools (Python, Go, Node.js)
- ✅ VS Code with extensions
- ✅ Git configuration

---

## 🔧 Step-by-Step Instructions

### Step 1: Install WSL2

Open PowerShell as Administrator:

```powershell
# Enable WSL
wsl --install

# Set WSL2 as default
wsl --set-default-version 2

# Install Ubuntu 22.04
wsl --install -d Ubuntu-22.04

# Restart computer if prompted
```

After restart, launch Ubuntu from Start menu and create username/password.

**Verify**:
```bash
wsl -l -v
# Should show Ubuntu-22.04 with Version 2
```

---

### Step 2: Install Docker Desktop

1. Download from: https://www.docker.com/products/docker-desktop/
2. Run installer
3. During installation:
   - ✅ Enable WSL2 backend
   - ✅ Add shortcut to desktop
4. Restart computer
5. Launch Docker Desktop
6. Go to Settings → Resources → WSL Integration
   - ✅ Enable integration with Ubuntu-22.04

**Verify**:
```bash
# In WSL Ubuntu terminal
docker --version
docker compose version
docker ps
# Should run without errors
```

---

### Step 3: Install Development Tools in WSL

Open Ubuntu terminal:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
    build-essential \
    curl \
    wget \
    git \
    vim \
    jq \
    net-tools \
    htop

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip
python3 --version

# Install Go 1.21
wget https://go.dev/dl/go1.21.9.linux-amd64.tar.gz
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go1.21.9.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
go version

# Install Node.js 20 (for UI tools)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node --version
npm --version
```

---

### Step 4: Install VS Code Extensions

Install VS Code on Windows, then add these extensions:

**Essential**:
- WSL (Microsoft) - Work with WSL
- Docker (Microsoft) - Docker support
- Python (Microsoft) - Python development
- Go (Google) - Go development

**Recommended**:
- YAML (Red Hat) - For configs
- Markdown All in One - Documentation
- REST Client - API testing
- Remote - SSH - SSH support

**To connect VS Code to WSL**:
1. Click green icon (bottom-left corner)
2. Select "Connect to WSL"
3. Open folder: `/home/<username>/smart-noc`

---

### Step 5: Clone Project and Set Up

```bash
# Create working directory
cd ~
mkdir -p ng-iam
cd ng-iam

# If you already have the project on Windows, access it via:
# cd /mnt/c/Users/baisingh/ng-iam/smart-noc

# Or clone fresh (if using Git)
# git clone <your-repo> smart-noc

cd smart-noc

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies (we'll add more later)
pip install --upgrade pip
pip install \
    kafka-python \
    requests \
    pyyaml \
    python-dotenv \
    loguru
```

---

### Step 6: Test Docker Setup

Create a test compose file:

```bash
# Create test file
cat > docker-compose.test.yml << 'EOF'
version: '3.8'

services:
  test-container:
    image: hello-world

EOF

# Test Docker Compose
docker compose -f docker-compose.test.yml up

# Should see "Hello from Docker!"

# Clean up
docker compose -f docker-compose.test.yml down
rm docker-compose.test.yml
```

---

### Step 7: Configure Git (Optional but Recommended)

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global init.defaultBranch main

# Save credentials
git config --global credential.helper store
```

---

### Step 8: Set Resource Limits

For laptop performance, configure Docker Desktop:

**Docker Desktop → Settings → Resources**:
- Memory: 8GB (or 50% of your RAM)
- CPUs: 4 cores (or 50% of your cores)
- Swap: 2GB
- Disk image size: 60GB

**WSL memory limit** (`C:\Users\baisingh\.wslconfig`):
```ini
[wsl2]
memory=12GB
processors=6
swap=4GB
```

Restart WSL:
```powershell
wsl --shutdown
```

---

## 🎯 Verification Checklist

Run this verification script:

```bash
cat > /tmp/verify-setup.sh << 'EOF'
#!/bin/bash

echo "🔍 Smart NOC Setup Verification"
echo "================================"

# Check WSL
echo -n "WSL2: "
wsl.exe -l -v | grep -i ubuntu && echo "✅" || echo "❌"

# Check Docker
echo -n "Docker: "
docker --version > /dev/null 2>&1 && echo "✅" || echo "❌"

# Check Docker Compose
echo -n "Docker Compose: "
docker compose version > /dev/null 2>&1 && echo "✅" || echo "❌"

# Check Python
echo -n "Python 3.11+: "
python3 --version | grep -E "3\.(11|12)" && echo "✅" || echo "❌"

# Check Go
echo -n "Go 1.21+: "
go version | grep -E "go1\.2[1-9]" && echo "✅" || echo "❌"

# Check Node
echo -n "Node.js: "
node --version > /dev/null 2>&1 && echo "✅" || echo "❌"

# Check Git
echo -n "Git: "
git --version > /dev/null 2>&1 && echo "✅" || echo "❌"

echo ""
echo "🎉 If all show ✅, you're ready for Phase 1!"

EOF

chmod +x /tmp/verify-setup.sh
bash /tmp/verify-setup.sh
```

---

## 📊 Expected Resource Usage

**Idle state** (just Docker running):
- RAM: ~2GB
- CPU: <5%
- Disk: ~10GB

**Phase 1 running** (Kafka + log generator):
- RAM: ~4-5GB
- CPU: 10-20%
- Disk: ~15GB

**Full system** (all agents):
- RAM: ~8-10GB
- CPU: 20-40%
- Disk: ~25GB

---

## 🐛 Troubleshooting

### Docker not starting in WSL
```bash
# Check Docker daemon
sudo service docker status

# Start if not running
sudo service docker start

# Or use Docker Desktop integration (recommended)
```

### WSL slow or unresponsive
```bash
# Restart WSL from PowerShell
wsl --shutdown

# Wait 10 seconds, then restart Ubuntu
```

### Python package installation errors
```bash
# Install Python dev headers
sudo apt install python3.11-dev python3.11-distutils

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### Port conflicts
```bash
# Check what's using a port (e.g., 9092 for Kafka)
sudo netstat -tulpn | grep 9092

# Or use lsof
sudo lsof -i :9092
```

---

## 🎓 Learning Resources

Before moving to Phase 1, familiarize yourself with:

1. **Docker Basics** (30 min):
   - https://www.youtube.com/watch?v=pg19Z8LL06w

2. **WSL2 Tips** (15 min):
   - https://learn.microsoft.com/en-us/windows/wsl/

3. **Terminal Basics** (if needed):
   - https://ubuntu.com/tutorials/command-line-for-beginners

---

## ✅ Completion Criteria

You're ready for Phase 1 when:

- ✅ All verification checks pass
- ✅ Docker Desktop shows "Running"
- ✅ VS Code can connect to WSL
- ✅ You can run `docker ps` without errors
- ✅ Python virtual environment activates

---

## 🚀 Next Step

**→ [Phase 1: Log Pipeline](PHASE-1-LOG-PIPELINE.md)**

Time to build the log ingestion system!

# Smart NOC - Setup & Operations Guide

**Version:** 1.0  
**Last Updated:** April 25, 2026  
**Target Audience:** NOC Team Members (All Skill Levels)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Starting the NOC](#starting-the-noc)
5. [Verifying the System](#verifying-the-system)
6. [Stopping the NOC](#stopping-the-noc)
7. [Troubleshooting](#troubleshooting)
8. [Architecture Overview](#architecture-overview)
9. [FAQ](#faq)

---

## 🎯 Overview

**Smart NOC** is an AI-powered Network Operations Center that automatically:
- **Ingests** network device logs
- **Detects** anomalies using machine learning
- **Correlates** events into incidents
- **Diagnoses** root causes using Large Language Models (LLM)
- **Recommends** remediation steps

### What You'll Learn
- How to start/stop the entire NOC system
- How to verify everything is working
- How to troubleshoot common issues
- Basic operations and monitoring

---

## 🔧 Prerequisites

### Required Software

| Software | Version | Download Link | Purpose |
|----------|---------|---------------|---------|
| **Docker Desktop** | Latest | [Get Docker](https://www.docker.com/products/docker-desktop/) | Runs all services in containers |
| **Python** | 3.9 - 3.12 | [Get Python](https://www.python.org/downloads/) | Log generator and testing tools |
| **WSL 2** | Latest | Run: `wsl --install` | Linux compatibility layer |
| **PowerShell** | 5.1+ | Pre-installed on Windows | Automation scripts |

### System Requirements

- **OS:** Windows 10/11 (64-bit)
- **RAM:** 8 GB minimum, 16 GB recommended
- **Disk:** 20 GB free space
- **CPU:** 4 cores minimum
- **Internet:** Required for LLM API access

### Verification Checklist

**For WSL/Bash Users:**

```bash
# Check Docker
docker --version
# Expected: Docker version 20.x or higher

# Check Docker is running
docker ps
# Expected: No errors (empty list is OK)

# Check Python
python3 --version
# Expected: Python 3.9.x or higher

# Check WSL
wsl --version
# Expected: WSL version info
```

**For PowerShell Users:**

```powershell
# Check Docker
docker --version
# Expected: Docker version 20.x or higher

# Check Docker is running
docker ps
# Expected: No errors (empty list is OK)

# Check Python
python --version
# Expected: Python 3.9.x or higher

# Check WSL
wsl --version
# Expected: WSL version info
```

**✅ If all commands work, you're ready to proceed!**

---

## 🚀 Initial Setup

### Step 1: Get the Code

**WSL/Bash:**
```bash
cd /mnt/c/Users/<YourUsername>/ng-iam/smart-noc
```

**PowerShell:**
```powershell
cd C:\Users\<YourUsername>\ng-iam\smart-noc
```

**Replace `<YourUsername>` with your actual Windows username.**

### Step 2: Configure Environment

**WSL/Bash:**

1. **Check if `.env` file exists:**
   ```bash
   ls -la .env
   ```

2. **If it doesn't exist, create it:**
   ```bash
   cp .env.example .env
   ```

3. **Edit the `.env` file:**
   ```bash
   nano .env  # or: vim .env
   ```

**PowerShell:**

1. **Check if `.env` file exists:**
   ```powershell
   Get-Item .env
   ```

2. **If it doesn't exist, create it:**
   ```powershell
   Copy-Item .env.example .env
   ```

3. **Edit the `.env` file:**
   ```powershell
   notepad .env
   ```

### Step 3: Configure Critical Settings

**REQUIRED: Update these values (same for both platforms):**
   ```env
   # GitHub Models API (Free Tier)
   LLM_API_KEY=github_pat_YOUR_TOKEN_HERE
   LLM_API_BASE=https://models.inference.ai.azure.com
   LLM_MODEL=gpt-4o-mini
   
   # Database Password (change from default)
   POSTGRES_PASSWORD=your_secure_password_here
   ```

   **How to get GitHub Models API key:**
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `read:user`, `read:org`
   - Copy token and paste into `LLM_API_KEY`

**Save and close** the file (Ctrl+X for nano, Ctrl+S for notepad)

### Step 4: Verify Configuration

**WSL/Bash:**
```bash
# Check configuration is valid
grep "LLM_API_KEY" .env
grep "POSTGRES_PASSWORD" .env
```

**PowerShell:**
```powershell
# Check configuration is valid
Select-String "LLM_API_KEY" .env
Select-String "POSTGRES_PASSWORD" .env
```

**⚠️ WARNING:** Never share your `.env` file or commit it to Git!

---

## ▶️ Starting the NOC

### Quick Start (Recommended)

**WSL/Bash - Use the automated setup script:**

```bash
# Navigate to project directory
cd /mnt/c/Users/<YourUsername>/ng-iam/smart-noc

# Run setup script
./setup-noc.sh
```

**PowerShell - Use the automated setup script:**

```powershell
# Navigate to project directory
cd C:\Users\<YourUsername>\ng-iam\smart-noc

# Run setup script
.\setup-noc.ps1
```

**What the script does:**
1. ✓ Checks prerequisites
2. ✓ Validates configuration
3. ✓ Sets up Python environment
4. ✓ Builds Docker images (5-10 minutes first time)
5. ✓ Starts all services
6. ✓ Runs health checks
7. ✓ Displays status

**First-time setup takes ~10-15 minutes. Subsequent starts take ~2 minutes.**

### Clean Start (If Problems Occur)

**WSL/Bash:**
```bash
# Remove old installation and start fresh
./setup-noc.sh --clean
```

**PowerShell:**
```powershell
# Remove old installation and start fresh
.\setup-noc.ps1 -Clean
```

### Manual Start (Advanced)

**WSL/Bash:**

```bash
# 1. Activate Python virtual environment
source ../../venv/bin/activate

# 2. Start infrastructure services first
docker compose up -d kafka postgres

# 3. Wait 30 seconds for infrastructure
sleep 30

# 4. Start application services
docker compose up -d

# 5. Check status
docker compose ps
```

**PowerShell:**

```powershell
# 1. Activate Python virtual environment
.\venv\Scripts\Activate.ps1

# 2. Start infrastructure services first
docker compose up -d kafka postgres

# 3. Wait 30 seconds for infrastructure
Start-Sleep -Seconds 30

# 4. Start application services
docker compose up -d

# 5. Check status
docker compose ps
```

---

## ✅ Verifying the System

### Quick Health Check

```powershell
# View all running services
docker compose ps

# Expected output: All services in "running" state
#   - kafka
#   - postgres
#   - anomaly-detection
#   - correlation-engine
#   - llm-diagnosis
```

### Detailed Verification

#### 1. Check Database

```powershell
# Count incidents in database
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents;"

# Expected: Shows number (0 or more)
```

#### 2. Check Services Are Processing

```powershell
# View LLM diagnosis service logs
docker compose logs llm-diagnosis --tail 20

# Expected: See "Diagnosis Service running!" or diagnosis messages
```

#### 3. Check Kafka Topics

```powershell
# List Kafka topics
docker compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list

# Expected: See topics like:
#   - network-events
#   - anomalies
#   - incidents
#   - incidents-diagnosed
```

### Generate Test Data

**WSL/Bash:**

```bash
# Activate Python environment
source ../../venv/bin/activate

# Navigate to log generator
cd services/log-generator

# Generate test scenario (5 incidents)
python generate_scenarios.py --scenario chaos --count 5

# Wait 30 seconds for processing
sleep 30

# Check results
cd ../..
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents WHERE created_at > NOW() - INTERVAL '1 minute';"
```

**PowerShell:**

```powershell
# Activate Python environment
.\venv\Scripts\Activate.ps1

# Navigate to log generator
cd services\log-generator

# Generate test scenario (5 incidents)
python generate_scenarios.py --scenario chaos --count 5

# Wait 30 seconds for processing
Start-Sleep -Seconds 30

# Check results
cd ..\..
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents WHERE created_at > NOW() - INTERVAL '1 minute';"
```

**✅ If you see new incidents, the system is working correctly!**

---

## 🛑 Stopping the NOC

### Clean Shutdown (Recommended)

**WSL/Bash - Use the automated teardown script:**

```bash
# Navigate to project directory
cd /mnt/c/Users/<YourUsername>/ng-iam/smart-noc

# Run teardown script
./teardown-noc.sh
```

**PowerShell - Use the automated teardown script:**

```powershell
# Navigate to project directory
cd C:\Users\<YourUsername>\ng-iam\smart-noc

# Run teardown script
.\teardown-noc.ps1
```

**Options:**

**WSL/Bash:**
```bash
# Keep database data (incidents preserved)
./teardown-noc.sh --keep-data

# Keep Docker images (faster restart next time)
./teardown-noc.sh --keep-images

# Force teardown (no confirmations)
./teardown-noc.sh --force

# Combine options
./teardown-noc.sh --keep-data --keep-images
```

**PowerShell:**
```powershell
# Keep database data (incidents preserved)
.\teardown-noc.ps1 -KeepData

# Keep Docker images (faster restart next time)
.\teardown-noc.ps1 -KeepImages

# Force teardown (no confirmations)
.\teardown-noc.ps1 -Force

# Combine options
.\teardown-noc.ps1 -KeepData -KeepImages
```

### Quick Stop (Without Cleanup)

```bash
# Just stop containers (same for both platforms)
docker compose stop

# Or stop specific service
docker compose stop llm-diagnosis
```

### Full Cleanup (Manual)

```bash
# Stop and remove everything (same for both platforms)
docker compose down -v

# Remove networks
docker network prune -f

# Remove images
docker rmi $(docker images "smart-noc*" -q)
```

---

## 🔥 Troubleshooting

### Problem: "Docker daemon is not running"

**Symptoms:**
```
Cannot connect to the Docker daemon
```

**Solution:**
1. Open Docker Desktop application
2. Wait for Docker icon in system tray to turn green
3. Try command again

---

### Problem: "Port already in use"

**Symptoms:**
```
Error: bind: address already in use
```

**Solution:**

**WSL/Bash:**
```bash
# Find what's using port 5432 (PostgreSQL)
sudo lsof -i :5432
# or
sudo netstat -tulpn | grep :5432

# Find what's using port 9092 (Kafka)
sudo lsof -i :9092
# or
sudo netstat -tulpn | grep :9092

# Stop the conflicting process or change port in .env
```

**PowerShell:**
```powershell
# Find what's using port 5432 (PostgreSQL)
netstat -ano | findstr :5432

# Find what's using port 9092 (Kafka)
netstat -ano | findstr :9092

# Stop the conflicting process or change port in .env
```

---

### Problem: "Setup script fails during build"

**Symptoms:**
```
ERROR: failed to build image
```

**Solutions:**

1. **Clean Docker cache (same for both platforms):**
   ```bash
   docker system prune -a -f
   ```

2. **Retry with clean flag:**
   
   **WSL/Bash:**
   ```bash
   ./setup-noc.sh --clean
   ```
   
   **PowerShell:**
   ```powershell
   .\setup-noc.ps1 -Clean
   ```

3. **Check disk space:**
   
   **WSL/Bash:**
   ```bash
   df -h /mnt/c
   # Need at least 10 GB free
   ```
   
   **PowerShell:**
   ```powershell
   Get-PSDrive C | Select-Object Used,Free
   # Need at least 10 GB free
   ```

---

### Problem: "LLM diagnosis not working"

**Symptoms:**
- No diagnosis appearing in database
- Logs show "Rate limit exceeded"

**Solutions:**

1. **Check API key is valid:**
   
   **WSL/Bash:**
   ```bash
   grep "LLM_API_KEY" .env
   # Verify key starts with "github_pat_"
   ```
   
   **PowerShell:**
   ```powershell
   Select-String "LLM_API_KEY" .env
   # Verify key starts with "github_pat_"
   ```

2. **Rate limit reached (150/day for free tier):**
   - Wait 24 hours for reset
   - Or upgrade to paid tier
   - Service will auto-resume when limit resets

3. **Restart diagnosis service (same for both platforms):**
   ```bash
   docker compose restart llm-diagnosis
   docker compose logs -f llm-diagnosis
   ```

---

### Problem: "Services keep restarting"

**Symptoms:**
```
docker compose ps
# Shows services with "restarting" state
```

**Solution:**

```powershell
# Check logs for specific service
docker compose logs anomaly-detection --tail 50

# Look for error messages
# Common issues:
# - Database connection failed → Check postgres is running
# - Kafka connection failed → Check kafka is running
# - Configuration error → Check .env file
```

---

### Problem: "Python virtual environment issues"

**Symptoms:**
- `'activate' is not recognized` (Windows)
- `source: not found` (WSL)

**Solution:**

**WSL/Bash:**
```bash
# Remove and recreate venv
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r services/log-generator/requirements.txt
```

**PowerShell:**
```powershell
# Remove and recreate venv
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r services\log-generator\requirements.txt
```

---

### General Debugging Commands

```powershell
# View all container logs
docker compose logs

# Follow logs in real-time
docker compose logs -f

# Check container resource usage
docker stats

# Restart specific service
docker compose restart <service-name>

# Enter container shell
docker compose exec <service-name> bash

# Check service health
docker compose ps --status running
```

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────┐
│                    DATA FLOW                        │
└─────────────────────────────────────────────────────┘

Network Logs → Logstash → Kafka (network-events)
                             ↓
              Anomaly Detection Service → Kafka (anomalies)
                             ↓
              Correlation Engine → Kafka (incidents)
                             ↓
              LLM Diagnosis Service → PostgreSQL
                             ↓
                      Enriched Incidents
```

### Service Details

| Service | Port | Purpose | Resources |
|---------|------|---------|-----------|
| **Kafka** | 9092 (external)<br>19092 (internal) | Message broker | 2 GB RAM |
| **PostgreSQL** | 5432 | Database | 1 GB RAM |
| **Anomaly Detection** | - | ML-based anomaly detection | 1 GB RAM |
| **Correlation Engine** | - | Event correlation → incidents | 512 MB RAM |
| **LLM Diagnosis** | - | AI root cause analysis | 512 MB RAM |
| **Log Generator** | - | Test data generator (optional) | 256 MB RAM |

### Data Persistence

- **PostgreSQL Data:** Stored in Docker volume `smart-noc_postgres_data`
- **Kafka Data:** Stored in Docker volume `smart-noc_kafka_data`
- **Backups:** Saved to `backups/` directory (created by teardown script)

### Network Architecture

- **Internal Network:** `smart-noc_default` (services communicate)
- **External Access:** Kafka (9092), PostgreSQL (5432)
- **No Internet Exposure:** Services run locally only

---

## ❓ FAQ

### Q: How long does first-time setup take?

**A:** 10-15 minutes (Docker image building). Subsequent starts take ~2 minutes.

---

### Q: Can I run this on a laptop?

**A:** Yes, but recommend 16 GB RAM and plugged into power.

---

### Q: How much does it cost?

**A:** $0 with GitHub Models free tier (150 diagnoses/day). Paid tier available if needed.

---

### Q: What if I restart my computer?

**A:** Services stop automatically. Run `.\setup-noc.ps1` again to restart.

---

### Q: How do I see what's happening?

**A:** View logs:
```powershell
# All services
docker compose logs -f

# Specific service
docker compose logs -f llm-diagnosis
```

---

### Q: Can I access the database directly?

**A:** Yes:
```powershell
docker compose exec -T postgres psql -U noc_admin -d smart_noc
```

---

### Q: How do I update the system?

**A:**
```powershell
# Pull latest code
git pull

# Rebuild and restart
.\teardown-noc.ps1 -KeepData
.\setup-noc.ps1 -Clean
```

---

### Q: Where are logs stored?

**A:** Docker container logs (not persisted). To save:
```powershell
docker compose logs > noc_logs_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt
```

---

### Q: Is my data safe?

**A:**
- ✅ Database persists between restarts (unless `-v` flag used)
- ✅ Teardown script offers backup before deletion
- ⚠️ Not production-grade (no replication, backups, etc.)

---

### Q: Can multiple people use this simultaneously?

**A:** One instance per machine. Not designed for multi-user access (yet).

---

### Q: What if rate limit is hit?

**A:**
- Service continues running
- New diagnoses queued automatically
- Resumes when limit resets (24 hours)
- Check status: `docker compose logs llm-diagnosis | Select-String "Rate limit"`

---

## 📞 Support & Resources

### Quick Commands Reference

See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for command cheat sheet.

### Log Locations

```powershell
# Service logs
docker compose logs <service-name>

# Database logs
docker compose logs postgres

# All logs
docker compose logs > full_logs.txt
```

### Getting Help

1. **Check logs:** `docker compose logs -f`
2. **Check this guide:** Search for your error
3. **Check containers:** `docker compose ps`
4. **Restart services:** `docker compose restart`
5. **Clean restart:** `.\teardown-noc.ps1 -Force` then `.\setup-noc.ps1 -Clean`

### Files You'll Need

- **Scripts:**
  - `setup-noc.ps1` - Start NOC
  - `teardown-noc.ps1` - Stop NOC

- **Configuration:**
  - `.env` - Environment variables
  - `docker-compose.yml` - Service definitions

- **Documentation:**
  - `NOC_SETUP_GUIDE.md` - This file
  - `QUICK_REFERENCE.md` - Command cheat sheet

---

## ✅ Next Steps

**After successful setup:**

1. ✅ **Verify all services running:**
   ```powershell
   docker compose ps
   ```

2. ✅ **Generate test data:**
   ```powershell
   cd services\log-generator
   ..\..\venv\Scripts\activate
   python generate_scenarios.py --scenario chaos --count 5
   ```

3. ✅ **Monitor AI diagnoses:**
   ```powershell
   docker compose logs -f llm-diagnosis
   ```

4. ✅ **Query database:**
   ```powershell
   docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents;"
   ```

**🎉 You're now running a fully automated AI-powered NOC!**

---

**Document Version:** 1.0  
**Last Updated:** April 25, 2026  
**Maintained By:** Smart NOC Team

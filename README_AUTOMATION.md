# Smart NOC - Automated Setup & Teardown Scripts

## 📦 What's Included

This package contains everything your team needs to set up and operate the Smart NOC system:

### Scripts

**For WSL/Bash Users (Recommended):**
- **`setup-noc.sh`** - Automated setup script (starts the entire NOC)
- **`teardown-noc.sh`** - Automated teardown script (safely stops and cleans up)

**For PowerShell Users:**
- **`setup-noc.ps1`** - Automated setup script (starts the entire NOC)
- **`teardown-noc.ps1`** - Automated teardown script (safely stops and cleans up)

### Documentation
- **`NOC_SETUP_GUIDE.md`** - Complete setup guide (for beginners)
- **`QUICK_REFERENCE.md`** - Command cheat sheet (for daily operations)
- **`README_SCRIPTS.md`** - Platform selection guide (bash vs PowerShell)
- **`README_AUTOMATION.md`** - This file

---

## 🚀 Quick Start (For Team Members)

### Choose Your Platform

**If you're using WSL/Bash** (you've been running `wsl bash -c` commands), see [WSL/Bash Quick Start](#wslbash-quick-start)

**If you're using PowerShell**, see [PowerShell Quick Start](#powershell-quick-start)

---

### WSL/Bash Quick Start

1. **Open WSL terminal**
   - Press `Windows + R`, type `wsl`, press Enter
   - Or search for "Ubuntu" in Start Menu

2. **Navigate to project directory**
   ```bash
   cd /mnt/c/Users/<YourUsername>/ng-iam/smart-noc
   ```

3. **Configure environment (ONE TIME)**
   ```bash
   # Copy example config
   cp .env.example .env
   
   # Edit configuration
   nano .env  # or: vim .env
   
   # Add your GitHub Models API key:
   # LLM_API_KEY=github_pat_YOUR_TOKEN_HERE
   ```

4. **Run setup script**
   ```bash
   ./setup-noc.sh
   ```

5. **Wait 10-15 minutes** (first time only)
   - Downloads Docker images
   - Builds services
   - Initializes database
   - Starts all containers

6. **Verify it's working**
   ```bash
   docker compose ps
   # All services should show "running"
   ```

**✅ That's it! The NOC is now running.**

---

### PowerShell Quick Start

1. **Open PowerShell as Administrator**
   - Press `Windows + X`
   - Select "Windows PowerShell (Admin)"

2. **Navigate to project directory**
   ```powershell
   cd C:\Users\<YourUsername>\ng-iam\smart-noc
   ```

3. **Configure environment (ONE TIME)**
   ```powershell
   # Copy example config
   Copy-Item .env.example .env
   
   # Edit configuration
   notepad .env
   
   # Add your GitHub Models API key:
   # LLM_API_KEY=github_pat_YOUR_TOKEN_HERE
   ```

4. **Run setup script**
   ```powershell
   .\setup-noc.ps1
   ```

5. **Wait 10-15 minutes** (first time only)
   - Downloads Docker images
   - Builds services
   - Initializes database
   - Starts all containers

6. **Verify it's working**
   ```powershell
   docker compose ps
   # All services should show "running"
   ```

**✅ That's it! The NOC is now running.**

---

## 🛑 Stopping the NOC

### Normal Shutdown (Keeps Data)

**WSL/Bash:**
```bash
./teardown-noc.sh --keep-data
```

**PowerShell:**
```powershell
.\teardown-noc.ps1 -KeepData
```

### Complete Cleanup (Removes Everything)

**WSL/Bash:**
```bash
./teardown-noc.sh
```

**PowerShell:**
```powershell
.\teardown-noc.ps1
```

---

## 📖 Documentation Guide

### For Beginners (Start Here)

**Read:** [`NOC_SETUP_GUIDE.md`](NOC_SETUP_GUIDE.md)

Covers:
- Prerequisites and requirements
- Step-by-step setup instructions
- How to verify the system is working
- Troubleshooting common problems
- Architecture overview
- FAQ

### For Daily Operations

**Read:** [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md)

Quick command reference for:
- Starting/stopping services
**WSL/Bash:**
```bash
# Navigate to directory
cd /mnt/c/Users/<YourUsername>/ng-iam/smart-noc

# Start NOC
./setup-noc.sh

# Verify status
docker compose ps
```

**PowerShell:**
```powershell
# Navigate to directory
cd C:\Users\<YourUsername>\ng-iam\smart-noc

# Start NOC
.\setup-noc.ps1

# Verify status
docker compose ps
```

### Scenario 2: Stopping NOC at End of Day

**WSL/Bash:**
```bash
# Stop NOC (keep data for tomorrow)
./teardown-noc.sh --keep-data
```

**PowerShell:**
```powershell
# Stop NOC (keep data for tomorrow)
.\teardown-noc.ps1 -KeepData
```

### Scenario 3: Fresh Install (Clean Slate)

**WSL/Bash:**
```bash
# Remove old installation
./teardown-noc.sh --force

# Clean install
./setup-noc.sh --clean
```

**PowerShell:**
```powershell
# Remove old installation
.\teardown-noc.ps1 -Force

# Clean install
.\setup-noc.ps1 -Clean
```

### Scenario 4: Something's Broken

**WSL/Bash:**
```bash
# Try restarting
./teardown-noc.sh --force
./setup-noc.sh --clean

# Check logs if still broken
docker compose logs <service-name>
```

**PowerShell:*sh (WSL/Bash)

```bash
# Skip prerequisite checks (faster, but risky)
./setup-noc.sh --skip-prereq

# Remove old installation first
./setup-noc.sh --clean

# Suppress build logs (cleaner output)
./setup-noc.sh --no-logs

# Combine options
./setup-noc.sh --clean --no-logs
```

### setup-noc.ps1 (PowerShell)

```powershell
# Skip prerequisite checks (faster, but risky)
.\setup-noc.ps1 -SkipPrereqCheck

# Remove old installation first
.\setup-noc.ps1 -Clean

# Suppress build logs (cleaner output)
.\setup-noc.ps1 -NoLogs

# Combine options
.\setup-noc.ps1 -Clean -NoLogs
```

### teardown-noc.sh (WSL/Bash)

```bash
# Keep database volumes (data preserved)
./teardown-noc.sh --keep-data

# Keep Docker images (faster next start)
./teardown-noc.sh --keep-images

# No confirmation prompts
./teardown-noc.sh --force

# Combine options
./teardown-noc.sh --keep-data --keep-images --force
```

### teardown-noc.ps1 (PowerShell)
# Generate test data
cd services/log-generator
source ../../venv/bin/activate
python generate_scenarios.py --scenario chaos --count 5

# Watch results (in another terminal)
docker compose logs -f llm-diagnosis
```

**PowerShell:**### Scenario 4: Something's Broken

```powershell
# Try restarting
.\teardown-noc.ps1 -Force
.\setup-noc.ps1 -Clean

# Check logs if still broken
docker compose logs <service-name>
```

### Scenario 5: Running Tests

```powershell
# Start NOC
.\setup-noc.ps1

# Generate test data
cd services\log-generator
..\..\venv\Scripts\Activate.ps1
python generate_scenarios.py --scenario chaos --count 5

# Watch results
docker compose logs -f llm-diagnosis
```

---

## ⚙️ Script Options

### setup-noc.ps1

```powershell
# Skip prerequisite checks (faster, but risky)
.\setup-noc.ps1 -SkipPrereqCheck

# Remove old installation first
.\setup-noc.ps1 -Clean

# Suppress build logs (cleaner output)
.\setup-noc.ps1 -NoLogs

# Combine options
.\setup-noc.ps1 -Clean -NoLogs
```

### teardown-noc.ps1

```powershell
# Keep database volumes (data preserved)
.\teardown-noc.ps1 -KeepData

# Keep Docker images (faster next start)
.\teardown-noc.ps1 -KeepImages

# No confirmation prompts
.\teardown-noc.ps1 -Force

# Combine options
.\teardown-noc.ps1 -KeepData -KeepImages -Force
```

---

## 🔍 What the Scripts Do

### setup-noc.ps1 Features

- ✅ **Checks prerequisites:** Docker, Python, WSL, disk space, memory
- ✅ **Validates configuration:** Ensures .env file has required values
- ✅ **Sets up Python environment:** Creates venv and installs dependencies
- ✅ **Builds Docker images:** Compiles all services (cached after first run)
- ✅ **Starts services:** Infrastructure first (Kafka, PostgreSQL), then apps
- ✅ **Runs health checks:** Verifies everything is working
- ✅ **Provides summary:** Shows what's running and next steps

**Typical Runtime:**
- First run: 10-15 minutes
- Subsequent runs: 2-3 minutes

### teardown-noc.ps1 Features

- ✅ **Confirms action:** Asks before deleting (unless -Force)
- ✅ **Offers backup:** Can backup database before removal
- ✅ **Graceful shutdown:** Stops services properly (no data corruption)
- ✅ **Cleanup:** Removes containers, networks, volumes, images (optional)
- ✅ **Validates:** Checks everything is removed
- ✅ **Provides summary:** Shows what was cleaned

**Typical Runtime:**
- Normal: 30-60 seconds
- With backup: 2-3 minutes

---

## 🛠️ Manual Operations (If Needed)

### Start Services Manually

```powershell
# Start infrastructure
docker compose up -d kafka postgres

# Wait 30 seconds
Start-Sleep -Seconds 30

# Start applications
docker compose up -d
```

### Stop Services Manually

```powershell
# Stop all
docker compose down

# Stop and remove volumes
docker compose down -v

# Stop specific service
docker compose stop llm-diagnosis
```

### Check Status

```powershell
# List running containers
docker compose ps

# View logs
docker compose logs -f llm-diagnosis

# Check resource usage
docker stats
```

---

## 🆘 Troubleshooting

### Script Won't Run

**Error:** "Execution policy does not allow running scripts"

**Solution:**
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try again
.\setup-noc.ps1
```

### Docker Not Running

**Error:** "Cannot connect to Docker daemon"

**Solution:**
1. Open Docker Desktop application
2. Wait for Docker to start (icon turns green in system tray)
3. Run script again

### Missing .env File

**Error:** ".env file not found"

**Solution:**
```powershell
Copy-Item .env.example .env
notepad .env
# Update LLM_API_KEY and POSTGRES_PASSWORD
```

### Services Don't Start

**Check:**
```powershell
# View all logs
docker compose logs

# Check specific service
docker compose logs llm-diagnosis

# Look for error messages
```

**Common Issues:**
- Port already in use → Change port in .env or stop conflicting app
- Insufficient disk space → Clean Docker: `docker system prune -a`
- Memory issues → Close other applications

---

## 📋 Pre-Flight Checklist

Before handing over to team members, ensure:

- [ ] **Docker Desktop** is installed and running
- [ ] **Python 3.9+** is installed
- [ ] **WSL 2** is installed (run: `wsl --install` if needed)
- [ ] **`.env` file** exists with valid API key
- [ ] **Scripts tested:** Run `.\setup-noc.ps1` and verify it works
- [ ] **Teardown tested:** Run `.\teardown-noc.ps1` and verify cleanup
- [ ] **Documentation reviewed:** Team member can follow NOC_SETUP_GUIDE.md

---

## 📞 Support

### For Team Members

1. **Read the guide:** [NOC_SETUP_GUIDE.md](NOC_SETUP_GUIDE.md)
2. **Check quick reference:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. **Check logs:** `docker compose logs <service-name>`
4. **Try clean restart:** `.\teardown-noc.ps1 -Force` + `.\setup-noc.ps1 -Clean`

### Common Questions

**Q: How long does setup take?**  
A: First time: 10-15 minutes. After that: 2-3 minutes.

**Q: Can I stop and restart without losing data?**  
A: Yes! Use `.\teardown-noc.ps1 -KeepData`

**Q: What if I restart my computer?**  
A: Run `.\setup-noc.ps1` again to restart services.

**Q: How much does this cost?**  
A: $0 with GitHub Models free tier (150 diagnoses/day).

**Q: Is my data safe?**  
A: Data persists in Docker volumes. Teardown offers backup before deletion.

---

## 📊 System Requirements

### Minimum
- Windows 10/11 (64-bit)
- 8 GB RAM
- 20 GB free disk space
- 4 CPU cores
- Internet connection

### Recommended
- Windows 11
- 16 GB RAM
- 50 GB free disk space
- 8 CPU cores
- Fast internet connection

---

## 🎓 Training New Team Members

### Day 1: Setup
1. Read NOC_SETUP_GUIDE.md (30 minutes)
2. Install prerequisites (30 minutes)
3. Run `.\setup-noc.ps1` (15 minutes)
4. Verify system is working (15 minutes)

### Day 2: Operations
1. Read QUICK_REFERENCE.md (15 minutes)
2. Generate test data (15 minutes)
3. View logs and database (30 minutes)
4. Practice stop/start (15 minutes)

### Day 3: Troubleshooting
1. Practice clean restart (15 minutes)
2. Review common issues (30 minutes)
3. Practice log analysis (30 minutes)

**Total Training Time:** ~4 hours

---

## 📝 Notes

- Scripts are designed for **Windows PowerShell** (not WSL/Linux)
- All paths are **Windows-style** (`C:\Users\...`)
- Scripts include **color-coded output** for easy reading
- **Progress indicators** show what's happening
- **Error messages** include troubleshooting hints
- **Safe by default:** Asks for confirmation before destructive actions

---

## ✅ Handover Checklist

When handing over to a team member:

- [ ] Provide access to project directory
- [ ] Ensure they have local admin rights (for Docker)
- [ ] Give them GitHub Models API key (or instructions to create one)
- [ ] Walk through first setup together
- [ ] Show them how to check logs
- [ ] Demonstrate teardown
- [ ] Point them to documentation
- [ ] Exchange contact info for support

---

**Version:** 1.0  
**Created:** April 25, 2026  
**For:** Smart NOC Team

**Remember:** The scripts are beginner-friendly. Even team members with no Docker or Kafka knowledge can operate the NOC using these tools! 🚀

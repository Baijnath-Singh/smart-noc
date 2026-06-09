# Smart NOC - Quick Reference Guide

**One-page command reference for daily operations**

---

## 🚀 Start/Stop NOC

### WSL/Bash Users (Recommended)

```bash
# Start NOC (automated)
./setup-noc.sh

# Start with clean slate
./setup-noc.sh --clean

# Skip prerequisite checks
./setup-noc.sh --skip-prereq

# Stop NOC (automated)
./teardown-noc.sh

# Stop and keep data
./teardown-noc.sh --keep-data

# Stop and keep images (faster restart)
./teardown-noc.sh --keep-data --keep-images

# Force stop (no prompts)
./teardown-noc.sh --force
```

### PowerShell Users

```powershell
# Start NOC (automated)
.\setup-noc.ps1

# Start with clean slate
.\setup-noc.ps1 -Clean

# Stop NOC (automated)
.\teardown-noc.ps1

# Stop and keep data
.\teardown-noc.ps1 -KeepData

# Stop and keep images (faster restart)
.\teardown-noc.ps1 -KeepData -KeepImages

# Force stop (no prompts)
.\teardown-noc.ps1 -Force
```

---

## 📊 Check Status

```powershell
# View all services
docker compose ps

# Check specific service
docker compose ps llm-diagnosis

# View service health
docker stats

# Check container logs
docker compose logs <service-name>

# Follow logs in real-time
docker compose logs -f <service-name>

# Last 50 lines
docker compose logs --tail 50 <service-name>
```

---

## 🔍 Database Queries

```powershell
# Connect to database
docker compose exec -T postgres psql -U noc_admin -d smart_noc

# Count incidents
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents;"

# View recent incidents
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, incident_type, severity, created_at FROM incidents ORDER BY created_at DESC LIMIT 10;"

# View diagnosed incidents
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, root_cause_confidence, LEFT(root_cause, 80) FROM incidents WHERE root_cause IS NOT NULL ORDER BY diagnosis_timestamp DESC LIMIT 5;"

# Diagnosis statistics
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT * FROM diagnosis_statistics;"

# Incident statistics
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT * FROM incident_statistics;"
```

---

## 🧪 Generate Test Data

### WSL/Bash

```bash
# Activate Python environment
source ../../venv/bin/activate
cd services/log-generator

# Generate chaos scenario (random anomalies)
python generate_scenarios.py --scenario chaos --count 5

# Generate interface flapping
python generate_scenarios.py --scenario flapping --count 10

# Generate high CPU scenario
python generate_scenarios.py --scenario high-cpu --count 8

# Generate BGP instability
python generate_scenarios.py --scenario bgp-instability --count 6

# Generate brute force attacks
python generate_scenarios.py --scenario brute-force --count 12

# Generate random logs
python generate_logs.py --rate 50 --duration 10
```

### PowerShell

```powershell
# Activate Python environment
.\venv\Scripts\Activate.ps1
cd services\log-generator

# Generate chaos scenario (random anomalies)
python generate_scenarios.py --scenario chaos --count 5

# Generate interface flapping
python generate_scenarios.py --scenario flapping --count 10

# Generate high CPU scenario
python generate_scenarios.py --scenario high-cpu --count 8

# Generate BGP instability
python generate_scenarios.py --scenario bgp-instability --count 6

# Generate brute force attacks
python generate_scenarios.py --scenario brute-force --count 12

# Generate random logs
python generate_logs.py --rate 50 --duration 10
```

---

## 🔧 Service Management

```powershell
# Restart specific service
docker compose restart <service-name>

# Restart all services
docker compose restart

# Stop specific service
docker compose stop <service-name>

# Start specific service
docker compose start <service-name>

# Rebuild service
docker compose build <service-name>

# Rebuild and restart
docker compose up -d --build <service-name>

# View service configuration
docker compose config
```

---

## 📝 View Logs

```powershell
# All services
docker compose logs

# Specific service
docker compose logs llm-diagnosis
docker compose logs correlation-engine
docker compose logs anomaly-detection

# Follow logs (real-time)
docker compose logs -f llm-diagnosis

# Last N lines
docker compose logs --tail 100 llm-diagnosis

# Since timestamp
docker compose logs --since 30m llm-diagnosis

# Save logs to file
docker compose logs > logs_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt
```

---

## 🐛 Troubleshooting

```powershell
# Check Docker is running
docker ps

# Check available disk space
Get-PSDrive C | Select-Object Used,Free

# Check memory usage
docker stats --no-stream

# Find ports in use
netstat -ano | findstr :5432
netstat -ano | findstr :9092

# Clean Docker cache
docker system prune -f

# Remove all unused resources
docker system prune -a -f

# Check service health
docker compose ps --status running

# Enter container shell
docker compose exec llm-diagnosis bash
docker compose exec postgres bash

# Check Kafka topics
docker compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list

# Check container environment
docker compose exec llm-diagnosis env
```

---

## 💾 Backup & Restore

### WSL/Bash

```bash
# Manual database backup
docker compose exec -T postgres pg_dump -U noc_admin smart_noc > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
docker compose exec -T postgres psql -U noc_admin smart_noc < backup_20260425_120000.sql

# Export logs
docker compose logs > full_logs_$(date +%Y%m%d_%H%M%S).txt

# Backup .env file
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)
```

### PowerShell

### WSL/Bash

```bash
# Watch incident count
watch -n 10 'docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents;"'

# Watch diagnosis progress
docker compose logs -f llm-diagnosis | grep "SUCCESS"

# Monitor resource usage
docker stats

# Check service uptime
docker compose ps --format json | jq -r '.[] | "\(.Service) - \(.Status)"'
```

### PowerShell

```powershell
# Manual database backup
docker compose exec -T postgres pg_dump -U noc_admin smart_noc > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# Restore database
Get-Content backup_20260425_120000.sql | docker compose exec -T postgres psql -U noc_admin smart_noc

# Export logs
docker compose logs > full_logs_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt

# Backup .env file
Copy-Item .env .env.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')
```

---

## 📈 Monitoring

```powershell
# Watch incident count
while ($true) { 
### WSL/Bash

```bash
# Update NOC code
git pull

# Rebuild after update
./teardown-noc.sh --keep-data
./setup-noc.sh --clean

# Update specific service
docker compose build <service-name>
docker compose up -d <service-name>

# Clean old Docker images
docker image prune -a

# Clean old volumes (CAUTION: deletes data)
docker volume prune
```

### PowerShell

    docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents;"
    Start-Sleep 10 
}

# Watch diagnosis progress
docker compose logs -f llm-diagnosis | Select-String "SUCCESS"

# Monitor resource usage
docker stats

# Check service uptime
docker compose ps --format json | ConvertFrom-Json | Select-Object Service,Status,State
```

---

## 🔄 Update & Maintenance

```powershell
# Update NOC code
git pull

# Rebuild after update
.\teardown-noc.ps1 -KeepData
.\setup-noc.ps1 -Clean

# Update specific service
docker compose build <service-name>
### WSL/Bash

```bash
# View environment variables
nano .env  # or: vim .env

# Never commit .env to Git
git status
# Should show: .env (untracked)

# Change database password
# 1. Edit .env: POSTGRES_PASSWORD=new_password
# 2. Teardown: ./teardown-noc.sh
# 3. Setup: ./setup-noc.sh --clean
```

### PowerShell

docker compose up -d <service-name>

# Clean old Docker images
docker image prune -a

# Clean old volumes (CAUTION: deletes data)
docker volume prune
```

---

## 🌐 Service Endpoints

| Service | Internal | External | Credentials |
|---------|----------|----------|-------------|
| Kafka | kafka:19092 | localhost:9092 | - |
| PostgreSQL | postgres:5432 | localhost:5432 | noc_admin / (from .env) |
| Zookeeper | zookeeper:2181 | localhost:2181 | - |

---

## 🔐 Security

```powershell
# View environment variables
notepad .env

# Never commit .env to Git
git status
# Should show: .env (untracked)

# Change database password
# 1. Edit .env: POSTGRES_PASSWORD=new_password
# 2. Teardown: .\teardown-noc.ps1
# 3. Setup: .\setup-noc.ps1 -Clean
```

---

## 📁 Important Files

```
smart-noc/

**WSL/Bash:**
```bash
./teardown-noc.sh --force
./setup-noc.sh --clean
```

**PowerShell:**
```powershell
.\teardown-noc.ps1 -Force
.\setup-noc.ps1 -Clean
```

### Task: Restart just LLM diagnosis
```bash
docker compose restart llm-diagnosis
docker compose logs -f llm-diagnosis
```

### Task: Check if system is working
```bash
docker compose ps
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents;"
```

### Task: Generate test incidents and watch diagnosis

**WSL/Bash:**
```bash
# Terminal 1: Watch logs
docker compose logs -f llm-diagnosis

# Terminal 2: Generate data
cd services/log-generator
source ../../venv/bin/activate
python generate_scenarios.py --scenario chaos --count 3
```

**PowerShell:**
```powershell
# Terminal 1: Watch logs
docker compose logs -f llm-diagnosis

# Terminal 2: Generate data
cd services\log-generator
..\..\venv\Scripts\activate
python generate_scenarios.py --scenario chaos --count 3
```

### Task: Export incident report

**WSL/Bash:**
```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "COPY (SELECT * FROM incidents WHERE created_at > NOW() - INTERVAL '24 hours') TO STDOUT CSV HEADER;" > incidents_report_$(date +%Y%m%d).csv
```

**PowerShell:**
```powershell
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "COPY (SELECT * FROM incidents WHERE created_at > NOW() - INTERVAL '24 hours') TO STDOUT CSV HEADER;" > incidents_report_$(Get-Date -Format 'yyyyMMdd').csv
```

### Task: Check rate limit status

**WSL/Bash:**
```bash
docker compose logs llm-diagnosis | grep "Rate limit"
```

**PowerShell:**

### Task: Generate test incidents and watch diagnosis
```powershell
# Terminal 1: Watch logs
docker compose logs -f llm-diagnosis

# Terminal 2: Generate data
cd services\log-generator
..\..\venv\Scripts\activate
python generate_scenarios.py --scenario chaos --count 3
```

### Task: Export incident report
```powershell
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "COPY (SELECT * FROM incidents WHERE created_at > NOW() - INTERVAL '24 hours') TO STDOUT CSV HEADER;" > incidents_report_$(Get-Date -Format 'yyyyMMdd').csv
```

### Task: Check rate limit status
```powershell
docker compose logs llm-diagnosis | Select-String "Rate limit"
```

---

## 🆘 Emergency Commands

```powershell
# Kill all containers
docker compose kill

# Force remove containers
docker compose rm -f

# Nuclear option (removes EVERYTHING)
docker compose down -v --remove-orphans
docker system prune -a -f --volumes

# Then restart
.\setup-noc.ps1 -Clean
```

---

## 💡 Tips & Tricks

1. **Use aliases** for common commands:
   ```powershell
   Set-Alias noc-start "C:\Users\<user>\ng-iam\smart-noc\setup-noc.ps1"
   Set-Alias noc-stop "C:\Users\<user>\ng-iam\smart-noc\teardown-noc.ps1"
   ```

2. **Monitor multiple services:**
   ```powershell
   docker compose logs -f llm-diagnosis correlation-engine
   ```

3. **Quick incident check:**
   ```powershell
   docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE root_cause IS NOT NULL) as diagnosed FROM incidents;"
   ```

4. **Watch diagnosis in real-time:**
   ```powershell
   docker compose logs -f llm-diagnosis | Select-String "SUCCESS|ERROR"
   ```

5. **Performance check:**
   ```powershell
   docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
   ```

---

## 📞 Quick Checklist

**Before reporting issues:**

- [ ] Docker Desktop is running
- [ ] All services show "running" in `docker compose ps`
- [ ] .env file has valid API key
- [ ] Sufficient disk space (10 GB+)
- [ ] Checked service logs: `docker compose logs <service>`
- [ ] Tried restarting service: `docker compose restart <service>`
- [ ] Tried clean restart: `.\teardown-noc.ps1 -Force` + `.\setup-noc.ps1 -Clean`

---

**Version:** 1.0  
**Last Updated:** April 25, 2026  
**Full Documentation:** [NOC_SETUP_GUIDE.md](NOC_SETUP_GUIDE.md)

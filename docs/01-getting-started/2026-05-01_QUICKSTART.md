# Smart NOC - Quick Start Guide

## 🚀 Quick Start (5 Minutes)

### 1. Prerequisites Check

```bash
# Check Docker
docker --version
# Expected: Docker version 24.x or higher

# Check Docker Compose
docker compose version
# Expected: Docker Compose version v2.x or higher
```

### 2. Start the System

```bash
# Navigate to project
cd ~/ng-iam/smart-noc

# Start all services
docker compose up -d

# Wait for all services to be healthy (takes ~60 seconds)
docker compose ps

# Expected output: All services show "Up (healthy)"
```

### 3. Install Python Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install log generator dependencies
cd services/log-generator
pip install -r requirements.txt
cd ../..
```

### 4. Generate Logs

```bash
# Start generating logs
python services/log-generator/generate_logs.py --rate 20

# You should see:
# ✅ Connected to Kafka successfully
# 📊 Sent: core-router-01 - INTERFACE_DOWN
```

### 5. View Results

Open these URLs in your browser:

- **Kafka UI**: http://localhost:8080
  - Go to Topics → network-logs
  - You should see messages flowing in

- **Elasticsearch**: http://localhost:9200/network-logs-*/_search?pretty&size=5
  - Should return parsed log entries

- **Grafana**: http://localhost:3000
  - Login: admin / admin
  - (Dashboard setup in Phase 1 guide)

---

## 🐛 Troubleshooting

### Services won't start

```bash
# Check Docker Desktop is running (Windows taskbar)
# Then restart services
docker compose down
docker compose up -d
```

### Kafka connection refused

```bash
# Wait for Kafka to initialize (can take 60 seconds)
docker compose logs kafka

# Look for: "Kafka Server started"
```

### Python package errors

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Reinstall dependencies
pip install -r services/log-generator/requirements.txt
```

### Port conflicts

```bash
# Check if ports are already in use
netstat -ano | findstr "9092"  # Kafka
netstat -ano | findstr "9200"  # Elasticsearch
netstat -ano | findstr "3000"  # Grafana

# If needed, change ports in docker-compose.yml
```

---

## 📚 Useful Commands

```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f kafka
docker compose logs -f logstash

# Restart a service
docker compose restart logstash

# Stop all services
docker compose down

# Stop and remove all data
docker compose down -v

# Check resource usage
docker stats
```

---

## 🔧 Configuration

### Change log generation rate

```bash
# Low: 5 logs/sec
python services/log-generator/generate_logs.py --rate 5

# Medium: 50 logs/sec
python services/log-generator/generate_logs.py --rate 50

# High: 100 logs/sec (laptop may struggle)
python services/log-generator/generate_logs.py --rate 100
```

### Run specific scenarios

```bash
# Interface flapping
python services/log-generator/generate_logs.py --scenario flap

# Run for specific duration
python services/log-generator/generate_logs.py --duration 300  # 5 minutes
```

---

## 📊 What's Next?

Once you have logs flowing:

1. ✅ **Phase 1 Complete** - Basic log pipeline working
2. 🔜 **Phase 2** - Add anomaly detection
3. 🔜 **Phase 3** - Add correlation engine
4. 🔜 **Phase 4** - Add LLM diagnosis
5. 🔜 **Phase 5** - Add remediation
6. 🔜 **Phase 6** - Add orchestration

Continue to: [docs/PHASE-2-ANOMALY-DETECTION.md](docs/PHASE-2-ANOMALY-DETECTION.md)

---

## 🆘 Getting Help

- **Documentation**: Check `docs/` folder for detailed guides
- **Logs**: Always check `docker compose logs` for errors
- **Community**: Search for specific error messages

**Tip**: Start with low log rates (5-10/sec) while learning the system!

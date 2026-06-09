# Troubleshooting Guide

## 🆘 Common Issues and Solutions

---

## Phase 0: Environment Setup

### Issue: WSL2 not installing

**Symptoms:**
```
wsl --install
Error: The requested operation requires elevation
```

**Solution:**
1. Run PowerShell as Administrator
2. Enable virtualization in BIOS
3. Run: `wsl --install --web-download`

---

### Issue: Docker Desktop won't start

**Symptoms:**
- Docker Desktop stuck on "Starting..."
- "Docker Desktop stopped"

**Solutions:**
1. Check Windows Subsystem for Linux is enabled:
   ```powershell
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```

2. Update WSL kernel:
   ```powershell
   wsl --update
   ```

3. Reset Docker Desktop:
   - Settings → Troubleshoot → Reset to factory defaults

4. Check virtualization:
   - Task Manager → Performance → CPU
   - Should show "Virtualization: Enabled"
   - If not, enable in BIOS

---

## Phase 1: Log Pipeline

### Issue: Kafka won't start

**Symptoms:**
```
kafka container keeps restarting
```

**Check logs:**
```bash
docker compose logs kafka
```

**Common causes:**

#### 1. Port 9092 already in use
```bash
# Windows: Check port
netstat -ano | findstr "9092"

# Kill process using port
taskkill /PID <process_id> /F
```

#### 2. Insufficient memory
```bash
# Check Docker Desktop → Settings → Resources
# Increase to at least 4GB
```

#### 3. Kafka data corruption
```bash
# Stop and remove volumes
docker compose down -v

# Start fresh
docker compose up -d
```

---

### Issue: Logstash parsing errors

**Symptoms:**
```
Tags: _grokparsefailure
```

**Debug:**
```bash
# View logstash logs
docker compose logs -f logstash

# Test grok pattern
docker compose exec logstash bin/logstash -e '
input { stdin { } }
filter { 
  grok { 
    match => { "message" => "YOUR_PATTERN_HERE" }
  }
}
output { stdout { codec => rubydebug } }'
```

**Solution:**
- Update grok pattern in `infrastructure/logstash/pipeline/network-logs.conf`
- Test at: https://grokdebugger.com/

---

### Issue: Elasticsearch won't start

**Symptoms:**
```
elasticsearch container exits immediately
```

**Check:**
```bash
docker compose logs elasticsearch
```

**Common issues:**

#### 1. vm.max_map_count too low (Linux/WSL)
```bash
# In WSL terminal
sudo sysctl -w vm.max_map_count=262144

# Make permanent
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

#### 2. Disk space low
```bash
# Check disk space
df -h

# Clean Docker
docker system prune -a --volumes
```

---

### Issue: Log generator can't connect to Kafka

**Symptoms:**
```python
kafka.errors.NoBrokersAvailable: NoBrokersAvailable
```

**Solutions:**

1. Check Kafka is running:
   ```bash
   docker compose ps kafka
   ```

2. Wait for Kafka to be ready (takes ~60 seconds):
   ```bash
   docker compose logs -f kafka | grep "started"
   ```

3. Check network:
   ```bash
   # From WSL
   curl -v telnet://localhost:9092
   ```

4. Check Kafka health:
   ```bash
   docker compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
   ```

---

## Phase 2: Anomaly Detection

### Issue: No anomalies detected

**Debug:**
1. Check detector is running:
   ```bash
   ps aux | grep anomaly_detector
   ```

2. Check logs:
   ```bash
   # If running in terminal
   # Should see: "Monitoring: network-logs-parsed"
   ```

3. Verify baseline exists:
   ```bash
   ls -l data/baseline.json
   ```

4. Lower thresholds temporarily:
   ```yaml
   # config/anomaly_detector.yaml
   interface_flap_count: 2  # was 5
   ```

---

### Issue: Too many false positives

**Solutions:**

1. Collect more baseline data:
   ```bash
   python anomaly_detector.py --mode baseline --duration 172800
   ```

2. Increase thresholds:
   ```yaml
   interface_flap_count: 10
   frequency_multiplier: 5
   zscore_threshold: 4
   ```

3. Add device-specific rules:
   ```python
   # Some devices are noisier
   if device_id in NOISY_DEVICES:
       threshold *= 2
   ```

---

## Docker Issues

### Issue: Docker daemon not running

**Symptoms:**
```
Cannot connect to the Docker daemon
```

**Solution:**
1. Start Docker Desktop on Windows
2. Wait for it to fully start
3. Check: `docker ps`

---

### Issue: Out of disk space

**Symptoms:**
```
no space left on device
```

**Solution:**
```bash
# Clean up Docker
docker system prune -a --volumes

# Check disk usage
docker system df

# Remove old images
docker images
docker rmi <image_id>
```

---

### Issue: Container won't stop

**Symptoms:**
```bash
docker compose down  # hangs
```

**Solution:**
```bash
# Force stop
docker compose down --timeout 30

# Or kill containers
docker ps -q | ForEach-Object { docker kill $_ }
```

---

## Performance Issues

### Issue: High CPU usage

**Check:**
```bash
docker stats

# Find culprit container
```

**Solutions:**

1. **Kafka**: Reduce heap
   ```yaml
   KAFKA_HEAP_OPTS: "-Xmx256M -Xms256M"
   ```

2. **Logstash**: Reduce workers
   ```yaml
   LS_JAVA_OPTS: "-Xmx256m -Xms256m"
   ```

3. **Log generator**: Lower rate
   ```bash
   python generate_logs.py --rate 5
   ```

---

### Issue: High memory usage

**Solutions:**

1. Limit Docker Desktop memory:
   - Docker Desktop → Settings → Resources
   - Set to 6GB or 8GB

2. Reduce container memory:
   ```yaml
   # In docker-compose.yml
   services:
     kafka:
       deploy:
         resources:
           limits:
             memory: 512M
   ```

3. Clear caches:
   ```bash
   # Elasticsearch
   curl -X POST "localhost:9200/_cache/clear?pretty"
   ```

---

## Network Issues

### Issue: Can't access services from browser

**Symptoms:**
- Kafka UI (http://localhost:8080) not loading
- Grafana (http://localhost:3000) not loading

**Solutions:**

1. Check containers are running:
   ```bash
   docker compose ps
   ```

2. Check port mapping:
   ```bash
   docker compose port grafana 3000
   ```

3. Check Windows firewall:
   - Allow Docker through firewall

4. Try 127.0.0.1 instead of localhost:
   - http://127.0.0.1:3000

---

### Issue: WSL can't connect to Docker

**Symptoms:**
```
Cannot connect to Docker daemon at unix:///var/run/docker.sock
```

**Solution:**
1. Docker Desktop → Settings → Resources → WSL Integration
2. Enable integration with Ubuntu
3. Restart WSL: `wsl --shutdown`

---

## Data Issues

### Issue: Logs not appearing in Elasticsearch

**Debug steps:**

1. Check Kafka has messages:
   ```bash
   # Kafka UI: http://localhost:8080
   # Look for messages in network-logs topic
   ```

2. Check Logstash is consuming:
   ```bash
   docker compose logs logstash | grep "Subscribed to topic"
   ```

3. Check Elasticsearch index exists:
   ```bash
   curl "localhost:9200/_cat/indices?v"
   ```

4. Query Elasticsearch directly:
   ```bash
   curl "localhost:9200/network-logs-*/_search?pretty&size=1"
   ```

---

### Issue: Data loss / messages missing

**Causes:**

1. **Kafka retention**: Messages expired
   ```bash
   # Check retention (default 7 days)
   # Increase in docker-compose.yml:
   KAFKA_LOG_RETENTION_HOURS: 168
   ```

2. **Logstash dropping messages**: Check dead letter queue
   ```bash
   # Check topic: network-logs-dead-letter
   ```

3. **Elasticsearch rejecting**: Check cluster health
   ```bash
   curl "localhost:9200/_cluster/health?pretty"
   ```

---

## Python Issues

### Issue: Package installation fails

**Symptoms:**
```
ERROR: Could not build wheels for xyz
```

**Solutions:**

1. Update pip:
   ```bash
   pip install --upgrade pip setuptools wheel
   ```

2. Install build tools:
   ```bash
   sudo apt-get install python3-dev build-essential
   ```

3. Use virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

---

### Issue: Import errors

**Symptoms:**
```python
ModuleNotFoundError: No module named 'kafka'
```

**Solution:**
```bash
# Make sure you're in venv
source venv/bin/activate

# Check where pip installs
pip show kafka-python

# Reinstall
pip install --force-reinstall kafka-python
```

---

## Getting More Help

### 1. Check logs
```bash
# All services
docker compose logs

# Specific service
docker compose logs -f kafka

# Last 100 lines
docker compose logs --tail 100
```

### 2. Check container health
```bash
docker compose ps
docker inspect <container_name>
```

### 3. Check system resources
```bash
# Docker stats
docker stats

# System resources (WSL)
htop
```

### 4. Enable debug logging

#### Logstash
```yaml
# infrastructure/logstash/config/logstash.yml
log.level: debug
```

#### Python
```python
# Set in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Emergency Reset

If everything is broken:

```bash
# Stop everything
docker compose down -v

# Remove all Docker data
docker system prune -a --volumes

# Restart Docker Desktop
# (Windows: right-click → Quit, then start again)

# Start fresh
docker compose up -d

# Wait 2 minutes for all services to start
docker compose ps
```

---

## Still Stuck?

1. **Check documentation**: See `docs/` folder for detailed guides
2. **Search logs**: Look for specific error messages
3. **Community**: Search GitHub issues for similar problems
4. **Start simple**: Comment out complex parts, add back incrementally

**Pro tip**: Keep a log of what you tried - helps debug faster!

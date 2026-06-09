# 🎯 Getting Started with Smart NOC

Welcome! This guide will help you navigate the documentation and start building your Smart NOC POC.

---

## 📖 Documentation Structure

```
smart-noc/
├── 📄 README.md                 ⭐ Start here - Complete overview
├── 📄 QUICKSTART.md             🚀 5-minute quick start
├── 📄 docker-compose.yml         🐳 Infrastructure definition
├── 📄 .gitignore
│
├── 📁 docs/
│   ├── 📄 PHASE-0-SETUP.md      👉 Step 1: Environment setup
│   ├── 📄 PHASE-1-LOG-PIPELINE.md   👉 Step 2: Build log pipeline
│   ├── 📄 PHASE-2-ANOMALY-DETECTION.md 👉 Step 3: Add anomaly detection
│   ├── 📄 ARCHITECTURE.md       🏗️ System architecture
│   ├── 📄 TECHNOLOGY-DECISIONS.md  🤔 Why we chose each tech
│   ├── 📄 ROADMAP.md            📅 Complete timeline (15-20 days)
│   └── 📄 TROUBLESHOOTING.md    🆘 Common issues & solutions
│
├── 📁 services/
│   └── log-generator/           🎲 Mock network device logs
│       ├── generate_logs.py
│       └── requirements.txt
│
├── 📁 infrastructure/
│   └── logstash/                ⚙️ Log parsing configuration
│       ├── config/
│       └── pipeline/
│
├── 📁 scripts/
│   ├── setup.ps1                💻 Windows setup verification
│   └── verify-setup.sh          🐧 Linux setup verification
│
└── 📁 configs/
    └── grafana/                 📊 Dashboards (will be added)
```

---

## 🚦 Three Ways to Start

### 1️⃣ Quick Start (For the Impatient)
**Time: 15 minutes**

```bash
# 1. Start services
cd ~/ng-iam/smart-noc
docker compose up -d

# 2. Install Python deps
source venv/bin/activate
pip install -r services/log-generator/requirements.txt

# 3. Generate logs
python services/log-generator/generate_logs.py

# 4. View results
# Open: http://localhost:8080 (Kafka UI)
```

👉 **Follow**: [QUICKSTART.md](QUICKSTART.md)

---

### 2️⃣ Guided Path (Recommended)
**Time: 1-3 weeks**

Follow phases in order:

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
  1 day    2-3 days   2-3 days   3-4 days   2-3 days   3-4 days   2-3 days
```

#### Start Here:
1. **Read**: [README.md](README.md) - Understand the big picture
2. **Setup**: [docs/PHASE-0-SETUP.md](docs/PHASE-0-SETUP.md) - Prepare environment
3. **Build**: [docs/PHASE-1-LOG-PIPELINE.md](docs/PHASE-1-LOG-PIPELINE.md) - First working system
4. **Continue**: Follow phases 2-6

👉 **Follow**: [docs/ROADMAP.md](docs/ROADMAP.md)

---

### 3️⃣ Deep Dive (For Architects)
**Time: Variable**

Understand the system before building:

1. **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
2. **Technology Choices**: [docs/TECHNOLOGY-DECISIONS.md](docs/TECHNOLOGY-DECISIONS.md)
3. **Design Rationale**: [README.md](README.md) - "Why" section
4. **Then**: Start Phase 0

---

## 🎯 Your First 30 Minutes

### Minute 0-10: Understand the Project
- Read [README.md](README.md) introduction
- Review architecture diagram in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Skim [QUICKSTART.md](QUICKSTART.md)

### Minute 10-20: Verify Setup
**Windows (PowerShell):**
```powershell
cd C:\Users\baisingh\ng-iam\smart-noc
.\scripts\setup.ps1
```

**WSL/Linux:**
```bash
cd ~/ng-iam/smart-noc
bash scripts/verify-setup.sh
```

### Minute 20-30: Start Services
```bash
# In WSL terminal
cd ~/ng-iam/smart-noc
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

**Success?** All services show "Up (healthy)" ✅

---

## 📚 Key Documents by Purpose

### Planning & Understanding
- 📄 [README.md](README.md) - Project overview
- 📄 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - How it works
- 📄 [docs/ROADMAP.md](docs/ROADMAP.md) - Timeline & milestones

### Implementation
- 📄 [docs/PHASE-0-SETUP.md](docs/PHASE-0-SETUP.md) - Environment setup
- 📄 [docs/PHASE-1-LOG-PIPELINE.md](docs/PHASE-1-LOG-PIPELINE.md) - Build pipeline
- 📄 [docs/PHASE-2-ANOMALY-DETECTION.md](docs/PHASE-2-ANOMALY-DETECTION.md) - Add intelligence

### Reference
- 📄 [docs/TECHNOLOGY-DECISIONS.md](docs/TECHNOLOGY-DECISIONS.md) - Tech stack explained
- 📄 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Fix common issues

### Quick Access
- 📄 [QUICKSTART.md](QUICKSTART.md) - Fast track guide

---

## 🎓 Learning Resources

### If You're New To...

**Docker & Containers**
- [Docker in 100 seconds](https://www.youtube.com/watch?v=Gjnup-PuquQ)
- [Docker Compose Tutorial](https://docs.docker.com/compose/gettingstarted/)

**Kafka**
- [Kafka in 5 minutes](https://www.youtube.com/watch?v=aj9CDZm0Glc)
- [Kafka Quickstart](https://kafka.apache.org/quickstart)

**Python**
- [Python Refresher](https://learnxinyminutes.com/docs/python/)

**Network Operations**
- [NOC Fundamentals](https://en.wikipedia.org/wiki/Network_operations_center)

---

## 🚨 When You Get Stuck

1. **Check**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common solutions
2. **Logs**: `docker compose logs <service-name>`
3. **Health**: `docker compose ps`
4. **Reset**: `docker compose down -v && docker compose up -d`

---

## 💡 Tips for Success

### ✅ DO:
- Follow phases in order
- Test after each step
- Read error messages carefully
- Keep notes of changes
- Start with low log rates

### ❌ DON'T:
- Skip prerequisite checks
- Try to build everything at once
- Ignore warnings
- Optimize prematurely
- Run at max rate immediately

---

## 🎯 Success Criteria by Phase

### Phase 1 Complete?
- [ ] Services running: `docker compose ps`
- [ ] Logs visible in Kafka UI: http://localhost:8080
- [ ] Data in Elasticsearch: `curl localhost:9200/network-logs-*/_search`
- [ ] Can generate 100+ logs/sec

### Phase 2 Complete?
- [ ] Anomalies detected automatically
- [ ] False positive rate < 10%
- [ ] Baseline collected
- [ ] Anomalies in dedicated Kafka topic

### Continue...
See individual phase documents for completion criteria.

---

## 🗺️ Navigation Map

```
Start Here
    ▼
┌───────────────┐
│   README.md   │ ◄─── Overview & motivation
└───────┬───────┘
        │
        ▼
┌───────────────┐
│PHASE-0-SETUP │ ◄─── Install tools
└───────┬───────┘
        │
        ▼
┌────────────────────┐
│PHASE-1-LOG-PIPELINE│ ◄─── First working system
└───────┬────────────┘
        │
        ▼
    [Phases 2-6]
        │
        ▼
┌───────────────┐
│  🎉 Complete! │
└───────────────┘

Need help?
    ▼
┌─────────────────┐
│TROUBLESHOOTING │
└─────────────────┘
```

---

## 🎬 Quick Command Reference

```bash
# Start system
docker compose up -d

# Stop system
docker compose down

# View logs
docker compose logs -f

# Restart service
docker compose restart <service>

# Generate logs
python services/log-generator/generate_logs.py

# Check health
docker compose ps

# Clean restart
docker compose down -v && docker compose up -d
```

---

## 📞 Support Resources

### Documentation
- Main README: [README.md](README.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Troubleshooting: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

### External Resources
- Kafka Docs: https://kafka.apache.org/documentation/
- Docker Docs: https://docs.docker.com/
- Logstash Docs: https://www.elastic.co/guide/en/logstash/

---

## 🎯 What's Your Goal?

### Just Want to Demo?
→ Follow [QUICKSTART.md](QUICKSTART.md) + Phase 1

### Build Complete POC?
→ Follow all phases in [docs/ROADMAP.md](docs/ROADMAP.md)

### Understand Architecture?
→ Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) first

### Learn the Technologies?
→ Read [docs/TECHNOLOGY-DECISIONS.md](docs/TECHNOLOGY-DECISIONS.md)

### Production Deployment?
→ Complete POC first, then extend

---

## ✨ Ready to Start?

**Next Step**: Choose your path above and begin!

**Recommended**: 
1. Run setup verification: `.\scripts\setup.ps1` (Windows) or `bash scripts/verify-setup.sh` (WSL)
2. Read: [docs/PHASE-0-SETUP.md](docs/PHASE-0-SETUP.md)
3. Start building!

**Good luck! 🚀**

---

## 📊 Project Stats

- **Total Implementation Time**: 15-20 days
- **Lines of Documentation**: 5000+
- **Phases**: 6 + setup
- **Technologies**: 10+
- **Estimated Cost**: $0 (all open-source)

---

**Questions?** Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) first!

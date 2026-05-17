# Technology Decisions & Alternatives

## 🎯 Core Decisions

This document explains why each technology was chosen and provides alternatives.

---

## 1. Message Broker: Apache Kafka

### ✅ Chosen: Apache Kafka (KRaft mode)

**Why:**
- Industry standard for log streaming
- High throughput (1M+ messages/sec)
- Built-in durability and replay capability
- Decouples producers from consumers
- KRaft mode = no ZooKeeper dependency (lighter)

**Laptop optimizations:**
- Single broker (no cluster)
- Reduced heap size (512MB)
- 3 partitions per topic

### 🔄 Alternatives

| Alternative | Pros | Cons | When to use |
|-------------|------|------|-------------|
| **Redis Streams** | Very lightweight, simple | No true persistence, limited scale | Quick POC, <10k msgs/sec |
| **RabbitMQ** | Easy to learn, good UI | Lower throughput than Kafka | Message routing focus |
| **Upstash Kafka** | Managed, free tier | Requires internet | Cloud-first approach |
| **NATS** | Extremely lightweight | Less mature ecosystem | Microservices focus |

**Recommendation for laptop**: Stick with Kafka unless memory constrained, then use Redis Streams.

---

## 2. Log Parsing: Logstash

### ✅ Chosen: Logstash

**Why:**
- Rich plugin ecosystem
- Powerful grok patterns for log parsing
- Native Kafka and Elasticsearch integration
- Well documented

**Configuration:**
- 512MB heap
- 2 pipeline workers

### 🔄 Alternatives

| Alternative | Pros | Cons | When to use |
|-------------|------|------|-------------|
| **Apache Flink** | Real-time streaming, stateful | More complex, higher overhead | Complex event processing |
| **Vector** | Rust-based, very fast | Smaller ecosystem | Performance-critical |
| **Fluentd** | Ruby-based, lightweight | Slower than alternatives | Container logs |
| **Custom Python** | Full control, easy to debug | No built-in features | Learning/prototyping |

**Recommendation**: Start with Logstash. Move to Flink in Phase 3 for correlation.

---

## 3. Storage: Elasticsearch

### ✅ Chosen: Elasticsearch

**Why:**
- Full-text search on logs
- Time-series optimized
- Native Grafana/Kibana integration
- Industry standard

**Configuration:**
- Single node
- 512MB heap
- No security (localhost only)

### 🔄 Alternatives

| Alternative | Pros | Cons | When to use |
|-------------|------|------|-------------|
| **PostgreSQL + TimescaleDB** | Relational, less memory | No full-text search | Structured data focus |
| **ClickHouse** | Extremely fast queries | Harder to learn | Analytics-heavy |
| **MongoDB** | Simple, flexible schema | Not optimized for logs | Document storage |
| **SQLite + FTS** | Zero config, file-based | Not scalable | Quick testing |

**Recommendation**: Use Elasticsearch. If memory constrained, use PostgreSQL + TimescaleDB.

---

## 4. Orchestration: Temporal

### ✅ Chosen: Temporal

**Why:**
- Best-in-class workflow engine
- Built-in retry logic and state management
- Perfect for long-running network operations
- Strong typing with Go/Python SDKs

**Will implement in**: Phase 6

### 🔄 Alternatives

| Alternative | Pros | Cons | When to use |
|-------------|------|------|-------------|
| **Apache Airflow** | DAG-based, well-known | Cron-focused, not event-driven | Batch processing |
| **Prefect** | Modern Python, easy | Newer, smaller ecosystem | Python-only shops |
| **Cadence** | Temporal predecessor | Less active development | If already using |
| **Custom state machine** | Simple, full control | Manual retry/state logic | Very simple workflows |

**Recommendation**: Use Temporal. It's perfect for this use case.

---

## 5. LLM: Ollama (Local)

### ✅ Chosen: Ollama + Llama 3 (8B)

**Why:**
- Runs locally (no API costs)
- Privacy (no data sent to cloud)
- Good performance on laptop
- Easy to use

**Will implement in**: Phase 4

### 🔄 Alternatives

| Alternative | Pros | Cons | When to use |
|-------------|------|------|-------------|
| **OpenAI GPT-4** | Best quality, fast | Costs money, cloud only | Production systems |
| **Anthropic Claude** | Good reasoning | Costs money | Complex diagnosis |
| **Azure OpenAI** | Enterprise support | Costs money, setup | Corporate environments |
| **Mistral 7B** | Lighter than Llama | Slightly lower quality | Very resource constrained |
| **GPT4All** | GUI included | Windows-focused | Desktop app preference |

**Recommendation**: 
- **Development**: Ollama (free)
- **Production**: OpenAI GPT-4 (better quality)

**Laptop requirements for Ollama:**
- 8GB RAM minimum
- 16GB recommended
- No GPU required (but helps)

---

## 6. Vector Database: ChromaDB

### ✅ Chosen: ChromaDB

**Why:**
- Embedded mode (no separate server)
- Simple Python API
- Lightweight
- Good for retrieval (past incident lookup)

**Will implement in**: Phase 4

### 🔄 Alternatives

| Alternative | Pros | Cons | When to use |
|-------------|------|------|-------------|
| **Weaviate** | More features, scalable | Separate server needed | Production scale |
| **Pinecone** | Managed, fast | Costs money, cloud-only | No infra management |
| **Qdrant** | Fast, Rust-based | Smaller ecosystem | Performance critical |
| **FAISS** | Facebook's library, fast | No persistence built-in | Research/prototyping |
| **Milvus** | Feature-rich | Heavy, complex | Large scale |

**Recommendation**: ChromaDB for POC. Weaviate for production.

---

## 7. Policy Engine: Open Policy Agent (OPA)

### ✅ Chosen: OPA

**Why:**
- Industry standard for policy-as-code
- Rego language for rules
- Fast evaluation
- Separate policy from code

**Will implement in**: Phase 5

### 🔄 Alternatives

| Alternative | Pros | Cons | When to use |
|-------------|------|------|-------------|
| **Custom Python rules** | Simple, no new language | Hard to maintain | Very simple rules |
| **AWS IAM/Azure Policy** | Cloud-native | Cloud-specific | Cloud deployments |
| **Casbin** | Multi-language | Less common | Specific auth needs |
| **JSON Schema** | Simple validation | Not for complex logic | Basic validation |

**Recommendation**: Use OPA. Industry standard for this use case.

---

## 8. Automation: Ansible

### ✅ Chosen: Ansible

**Why:**
- Network automation standard
- Agentless (SSH-based)
- Large community
- Many network modules

**Will implement in**: Phase 5

### 🔄 Alternatives

| Alternative | Pros | Cons | When to use |
|-------------|------|------|-------------|
| **Python + Netmiko** | Direct control, simple | Manual error handling | Custom scripts |
| **Terraform** | Infrastructure as code | Not for configuration | Infra provisioning |
| **SaltStack** | Fast, event-driven | Requires agent | Large fleets |
| **NAPALM** | Vendor-neutral | Limited actions | Cross-vendor |
| **Custom Go** | Fast, compiled | Write everything | Performance critical |

**Recommendation**: Ansible for network automation.

---

## 9. Graph Database: Neo4j Community

### ✅ Chosen: Neo4j Community Edition

**Why:**
- Best graph database
- Cypher query language (intuitive)
- Free community edition
- Good for device topology

**Will implement in**: Phase 3

### 🔄 Alternatives

| Alternative | Pros | Cons | When to use |
|-------------|------|------|-------------|
| **Custom graph (Python)** | Simple, lightweight | Manual implementation | Small topologies |
| **Amazon Neptune** | Managed | Cloud-only, costs | AWS deployments |
| **ArangoDB** | Multi-model | Complex | Need document + graph |
| **NetworkX (Python)** | Easy, Pythonic | In-memory only | Prototyping |
| **JanusGraph** | Scalable | Heavy, complex | Very large graphs |

**Recommendation**: 
- **POC**: NetworkX (Python library)
- **Production**: Neo4j

---

## 🎯 Recommended Stack by Environment

### 💻 Laptop POC (What we're building)

```yaml
Ingestion: Kafka (KRaft)
Parsing: Logstash
Storage: Elasticsearch
Orchestration: Temporal
LLM: Ollama + Llama 3
Vector DB: ChromaDB
Policy: OPA
Automation: Ansible
Graph: NetworkX
```

**Total RAM**: ~8-10GB  
**Total Disk**: ~25GB

---

### ☁️ Cloud Production

```yaml
Ingestion: Confluent Kafka / AWS MSK
Parsing: Apache Flink
Storage: Elasticsearch Service / OpenSearch
Orchestration: Temporal Cloud
LLM: OpenAI GPT-4
Vector DB: Weaviate Cloud / Pinecone
Policy: OPA
Automation: Ansible
Graph: Neo4j Aura
```

**Cost**: ~$500-1000/month (small scale)

---

### 🏢 Enterprise Production

```yaml
Ingestion: Kafka (multi-broker cluster)
Parsing: Apache Flink (cluster)
Storage: Elasticsearch (cluster)
Orchestration: Temporal (self-hosted cluster)
LLM: Azure OpenAI / Private deployment
Vector DB: Weaviate (self-hosted)
Policy: OPA
Automation: Ansible Tower / AWX
Graph: Neo4j Enterprise
```

---

## 🔧 When to Change Technologies

### Switch from Kafka to Redis:
- Memory < 4GB available
- Log rate < 10k/sec
- No replay requirements

### Switch from Elasticsearch to PostgreSQL:
- Need strong ACID guarantees
- Memory < 2GB for storage
- Structured queries only

### Switch from Ollama to OpenAI:
- Diagnosis quality insufficient
- No GPU available
- Budget allows ($50-200/month)

### Switch from Logstash to Flink:
- Need windowing/aggregation
- Complex event processing
- Stateful transformations

---

## 📊 Decision Matrix

| Concern | Solution | Alternative |
|---------|----------|-------------|
| Low memory | Redis + SQLite | Cloud services |
| No internet | All local | Accept limitations |
| Windows-only | Docker Desktop | Cloud-based |
| Learning curve | Start simple | Use managed services |
| Cost sensitive | All open-source | Hybrid (some cloud) |
| Time sensitive | Cloud managed | Accept higher cost |

---

## 🎓 Learning Resources

- **Kafka**: Confluent tutorials
- **Temporal**: learn.temporal.io
- **Ollama**: ollama.ai/docs
- **OPA**: openpolicyagent.org/docs
- **Ansible**: docs.ansible.com/network

---

**💡 Pro Tip**: Don't optimize prematurely. Start with the recommended stack and change only when you hit actual bottlenecks.

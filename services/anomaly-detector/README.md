# Smart NOC - Anomaly Detection Service

AI-powered anomaly detection using **hybrid approach**: rule-based + machine learning (Isolation Forest).

## Architecture

```
Network Logs (Kafka) 
    ↓
Anomaly Detector
 ├─ Rule-Based Detectors (4 rules)
 │   ├─ Interface Flapping
 │   ├─ Auth Brute Force  
 │   ├─ High CPU Sustained
 │   └─ BGP Instability
 │
 └─ ML-Based Detector (Isolation Forest)
     └─ Unsupervised anomaly detection
    ↓
Anomalies (Kafka)
```

## Features

### Rule-Based Detection
- **Interface Flapping**: Detects >5 state changes in 5 minutes
- **Auth Brute Force**: Detects >10 failed logins in 2 minutes
- **High CPU**: Detects CPU >80% for 10+ minutes
- **BGP Instability**: Detects >3 BGP state changes in 5 minutes

### ML-Based Detection (Isolation Forest)
- **Unsupervised learning**: No training data required
- **Auto-training**: Trains every 60 minutes on recent logs
- **Feature extraction**: 12 features including severity, timing, event types
- **Confidence scoring**: Provides anomaly confidence (0-1)

## Configuration

Edit `config.yaml` to adjust:
- Detection thresholds
- Sliding window sizes
- ML model parameters
- Kafka topics

## Testing

### Generate Specific Scenarios

```bash
# Interface flapping (10 flaps)
cd services/log-generator
python generate_scenarios.py --scenario flapping --count 10

# Auth brute force (15 attempts)
python generate_scenarios.py --scenario brute-force --count 15

# High CPU (5 minutes)
python generate_scenarios.py --scenario high-cpu --duration 300

# BGP instability (5 changes)
python generate_scenarios.py --scenario bgp-unstable --count 5

# Mixed chaos (2 minutes of random anomalies)
python generate_scenarios.py --scenario chaos --duration 120
```

## Output Format

Anomalies published to `anomalies` Kafka topic:

```json
{
  "anomaly_type": "INTERFACE_FLAPPING",
  "severity": "HIGH",
  "device_id": "core-router-01",
  "interface": "GigabitEthernet0/1",
  "event_count": 10,
  "window_minutes": 5,
  "detection_method": "rule",
  "confidence": 1.0,
  "timestamp": "2026-04-24T12:00:00",
  "details": "Interface changed state 10 times in 5 minutes"
}
```

## Monitoring

Check service logs:
```bash
docker compose logs -f anomaly-detector
```

Statistics printed every 60 seconds showing:
- Logs processed
- Anomalies detected
- Rule vs ML detection counts
- ML model training status

"""
LLM Diagnosis Service - Configuration
Phase 4: AI-Powered Root Cause Analysis
"""

import os
from typing import Optional

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_INPUT_TOPIC = os.getenv('KAFKA_INPUT_TOPIC', 'incidents')
KAFKA_OUTPUT_TOPIC = os.getenv('KAFKA_OUTPUT_TOPIC', 'incidents-diagnosed')
KAFKA_CONSUMER_GROUP = os.getenv('KAFKA_CONSUMER_GROUP', 'llm-diagnosis-service')
KAFKA_AUTO_OFFSET_RESET = os.getenv('KAFKA_AUTO_OFFSET_RESET', 'latest')  # 'earliest' for backfill

# PostgreSQL Configuration
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'smart_noc')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'noc_admin')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'noc_password')

# LLM Provider Configuration
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai')  # 'openai', 'anthropic', 'azure'
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4-turbo-preview')  # or 'claude-3-opus-20240229'
LLM_API_KEY = os.getenv('LLM_API_KEY', '')  # Required!
LLM_API_BASE = os.getenv('LLM_API_BASE', '')  # Optional: for Azure OpenAI
LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '2000'))
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))  # Lower = more focused
LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '30'))  # seconds

# Diagnosis Configuration
DIAGNOSIS_MIN_CONFIDENCE = float(os.getenv('DIAGNOSIS_MIN_CONFIDENCE', '0.3'))  # Reject below this
DIAGNOSIS_CACHE_TTL = int(os.getenv('DIAGNOSIS_CACHE_TTL', '3600'))  # Cache similar incidents (seconds)
DIAGNOSIS_RETRY_ATTEMPTS = int(os.getenv('DIAGNOSIS_RETRY_ATTEMPTS', '3'))
DIAGNOSIS_BATCH_SIZE = int(os.getenv('DIAGNOSIS_BATCH_SIZE', '1'))  # Process N incidents at once
DIAGNOSIS_DELAY_SECONDS = int(os.getenv('DIAGNOSIS_DELAY_SECONDS', '5'))  # Wait N seconds after incident creation

# Context Configuration  
CONTEXT_MAX_ANOMALIES = int(os.getenv('CONTEXT_MAX_ANOMALIES', '50'))  # Max anomalies to include in context
CONTEXT_HISTORICAL_INCIDENTS = int(os.getenv('CONTEXT_HISTORICAL_INCIDENTS', '5'))  # Similar past incidents
CONTEXT_DEVICE_HISTORY_HOURS = int(os.getenv('CONTEXT_DEVICE_HISTORY_HOURS', '24'))  # Device incident history

# Vector Service Configuration (Week 2: Enhanced Context)
VECTOR_SERVICE_ENABLED = os.getenv('VECTOR_SERVICE_ENABLED', 'true').lower() == 'true'
VECTOR_CHROMADB_HOST = os.getenv('CHROMADB_HOST', 'chromadb')
VECTOR_CHROMADB_PORT = int(os.getenv('CHROMADB_PORT', '8000'))
VECTOR_SIMILAR_INCIDENTS_COUNT = int(os.getenv('VECTOR_SIMILAR_INCIDENTS_COUNT', '3'))  # Top N similar incidents
VECTOR_KB_ARTICLES_COUNT = int(os.getenv('VECTOR_KB_ARTICLES_COUNT', '2'))  # Top N KB articles
VECTOR_MIN_SIMILARITY = float(os.getenv('VECTOR_MIN_SIMILARITY', '0.60'))  # Minimum similarity threshold (lowered from 0.70 for better recall)

# Phase 2: Remediation Lessons Configuration
REMEDIATION_LESSONS_SOURCE = os.getenv('REMEDIATION_LESSONS_SOURCE', 'chromadb').lower()  # 'sql' or 'chromadb'
REMEDIATION_LESSONS_COUNT = int(os.getenv('REMEDIATION_LESSONS_COUNT', '5'))  # Top N lessons from ChromaDB
REMEDIATION_LESSONS_MIN_SIMILARITY = float(os.getenv('REMEDIATION_LESSONS_MIN_SIMILARITY', '0.50'))  # Minimum similarity for ChromaDB

# Remediation Configuration
REMEDIATION_MAX_STEPS = int(os.getenv('REMEDIATION_MAX_STEPS', '10'))  # Max steps per plan
REMEDIATION_INCLUDE_ESCALATION = os.getenv('REMEDIATION_INCLUDE_ESCALATION', 'true').lower() == 'true'
REMEDIATION_INCLUDE_VERIFICATION = os.getenv('REMEDIATION_INCLUDE_VERIFICATION', 'true').lower() == 'true'

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', 'json')  # 'json' or 'text'

# Feature Flags
ENABLE_DIAGNOSIS = os.getenv('ENABLE_DIAGNOSIS', 'true').lower() == 'true'
ENABLE_REMEDIATION = os.getenv('ENABLE_REMEDIATION', 'true').lower() == 'true'
ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'
ENABLE_COST_TRACKING = os.getenv('ENABLE_COST_TRACKING', 'true').lower() == 'true'

# Database Connection String
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Validation
def validate_config():
    """Validate required configuration"""
    errors = []
    
    if not LLM_API_KEY:
        errors.append("LLM_API_KEY is required (set via environment variable)")
    
    if LLM_PROVIDER not in ['openai', 'anthropic', 'azure']:
        errors.append(f"Invalid LLM_PROVIDER: {LLM_PROVIDER} (must be openai, anthropic, or azure)")
    
    if DIAGNOSIS_MIN_CONFIDENCE < 0 or DIAGNOSIS_MIN_CONFIDENCE > 1:
        errors.append(f"DIAGNOSIS_MIN_CONFIDENCE must be between 0 and 1, got {DIAGNOSIS_MIN_CONFIDENCE}")
    
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

# Cost tracking (approximate)
COST_PER_1K_TOKENS = {
    'gpt-4-turbo-preview': {'input': 0.01, 'output': 0.03},
    'gpt-4': {'input': 0.03, 'output': 0.06},
    'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
    'claude-3-opus-20240229': {'input': 0.015, 'output': 0.075},
    'claude-3-sonnet-20240229': {'input': 0.003, 'output': 0.015},
    'claude-3-haiku-20240307': {'input': 0.00025, 'output': 0.00125},
}

def get_estimated_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost for LLM call"""
    if model not in COST_PER_1K_TOKENS:
        return 0.0
    
    costs = COST_PER_1K_TOKENS[model]
    input_cost = (input_tokens / 1000) * costs['input']
    output_cost = (output_tokens / 1000) * costs['output']
    return input_cost + output_cost

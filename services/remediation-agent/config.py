"""
Configuration for remediation agent service
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service
    SERVICE_NAME: str = "remediation-agent"
    SIMULATION_MODE: bool = True  # Set to False when connecting to real devices
    
    # Groq LLM
    GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    KAFKA_CONSUME_TOPIC: str = "incident-diagnoses"  # Where LLM diagnosis publishes
    KAFKA_PRODUCE_TOPIC: str = "incident-remediations"  # Where we publish results
    KAFKA_GROUP_ID: str = "remediation-agent-group"
    
    # PostgreSQL
    POSTGRES_HOST: str = os.getenv('POSTGRES_HOST', 'postgres')
    POSTGRES_PORT: int = int(os.getenv('POSTGRES_PORT', '5432'))
    POSTGRES_USER: str = os.getenv('POSTGRES_USER', 'noc_admin')
    POSTGRES_PASSWORD: str = os.getenv('POSTGRES_PASSWORD', 'noc_password')
    POSTGRES_DB: str = os.getenv('POSTGRES_DB', 'smart_noc')
    
    # Execution settings
    MAX_RETRY_ATTEMPTS: int = 3
    VERIFICATION_WAIT_SECONDS: int = 5
    ENABLE_AUTO_EXECUTION: bool = True  # Set to False to require approval
    
    # Safety guards
    MAX_EXECUTIONS_PER_HOUR: int = 100
    REQUIRE_APPROVAL_ABOVE_SEVERITY: str = "HIGH"  # HIGH, CRITICAL
    
    class Config:
        env_file = ".env"


settings = Settings()

# Contributing to Smart NOC

**Document Date**: June 9, 2026  
**Status**: Active  
**Audience**: Developers, Contributors

---

## 🎯 Overview

Thank you for your interest in contributing to Smart NOC! This autonomous AI-driven Network Operations Center is designed for multi-vendor environments (Cisco, Juniper, HP, Dell, Extreme Networks).

This guide will help you understand our development workflow, coding standards, and contribution process.

---

## 🚀 Quick Start for Contributors

### 1. **Setup Development Environment**

```bash
# Clone repository
git clone <repository-url>
cd smart-noc

# Run setup script
./setup-noc.sh

# Activate virtual environment
source venv/bin/activate

# Verify services are running
docker-compose ps
```

### 2. **Understand the Architecture**

Before contributing, read:
- [Architecture Overview](../02-architecture/2026-05-15_ARCHITECTURE.md)
- [Technology Decisions](../02-architecture/2026-05-10_TECHNOLOGY_DECISIONS.md)
- [Testing Guide](../04-testing/2026-05-25_TESTING_GUIDE.md)

### 3. **Choose Your Contribution Area**

| Area | Services | Technologies |
|------|----------|--------------|
| **LLM Diagnosis** | `services/llm-diagnosis/` | Python, Pydantic, Groq API |
| **Vector Search** | `services/vector-service/` | Python, ChromaDB, FastAPI |
| **Anomaly Detection** | `services/anomaly-detector/` | Python, Scikit-learn, Isolation Forest |
| **Correlation Engine** | `services/correlation-engine/` | Python, Kafka |
| **Remediation** | `services/remediation-agent/` | Python, LangGraph |
| **Frontend** | `services/dashboard/` | React, TypeScript |

---

## 📜 Coding Standards

### Python Code Style

**Follow PEP 8** with these conventions:

```python
# Good: Clear function names, type hints, docstrings
def diagnose_incident(
    incident_id: str,
    context: Dict[str, Any]
) -> DiagnosisResponse:
    """
    Diagnose network incident using LLM and vector search.
    
    Args:
        incident_id: Unique incident identifier
        context: Incident context including logs and metrics
        
    Returns:
        DiagnosisResponse with root cause and remediation plan
    """
    logger.info(f"Diagnosing incident {incident_id}")
    # ... implementation
```

**Key Conventions:**
- Use type hints for all function parameters and return values
- Write docstrings for all public functions
- Use f-strings for string formatting
- Limit line length to 100 characters
- Use meaningful variable names (no single letters except loop counters)

### File Organization

```
services/<service-name>/
├── __init__.py
├── main.py              # FastAPI app or service entry point
├── models.py            # Pydantic models
├── config.py            # Configuration management
├── <service>_client.py  # External API clients
├── <service>_service.py # Business logic
├── utils.py             # Helper functions
└── tests/               # Unit tests
    ├── __init__.py
    ├── test_models.py
    ├── test_service.py
    └── test_integration.py
```

### Logging Standards

Use structured logging with levels:

```python
import logging

logger = logging.getLogger(__name__)

# Error: Something failed
logger.error(f"Failed to diagnose incident {incident_id}: {str(e)}")

# Warning: Something unexpected but handled
logger.warning(f"No similar incidents found for {incident_id}")

# Info: Key milestones
logger.info(f"✓ Diagnosis complete for incident {incident_id}")

# Debug: Detailed information
logger.debug(f"Retrieved {len(results)} KB articles")
```

**Use emoji prefixes for key events:**
- `✓` Success
- `✗` Failure
- `⚠` Warning
- `🧠` LLM operation
- `📊` Metrics/Stats
- `🔍` Search operation

---

## 🔧 Development Workflow

### 1. **Create a Feature Branch**

```bash
git checkout -b feature/your-feature-name
```

**Branch naming conventions:**
- `feature/<feature-name>` - New features
- `bugfix/<bug-description>` - Bug fixes
- `refactor/<component>` - Code refactoring
- `docs/<topic>` - Documentation updates

### 2. **Make Changes**

- Write clean, well-documented code
- Add unit tests for new functionality
- Update documentation if behavior changes
- Follow existing code patterns

### 3. **Test Your Changes**

```bash
# Run unit tests for your service
pytest services/<service-name>/tests/

# Run integration tests
pytest tests/integration/

# Run E2E tests
./scripts/test-e2e.sh
```

### 4. **Commit with Clear Messages**

```bash
git add .
git commit -m "feat: Add Chain-of-Thought reasoning to LLM diagnosis"
```

**Commit message format:**
```
<type>: <subject>

<optional body>

<optional footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Test updates
- `chore`: Maintenance tasks

**Example:**
```
feat: Implement Pydantic structured output validation

- Add DiagnosisResponse and RemediationStep models
- Integrate validation in llm_client
- Add dangerous command blocking
- Update tests for Pydantic validation

Resolves: #123
```

### 5. **Create Pull Request**

- Push your branch to remote
- Create PR with clear description
- Link related issues
- Request review from team

---

## 🧪 Testing Requirements

### Unit Tests

Every new function must have unit tests:

```python
# services/llm-diagnosis/tests/test_models.py
import pytest
from models import DiagnosisResponse, RemediationStep, Priority

def test_diagnosis_response_validation():
    """Test that DiagnosisResponse validates correctly"""
    data = {
        "reasoning": "Step 1: Analyzed logs. Step 2: Identified root cause.",
        "root_cause": "BGP peering issue",
        "confidence": 0.85,
        "remediation_plan": [
            {
                "priority": "HIGH",
                "step": "Reset BGP session",
                "action": "Clear BGP neighbor",
                "command": "clear ip bgp 10.0.0.1",
                "expected_outcome": "BGP session re-established",
                "duration_minutes": 5
            }
        ],
        "affected_components": ["Router-1"],
        "escalation_needed": False
    }
    
    diagnosis = DiagnosisResponse(**data)
    assert diagnosis.confidence == 0.85
    assert len(diagnosis.remediation_plan) == 1
```

### Integration Tests

Test interactions between services:

```python
# tests/integration/test_llm_vector_integration.py
def test_llm_uses_vector_search():
    """Test that LLM diagnosis uses vector search context"""
    # Create test incident
    incident = create_test_incident("BGP flapping")
    
    # Trigger diagnosis
    response = diagnose_incident(incident.id)
    
    # Verify vector search was called
    assert response.reasoning contains "KB-EXT-019"
    assert response.confidence > 0.8
```

### Test Coverage

- Minimum 80% code coverage for new code
- Run coverage report:
  ```bash
  pytest --cov=services/<service-name> --cov-report=html
  ```

---

## 📝 Documentation Requirements

### Code Documentation

- **All public functions**: Docstrings with Args, Returns, Raises
- **Complex logic**: Inline comments explaining "why", not "what"
- **Algorithms**: Link to papers or reference implementations

### Feature Documentation

When adding a new feature, create documentation:

```
docs/03-features/<category>/YYYY-MM-DD_FEATURE_NAME.md
```

**Required sections:**
1. Overview
2. Problem Statement
3. Solution Architecture
4. Implementation Details
5. Configuration
6. Testing/Validation
7. Troubleshooting
8. Future Enhancements

### Update Master Index

Add your new document to [docs/README.md](../README.md) in the appropriate section.

---

## 🐛 Bug Fix Process

### 1. **Reproduce the Bug**

- Create a test case that reproduces the bug
- Document steps to reproduce
- Note expected vs actual behavior

### 2. **Fix the Bug**

- Write the minimal fix necessary
- Ensure the reproduction test now passes
- Check for similar bugs in related code

### 3. **Add Regression Test**

```python
def test_regression_issue_123():
    """Regression test for issue #123: Pydantic validation fails on empty reasoning"""
    # This should not raise ValidationError anymore
    data = {...}  # Previously failing input
    diagnosis = DiagnosisResponse(**data)
    assert diagnosis is not None
```

---

## 🔍 Code Review Guidelines

### For Contributors

When submitting PR:
- Self-review your code first
- Check for debug prints, commented code
- Ensure tests pass locally
- Update documentation
- Keep PR focused (one feature/fix per PR)

### For Reviewers

When reviewing:
- Check code quality and readability
- Verify tests cover edge cases
- Ensure documentation is updated
- Test changes locally if possible
- Provide constructive feedback

**Review checklist:**
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No security vulnerabilities
- [ ] Performance impact considered
- [ ] Error handling adequate

---

## 🏗️ Architecture Principles

### 1. **Microservices Communication**

- Use Kafka for asynchronous messaging
- Use REST APIs for synchronous requests
- Always include error handling and retries

### 2. **Data Storage**

- **PostgreSQL**: Structured data (incidents, diagnoses)
- **ChromaDB**: Vector embeddings for semantic search
- **Kafka**: Event streaming and message passing

### 3. **Error Handling**

Always handle errors gracefully:

```python
try:
    result = llm_client.diagnose(incident)
except LLMAPIError as e:
    logger.error(f"LLM API error: {str(e)}")
    # Fallback to rule-based diagnosis
    result = fallback_diagnosis(incident)
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    raise DiagnosisError(f"Failed to diagnose incident: {str(e)}")
```

### 4. **Configuration Management**

- Use environment variables for sensitive data (API keys)
- Use config files for service configuration
- Never commit secrets to git

---

## 🚀 Release Process

### Version Numbering

We use Semantic Versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version number bumped
- [ ] Tagged in git: `v1.2.3`
- [ ] Deployment tested in staging
- [ ] Production deployment plan ready

---

## 📚 Learning Resources

### Internal Documentation

- [Architecture](../02-architecture/2026-05-15_ARCHITECTURE.md)
- [Features Overview](../03-features/)
- [Testing Guide](../04-testing/2026-05-25_TESTING_GUIDE.md)

### External Resources

**Python Development:**
- [PEP 8 Style Guide](https://pep8.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

**LLM/AI:**
- [Groq API Documentation](https://console.groq.com/docs)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [ChromaDB Documentation](https://docs.trychroma.com/)

**Testing:**
- [Pytest Documentation](https://docs.pytest.org/)
- [Test-Driven Development](https://testdriven.io/)

---

## 🤝 Community

### Getting Help

1. **Documentation**: Check docs/ first
2. **Troubleshooting**: See [Troubleshooting Guide](../05-operations/2026-06-01_TROUBLESHOOTING.md)
3. **Team Chat**: Ask in team channel
4. **GitHub Issues**: Open an issue for bugs/features

### Reporting Issues

**Good issue report:**
```
**Title**: Pydantic validation fails for confidence > 1.0

**Description**:
When LLM returns confidence value > 1.0, Pydantic validation fails 
instead of clamping to 1.0.

**Steps to Reproduce**:
1. Create incident with high confidence scenario
2. Call diagnose_incident()
3. Observe ValidationError

**Expected**: Confidence should clamp to 1.0
**Actual**: ValidationError raised

**Environment**:
- Smart NOC version: 3.0
- Python: 3.11
- Pydantic: 2.6.1

**Logs**:
```
[error log here]
```
```

### Suggesting Features

- Check roadmap first: [Roadmap](../08-roadmap/2026-05-10_ROADMAP.md)
- Open GitHub issue with `[FEATURE]` prefix
- Describe problem, proposed solution, and benefits
- Discuss with team before implementing large features

---

## ⚖️ License

[Include license information]

---

## 📞 Contact

- **Project Lead**: [Name] ([email])
- **Technical Lead**: [Name] ([email])
- **Team Channel**: [Slack/Teams link]

---

**Document Version**: 1.0  
**Last Updated**: June 9, 2026  
**Maintainer**: Smart NOC Team (Extreme Networks)

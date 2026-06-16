# Knowledge Base Expansion Plan

**Target:** 23 → 100+ Extreme Networks Articles  
**Timeline:** 3-5 days (phased approach)  
**Date:** June 15, 2026

---

## Phase 1: Infrastructure Setup (Day 1)

### 1.1 Create KB Fetcher Tool

**Script:** `scripts/kb_fetcher.py`

```
Purpose: Fetch and parse Extreme Networks articles
Input: Article URLs from ExtremePortal
Output: Structured JSON files ready for ChromaDB import
```

**Features:**
- HTTP requests with error handling
- HTML parsing (BeautifulSoup/lxml)
- Content extraction (title, symptoms, commands, solutions)
- Rate limiting (respect Extreme's servers)
- Caching (avoid re-fetching)

### 1.2 Create KB Article Validator

**Script:** `scripts/kb_validator.py`

```
Purpose: Validate article structure before ChromaDB import
Checks:
  - Required fields present (title, vendor, platform, category)
  - Command syntax valid (EXOS pattern matching)
  - Metadata completeness
  - Text quality (no HTML artifacts, proper formatting)
```

### 1.3 Create ChromaDB Bulk Importer

**Script:** `scripts/kb_bulk_import.py`

```
Purpose: Load validated articles into ChromaDB
Features:
  - Batch processing (10-50 articles at once)
  - Duplicate detection (skip if article exists)
  - Embedding generation (all-MiniLM-L6-v2)
  - Progress tracking
  - Rollback on error
```

---

## Phase 2: Article Collection Strategy (Day 1-2)

### 2.1 Article Categories & Target URLs

**Interface Issues (30 articles)**
```
Search Queries:
- "EXOS interface flapping"
- "EXOS port down troubleshooting"
- "EXOS SFP issues"
- "EXOS link down"
- "EXOS speed duplex mismatch"
- "EXOS port statistics errors"
```

**Routing Issues (25 articles)**
```
Search Queries:
- "EXOS BGP troubleshooting"
- "EXOS OSPF neighbor down"
- "EXOS routing issues"
- "EXOS BGP session failure"
- "EXOS OSPF adjacency"
- "EXOS static route"
```

**Switching Issues (20 articles)**
```
Search Queries:
- "EXOS VLAN troubleshooting"
- "EXOS STP loop"
- "EXOS LAG configuration"
- "EXOS MLAG issues"
- "EXOS EAPS troubleshooting"
- "EXOS MAC address learning"
```

**Performance Issues (15 articles)**
```
Search Queries:
- "EXOS high CPU utilization"
- "EXOS memory exhaustion"
- "EXOS performance troubleshooting"
- "EXOS buffer issues"
- "EXOS process high CPU"
```

**Security Issues (10 articles)**
```
Search Queries:
- "EXOS authentication failure"
- "EXOS 802.1X troubleshooting"
- "EXOS RADIUS issues"
- "EXOS port security"
- "EXOS ACL troubleshooting"
```

### 2.2 Article URL Collection Method

**Option A: Manual Curation (Recommended for Phase 1)**
1. Search ExtremePortal for each query
2. Copy top 3-5 most relevant article URLs
3. Create `kb_sources/extreme_urls.txt`:
```
https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408  # BGP Configuration
https://extreme-networks.my.site.com/ExtrArticleDetail?an=000079504  # BGP Troubleshooting
https://extreme-networks.my.site.com/ExtrArticleDetail?an=000103823  # BGP Default Route
...
```

**Option B: Semi-Automated (Future)**
- Script searches ExtremePortal programmatically
- Filters by relevance score
- Human review before import

---

## Phase 3: Content Fetching & Parsing (Day 2-3)

### 3.1 Fetch Workflow

```bash
# Step 1: Read URL list
python scripts/kb_fetcher.py --input kb_sources/extreme_urls.txt \
                              --output kb_sources/raw_articles/

# Output: kb_sources/raw_articles/000122408.html, 000079504.html, etc.
```

### 3.2 Parse Workflow

```bash
# Step 2: Parse HTML to structured JSON
python scripts/kb_parser.py --input kb_sources/raw_articles/ \
                             --output kb_sources/parsed_articles/

# Output: kb_sources/parsed_articles/000122408.json
```

**JSON Structure:**
```json
{
  "article_id": "KB-EXOS-BGP-001",
  "source_url": "https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408",
  "title": "How To: Configure BGP on Switch Engine (EXOS)",
  "vendor": "Extreme Networks",
  "platform": "EXOS",
  "category": "routing",
  "subcategory": "BGP",
  "symptoms": [
    "BGP neighbor not establishing",
    "BGP session down",
    "Routes not being advertised"
  ],
  "root_causes": [
    "Incorrect AS number configuration",
    "Loopback interface misconfiguration",
    "Missing route to neighbor's loopback",
    "Authentication mismatch"
  ],
  "diagnostic_commands": [
    "show bgp",
    "show bgp neighbor",
    "show bgp routes all",
    "show iproute",
    "show configuration bgp"
  ],
  "remediation_steps": [
    {
      "step": 1,
      "description": "Verify BGP configuration",
      "commands": ["show configuration bgp"],
      "expected_output": "Check AS number, router ID"
    },
    {
      "step": 2,
      "description": "Check BGP neighbor status",
      "commands": ["show bgp neighbor"],
      "expected_output": "State should be Established"
    },
    {
      "step": 3,
      "description": "Verify loopback reachability",
      "commands": ["ping <neighbor_loopback_ip>"],
      "expected_output": "Successful ping response"
    }
  ],
  "configuration_example": {
    "scenario": "iBGP between R10 and R11",
    "commands": [
      "configure bgp AS-number 100",
      "configure bgp routerid 1.1.1.1",
      "create bgp neighbor 2.2.2.2 remote-AS-number 100",
      "configure bgp neighbor 2.2.2.2 source-interface ipaddress 1.1.1.1",
      "enable bgp neighbor 2.2.2.2",
      "enable bgp"
    ]
  },
  "related_articles": ["KB-EXOS-BGP-002", "KB-EXOS-ROUTING-001"],
  "keywords": ["BGP", "routing", "neighbor", "AS", "loopback", "iBGP", "eBGP"],
  "last_updated": "2025-04-16",
  "confidence_tags": {
    "official_source": true,
    "tested": true,
    "version_specific": "EXOS 32.7.1+"
  }
}
```

### 3.3 Validation

```bash
# Step 3: Validate parsed articles
python scripts/kb_validator.py --input kb_sources/parsed_articles/ \
                                --output kb_sources/validated_articles/

# Check:
# - All required fields present
# - Commands are valid EXOS syntax
# - No HTML artifacts
# - Proper JSON structure
```

---

## Phase 4: ChromaDB Import (Day 3)

### 4.1 Import Workflow

```bash
# Step 4: Import to ChromaDB
python scripts/kb_bulk_import.py --input kb_sources/validated_articles/ \
                                  --collection kb_articles \
                                  --batch-size 20

# Output:
# - Loaded 100 articles
# - 0 duplicates skipped
# - 0 errors
# - Time: 45 seconds
```

### 4.2 Verify Import

```python
# Check ChromaDB collection
import chromadb
client = chromadb.HttpClient(host='localhost', port=8000)
collection = client.get_collection('kb_articles')

# Query count
print(f"Total articles: {collection.count()}")  # Should be 123 (23 existing + 100 new)

# Test search
results = collection.query(
    query_texts=["BGP neighbor down"],
    n_results=5,
    where={"vendor": "Extreme Networks", "platform": "EXOS"}
)
print(results)
```

---

## Phase 5: Testing & Validation (Day 4)

### 5.1 End-to-End Test

**Test Case 1: BGP Session Down**
```bash
# Generate test incident
python scripts/test-incident-generator.py --type BGP_SESSION_DOWN \
                                           --device 10.139.38.188 \
                                           --interface N/A

# Expected LLM Output:
# - Root Cause: BGP neighbor not reachable / AS mismatch / Authentication failure
# - Commands: show bgp, show bgp neighbor, show iproute
# - Confidence: >0.85 (improved from 0.70)
```

**Test Case 2: Interface Flapping**
```bash
# Generate test incident
python scripts/test-incident-generator.py --type INTERFACE_FLAPPING \
                                           --device 10.139.38.188 \
                                           --interface 1:55

# Expected LLM Output:
# - Root Cause: SFP issues / Cable problems / Duplex mismatch
# - Commands: show port 1:55 information detail, show port 1:55 statistics
# - Confidence: >0.85
```

### 5.2 Quality Metrics

**Measure Before/After:**
```sql
-- Average confidence score
SELECT AVG(confidence_score) 
FROM incidents 
WHERE created_at > '2026-06-15'  -- After KB expansion
AND status = 'DIAGNOSED';

-- Expected: 0.70 → 0.85+ (21% improvement)
```

**Command Specificity:**
```python
# Count vendor-specific commands in remediation plans
# Before: 60% generic (show interface), 40% EXOS-specific (show port X:Y)
# After: 90%+ EXOS-specific
```

---

## Phase 6: Iterative Expansion (Day 5+)

### 6.1 Identify Gaps

```sql
-- Find incident types with low confidence scores
SELECT incident_type, AVG(confidence_score), COUNT(*)
FROM incidents
WHERE confidence_score < 0.80
GROUP BY incident_type
ORDER BY COUNT(*) DESC;
```

**Example Output:**
```
incident_type              | avg_confidence | count
---------------------------+---------------+-------
AUTHENTICATION_ISSUE       | 0.65          | 45
PERFORMANCE_ISSUE          | 0.68          | 32
VLAN_CONNECTIVITY_ISSUE    | 0.72          | 28
```

**Action:** Search for more articles in these categories

### 6.2 Add Articles for Low-Confidence Areas

```bash
# Search for authentication articles
curl "https://extreme-networks.my.site.com/ExtrSearch?q=EXOS+authentication+troubleshooting"

# Add URLs to kb_sources/extreme_urls_phase2.txt
# Repeat fetch → parse → validate → import workflow
```

---

## Tools & Scripts Overview

```
scripts/
├── kb_fetcher.py           # Fetch articles from URLs
├── kb_parser.py            # Parse HTML to JSON
├── kb_validator.py         # Validate article structure
├── kb_bulk_import.py       # Import to ChromaDB
├── kb_quality_checker.py   # Measure KB quality metrics
└── test-incident-generator.py  # Generate test incidents

kb_sources/
├── extreme_urls.txt        # Phase 1 URLs
├── extreme_urls_phase2.txt # Phase 2 URLs (gaps)
├── raw_articles/           # Fetched HTML
│   ├── 000122408.html
│   └── 000079504.html
├── parsed_articles/        # Structured JSON
│   ├── 000122408.json
│   └── 000079504.json
└── validated_articles/     # Ready for import
    ├── 000122408.json
    └── 000079504.json
```

---

## Execution Plan Summary

### Quick Start (Minimum Viable)

**Day 1 (4 hours):**
1. Create `kb_fetcher.py` (2 hours)
2. Manually curate 20 high-value article URLs (1 hour)
3. Fetch articles (15 minutes)
4. Manually convert 20 articles to JSON format (1 hour)

**Day 2 (3 hours):**
1. Create `kb_bulk_import.py` (2 hours)
2. Import 20 articles to ChromaDB (15 minutes)
3. Test with 5 incidents (30 minutes)
4. Measure improvement (15 minutes)

**Result:** 23 → 43 articles (+87%), test confidence improvement

### Full Scale (Comprehensive)

**Day 1-2:** Build all tools (kb_fetcher, parser, validator, importer)
**Day 3:** Curate 100 article URLs, fetch & parse
**Day 4:** Validate & import all articles, E2E testing
**Day 5:** Measure quality, identify gaps, add Phase 2 articles

**Result:** 23 → 123 articles (+435%), 21%+ confidence improvement

---

## Alternative Approach: Hybrid (Recommended)

**Week 1 - Quick Win (20 articles)**
- Focus on top 20 most common incident types from your PostgreSQL history
- Manual curation of best articles
- Simple fetch & import scripts
- Prove value quickly

**Week 2 - Scale Up (80 articles)**
- Build comprehensive parser
- Batch processing
- Cover all 5 categories evenly

**Week 3 - Refinement**
- Gap analysis
- Quality improvements
- Add edge cases

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| KB Articles | 23 | 100+ | ChromaDB count |
| Avg Confidence | 0.70-0.85 | 0.85-0.95 | PostgreSQL query |
| EXOS-Specific Commands | 40% | 90%+ | Remediation plan analysis |
| MTTR | ~90 min | ~45 min | Incident resolution time |
| Coverage | Generic | Extreme-specific | Vector similarity scores |

---

## Risk Mitigation

**Risk 1:** Article parsing fails due to HTML structure changes
- **Mitigation:** Manual review of first 5 articles, adjust parser

**Risk 2:** ChromaDB performance degrades with 100+ articles
- **Mitigation:** Benchmark at 50, 100, 200 articles; optimize if needed

**Risk 3:** LLM still produces generic commands despite better KB
- **Mitigation:** Improve system prompt, add examples, test iteratively

**Risk 4:** Extreme Networks blocks automated fetching
- **Mitigation:** Rate limiting, manual fetching as backup

---

## Next Steps (Decision Required)

**Option A: Quick Start (Recommended)**
1. I create `kb_fetcher.py` now
2. You manually curate 20 article URLs
3. We import 20 articles today
4. Test & measure improvement
5. Scale up if successful

**Option B: Full Automation**
1. I build all 5 tools (6-8 hours)
2. Automated article discovery
3. Batch import 100+ articles
4. More complex, higher risk

**Option C: Manual First**
1. You copy-paste 10 articles manually
2. I convert to JSON and import
3. Test immediately
4. Decide on automation after seeing results

**Which approach do you prefer?**

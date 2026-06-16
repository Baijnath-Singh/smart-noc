# KB Article Tools - Quick Start

**Created:** June 15, 2026  
**Status:** Ready to Use ✅

---

## What Was Created

### 1. Interactive Article Creator
**File:** `scripts/kb_article_creator.py` (18KB, executable)

**Purpose:** Interactive tool that guides you through creating KB articles from Extreme Networks support URLs.

**Key Features:**
- Fetches content from ExtremePortal URLs
- Parses HTML and extracts commands/procedures
- Prompts for metadata (category, symptoms, root causes)
- Generates structured JSON articles
- Optional direct import to ChromaDB

### 2. Batch Importer
**File:** `scripts/kb_bulk_import.py` (11KB, executable)

**Purpose:** Import multiple JSON articles to ChromaDB in batch.

**Key Features:**
- Batch processing (default: 20 articles per batch)
- Duplicate detection (skips existing articles)
- Progress tracking and error handling
- Summary statistics

### 3. Documentation
**File:** `scripts/README_KB_TOOLS.md` (15KB)

Complete usage guide with examples, troubleshooting, and best practices.

### 4. Directory Structure
```
kb_sources/
├── raw_articles/          # Downloaded HTML (optional)
├── parsed_articles/       # Intermediate JSON (optional)
└── validated_articles/    # Final JSON (ready for import)
```

---

## Quick Start (First Article)

### Step 1: Run Interactive Creator
```bash
python scripts/kb_article_creator.py
```

### Step 2: Provide URL When Prompted
```
Enter Extreme Networks article URL: https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408
```

### Step 3: Fill in Metadata
- Platform: EXOS
- Category: routing (or interface, switching, performance, security)
- Subcategory: BGP
- Symptoms: List 2-5 symptoms
- Root Causes: List 3-5 common causes
- Keywords: 3-5 keywords

### Step 4: Review and Save
- Preview shows extracted commands and steps
- Confirm to save as JSON
- Optionally import to ChromaDB

### Step 5: Import to ChromaDB (if not done in Step 4)
```bash
python scripts/kb_bulk_import.py --input kb_sources/validated_articles/
```

---

## Example URLs to Start With

### Interface Issues
```
https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408  # BGP Configuration
https://extreme-networks.my.site.com/ExtrArticleDetail?an=000079504  # BGP Troubleshooting
```

### Finding More Articles
1. Go to: https://extreme-networks.my.site.com/ExtrSearch
2. Search: "EXOS troubleshooting" + category (interface/BGP/VLAN/etc)
3. Filter for "How To:" and "Troubleshooting" articles
4. Copy article URLs

---

## Recommended First 10 Articles

Create articles for these common issues (search ExtremePortal for URLs):

1. **Interface flapping** (SFP/cable issues)
2. **BGP neighbor down** (session failures)
3. **OSPF neighbor issues** (adjacency problems)
4. **VLAN connectivity** (misconfiguration)
5. **LAG/MLAG issues** (port aggregation)
6. **STP loops** (broadcast storms)
7. **High CPU utilization** (performance)
8. **Authentication failures** (RADIUS/802.1X)
9. **Port not coming up** (config mismatch)
10. **EAPS ring issues** (redundancy)

---

## Testing After Import

### 1. Check ChromaDB Count
```python
import chromadb
client = chromadb.HttpClient(host='localhost', port=8000)
collection = client.get_collection('kb_articles')
print(f"Total articles: {collection.count()}")  # Should be 23 + your new articles
```

### 2. Test Vector Search
```python
results = collection.query(
    query_texts=["BGP neighbor down troubleshooting"],
    n_results=5,
    where={"platform": "EXOS"}
)
print(results)
```

### 3. Generate Test Incident
```bash
python scripts/test-incident-generator.py --type BGP_SESSION_DOWN --device 10.139.38.188
```

### 4. Check LLM Diagnosis
```bash
docker logs smart-noc-llm-diagnosis --tail 50 | grep -i "kb articles"
```

**Expected:** Should see "Retrieved 5 similar KB articles" with your new articles in the results.

---

## Success Metrics

Track improvement as you add articles:

| Metric | Before (23 articles) | Target (50 articles) | Target (100 articles) |
|--------|---------------------|---------------------|----------------------|
| Avg Confidence | 0.70-0.85 | 0.80-0.90 | 0.85-0.95 |
| EXOS-Specific Commands | 40% | 70% | 90%+ |
| KB Hit Rate | Low | Medium | High |

**Measure confidence:**
```sql
SELECT AVG(confidence_score) 
FROM incidents 
WHERE created_at > '2026-06-15'  -- After KB expansion
AND status = 'DIAGNOSED';
```

---

## Troubleshooting

### ChromaDB Not Running
```bash
docker ps | grep chromadb
docker-compose restart chromadb
curl http://localhost:8000/api/v1/heartbeat
```

### Script Errors
```bash
# Re-install dependencies
pip install -r scripts/kb_tools_requirements.txt

# Check Python version (need 3.8+)
python --version
```

### Article Parsing Issues
- Some articles have different HTML structure
- Tool extracts what it can, you fill in gaps
- Manually edit JSON before importing if needed

---

## Next Steps

1. ✅ **Tools created and tested**
2. ⏭️ **Create first 10 articles** (3-4 hours)
3. ⏭️ **Import and test** (verify improvement)
4. ⏭️ **Scale to 50 articles** (next week)
5. ⏭️ **Scale to 100+ articles** (ongoing)

---

## Dependencies Installed

✅ requests==2.31.0  
✅ beautifulsoup4==4.12.2  
✅ lxml==4.9.3  
✅ chromadb==0.5.0 (already installed)

---

## Files Created

```
scripts/
├── kb_article_creator.py          ✅ 18KB, executable
├── kb_bulk_import.py              ✅ 11KB, executable
├── kb_tools_requirements.txt      ✅ Dependencies list
└── README_KB_TOOLS.md             ✅ 15KB, comprehensive guide

kb_sources/                        ✅ Directory structure
├── raw_articles/
├── parsed_articles/
└── validated_articles/

docs/
├── KB_EXPANSION_PLAN.md           ✅ Strategic plan
└── KB_TOOLS_QUICKSTART.md         ✅ This file
```

---

## Ready to Start!

**Command to begin:**
```bash
python scripts/kb_article_creator.py
```

**First URL to try:**
```
https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408
```

**Questions?** Check [scripts/README_KB_TOOLS.md](scripts/README_KB_TOOLS.md) for detailed documentation.

---

**Good luck expanding your knowledge base! 🚀**

# Knowledge Base Article Tools

Interactive and batch tools for creating and importing KB articles into Smart NOC's ChromaDB knowledge base.

---

## Tools Overview

### 1. `kb_article_creator.py` - Interactive Article Creator
Interactive tool that guides you through creating KB articles from Extreme Networks support URLs.

### 2. `kb_bulk_import.py` - Batch Importer
Batch import multiple JSON articles into ChromaDB.

---

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r scripts/kb_tools_requirements.txt

# Make scripts executable
chmod +x scripts/kb_article_creator.py
chmod +x scripts/kb_bulk_import.py
```

### Basic Usage

```bash
# Interactive article creation
python scripts/kb_article_creator.py

# With automatic ChromaDB import
python scripts/kb_article_creator.py --import

# Batch import existing articles
python scripts/kb_bulk_import.py --input kb_sources/validated_articles/
```

---

## Tool 1: Interactive Article Creator

### Features

✅ **Guided Workflow:** Step-by-step prompts for all metadata  
✅ **Auto-Fetch:** Downloads content from Extreme Networks URLs  
✅ **Smart Parsing:** Extracts commands, procedures, and objectives  
✅ **Command Detection:** Automatically identifies EXOS commands  
✅ **Preview:** Shows article before saving  
✅ **Batch Processing:** Create multiple articles in one session  
✅ **Direct Import:** Optional automatic import to ChromaDB  

### Workflow

```
1. Provide Extreme Networks article URL
   ↓
2. Tool fetches and parses HTML content
   ↓
3. You provide metadata:
   - Category (interface/routing/switching/etc)
   - Symptoms
   - Root causes
   - Keywords
   ↓
4. Tool creates structured JSON article
   ↓
5. Preview article
   ↓
6. Save and optionally import to ChromaDB
   ↓
7. Continue with next article or exit
```

### Interactive Session Example

```bash
$ python scripts/kb_article_creator.py

======================================================================
              KB Article Creator for Smart NOC
======================================================================

ℹ This tool will help you create structured KB articles...

Output directory for JSON files [kb_sources/validated_articles]: 

======================================================================
                          Article #1
======================================================================

Enter Extreme Networks article URL: https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408

ℹ Fetching content from: https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408
✓ Content fetched successfully
ℹ Parsing article content...
✓ Article parsed: How To: Configure BGP on Switch Engine (EXOS)

======================================================================
                       Article Metadata
======================================================================

Article title [How To: Configure BGP on Switch Engine (EXOS)]: 
Platform (EXOS/VOSS/EOS) [EXOS]: 

ℹ Categories: interface, routing, switching, performance, security, configuration
Category [interface]: routing
Subcategory (e.g., flapping, BGP, VLAN, CPU) []: BGP

Symptoms/Issues (one per line, empty line to finish):
  > BGP neighbor not establishing
  > BGP session down
  > Routes not being advertised
  > 

Common Root Causes (one per line, empty line to finish):
  > Incorrect AS number
  > Loopback misconfiguration
  > Missing route to neighbor
  > Authentication mismatch
  > 

Keywords/Tags (one per line, empty line to finish):
  > BGP
  > routing
  > neighbor
  > AS
  > iBGP
  > 

Have you tested this? (y/n) [n]: y
EXOS version (or 'All versions') [All versions]: 32.6+

ℹ Creating KB article...

======================================================================
                       Article Preview
======================================================================

Article ID: KB-EXOS-ROUTING-001
Title: How To: Configure BGP on Switch Engine (EXOS)
Platform: EXOS
Category: routing / BGP

Symptoms:
  • BGP neighbor not establishing
  • BGP session down
  • Routes not being advertised

Root Causes:
  • Incorrect AS number
  • Loopback misconfiguration
  • Missing route to neighbor
  • Authentication mismatch

Diagnostic Commands (8):
  • show bgp
  • show bgp neighbor
  • show bgp routes all
  • show iproute
  • show configuration bgp
  ... and 3 more

Remediation Steps (10):
  1. Create, Configure, and Enable Loopback (optional) interfaces create vlan <vlan-...
  2. Assign an IP address on each VLAN interface: configure vlan <vlan-name> ipadd...
  3. Add ports on each VLAN: configure vlan <vlan-name> add ports <ports> untagged...
  ... and 7 more steps

Keywords: BGP, routing, neighbor, AS, iBGP

Save this article? (y/n) [y]: y
✓ Article saved: kb_sources/validated_articles/KB-EXOS-ROUTING-001.json

Process another article? (y/n) [y]: n

======================================================================
                          Summary
======================================================================

✓ Created 1 KB articles
ℹ Articles saved in: kb_sources/validated_articles

ℹ To import articles to ChromaDB later, run:
  python scripts/kb_bulk_import.py --input kb_sources/validated_articles
```

### Command-Line Options

```bash
# Basic usage (saves JSON only)
python scripts/kb_article_creator.py

# With automatic ChromaDB import
python scripts/kb_article_creator.py --import
python scripts/kb_article_creator.py --load  # Same as --import
```

### Article Structure (JSON Output)

```json
{
  "article_id": "KB-EXOS-ROUTING-001",
  "source_url": "https://extreme-networks.my.site.com/...",
  "title": "How To: Configure BGP on Switch Engine (EXOS)",
  "vendor": "Extreme Networks",
  "platform": "EXOS",
  "category": "routing",
  "subcategory": "BGP",
  "symptoms": [
    "BGP neighbor not establishing",
    "BGP session down"
  ],
  "root_causes": [
    "Incorrect AS number",
    "Loopback misconfiguration"
  ],
  "diagnostic_commands": [
    "show bgp",
    "show bgp neighbor",
    "show bgp routes all"
  ],
  "remediation_steps": [
    {
      "step": 1,
      "description": "Verify BGP configuration",
      "commands": ["show configuration bgp"],
      "expected_output": ""
    }
  ],
  "configuration_example": {
    "scenario": "iBGP between R10 and R11",
    "commands": [
      "configure bgp AS-number 100",
      "configure bgp routerid 1.1.1.1"
    ]
  },
  "keywords": ["BGP", "routing", "neighbor"],
  "last_updated": "2026-06-15",
  "confidence_tags": {
    "official_source": true,
    "tested": true,
    "version_specific": "32.6+"
  }
}
```

---

## Tool 2: Batch Importer

### Features

✅ **Batch Processing:** Import 10-100s of articles at once  
✅ **Duplicate Detection:** Skips articles already in ChromaDB  
✅ **Progress Tracking:** Shows batch-by-batch progress  
✅ **Error Handling:** Continues on individual failures  
✅ **Summary Report:** Detailed import statistics  

### Usage

```bash
# Basic import
python scripts/kb_bulk_import.py --input kb_sources/validated_articles/

# Custom batch size (default: 20)
python scripts/kb_bulk_import.py --input kb_sources/validated_articles/ --batch-size 50

# Custom collection name (default: kb_articles)
python scripts/kb_bulk_import.py --input kb_sources/validated_articles/ --collection my_kb

# Remote ChromaDB server
python scripts/kb_bulk_import.py --input kb_sources/validated_articles/ \
                                  --host 192.168.1.100 \
                                  --port 8000
```

### Example Output

```bash
$ python scripts/kb_bulk_import.py --input kb_sources/validated_articles/

ℹ Loading articles from: kb_sources/validated_articles/
✓ Loaded 25 articles
ℹ Connecting to ChromaDB at localhost:8000
ℹ Collection 'kb_articles' currently has 23 articles
ℹ Processing 25 articles in batches of 20...

ℹ Processing batch 1/2 (20 articles)...
⚠ Article KB-EXOS-INTERFACE-001 already exists, skipping
⚠ Article KB-EXOS-INTERFACE-002 already exists, skipping
✓ Batch 1 imported: 18 articles

ℹ Processing batch 2/2 (5 articles)...
✓ Batch 2 imported: 5 articles

======================================================================
                        Import Summary
======================================================================

Initial article count: 23
Final article count:   46
Articles processed:    25

✓ Successfully imported: 23
⚠ Skipped (duplicates):  2
✗ Errors:                0

Net change: +23 articles
======================================================================

✓ All articles processed successfully!
```

---

## Typical Workflow

### Phase 1: Create Articles (Interactive)

```bash
# Start interactive session
python scripts/kb_article_creator.py

# Process 5-10 articles in one session
# Articles saved as JSON in kb_sources/validated_articles/
```

### Phase 2: Review JSON Files (Optional)

```bash
# Review generated articles
ls -lh kb_sources/validated_articles/
cat kb_sources/validated_articles/KB-EXOS-ROUTING-001.json | jq .

# Edit if needed
vim kb_sources/validated_articles/KB-EXOS-ROUTING-001.json
```

### Phase 3: Batch Import to ChromaDB

```bash
# Import all articles at once
python scripts/kb_bulk_import.py --input kb_sources/validated_articles/
```

### Phase 4: Verify in ChromaDB

```python
import chromadb
client = chromadb.HttpClient(host='localhost', port=8000)
collection = client.get_collection('kb_articles')

# Check count
print(f"Total articles: {collection.count()}")

# Test search
results = collection.query(
    query_texts=["BGP session down troubleshooting"],
    n_results=5,
    where={"platform": "EXOS"}
)
print(results)
```

---

## Recommended Article Sources

### Extreme Networks Support Portal

1. **Search by Category:**
   - https://extreme-networks.my.site.com/ExtrSearch?q=EXOS+interface+troubleshooting
   - https://extreme-networks.my.site.com/ExtrSearch?q=EXOS+BGP+troubleshooting
   - https://extreme-networks.my.site.com/ExtrSearch?q=EXOS+VLAN+configuration

2. **Filter Results:**
   - Look for "How To:" and "Troubleshooting" articles
   - Prioritize articles with commands and examples
   - Check "Last Modified" date (prefer recent)

3. **Top Priority Articles:**
   - Interface flapping (SFP, cable, duplex issues)
   - BGP session failures
   - OSPF neighbor issues
   - VLAN connectivity problems
   - LAG/MLAG configuration
   - STP loops
   - Authentication failures (RADIUS, 802.1X)
   - High CPU/memory utilization

### Article Quality Checklist

✅ Contains EXOS commands  
✅ Has troubleshooting steps  
✅ Includes symptoms/errors  
✅ Shows expected output  
✅ Provides configuration examples  
✅ Recent (within 2-3 years)  
✅ Official Extreme Networks source  

---

## Directory Structure

```
smart-noc/
├── scripts/
│   ├── kb_article_creator.py       # Interactive creator tool
│   ├── kb_bulk_import.py           # Batch importer
│   ├── kb_tools_requirements.txt   # Python dependencies
│   └── README_KB_TOOLS.md          # This file
│
└── kb_sources/                     # Working directory
    ├── extreme_urls.txt            # URL list (optional)
    ├── raw_articles/               # Downloaded HTML (optional)
    ├── parsed_articles/            # Intermediate JSON (optional)
    └── validated_articles/         # Final JSON (ready for import)
        ├── KB-EXOS-INTERFACE-001.json
        ├── KB-EXOS-ROUTING-001.json
        └── ...
```

---

## Troubleshooting

### Issue: "Failed to fetch content"

**Cause:** Network issue or invalid URL

**Solution:**
```bash
# Test URL manually
curl -I "https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408"

# Check if you need authentication/VPN
```

### Issue: "Failed to connect to ChromaDB"

**Cause:** ChromaDB service not running

**Solution:**
```bash
# Check if ChromaDB container is running
docker ps | grep chromadb

# Restart if needed
docker-compose restart chromadb

# Verify health
curl http://localhost:8000/api/v1/heartbeat
```

### Issue: "Article missing article_id"

**Cause:** JSON file is corrupted or incomplete

**Solution:**
```bash
# Validate JSON
cat kb_sources/validated_articles/KB-EXOS-XXX.json | jq .

# Fix or regenerate article
```

### Issue: Parsing extracts too few commands

**Cause:** HTML structure varies by article

**Solution:** Manually add commands to JSON before importing:
```bash
# Edit JSON file
vim kb_sources/validated_articles/KB-EXOS-XXX.json

# Add to "diagnostic_commands" array
```

---

## Tips for Best Results

### 1. Article Selection
- Start with "How To:" and "Troubleshooting" articles
- Prefer articles with lots of commands
- Focus on your most common incident types first

### 2. Metadata Quality
- **Symptoms:** Be specific ("BGP neighbor down" vs "routing problem")
- **Root Causes:** List 3-5 common causes
- **Keywords:** Include platform (EXOS), feature (BGP), symptoms

### 3. Batch Processing
- Create 5-10 articles, then import and test
- Measure improvement in LLM confidence scores
- Adjust strategy based on results

### 4. Testing After Import
```bash
# Generate test incident
python scripts/test-incident-generator.py --type BGP_SESSION_DOWN

# Check LLM diagnosis
docker logs smart-noc-llm-diagnosis --tail 50

# Verify ChromaDB was used
# Look for "Retrieved X similar KB articles" in logs
```

---

## Performance Expectations

| Articles | Creation Time | Import Time | Total Time |
|----------|--------------|-------------|------------|
| 10       | 30-40 min    | 10-15 sec   | ~40 min    |
| 20       | 60-80 min    | 20-30 sec   | ~80 min    |
| 50       | 2-3 hours    | 45-60 sec   | ~3 hours   |
| 100      | 4-6 hours    | 90-120 sec  | ~6 hours   |

**Note:** Interactive creation is the time-consuming part. Consider splitting work across multiple sessions or team members.

---

## Next Steps

1. **Install dependencies:**
   ```bash
   pip install -r scripts/kb_tools_requirements.txt
   ```

2. **Create first article:**
   ```bash
   python scripts/kb_article_creator.py
   ```

3. **Import to ChromaDB:**
   ```bash
   python scripts/kb_bulk_import.py --input kb_sources/validated_articles/
   ```

4. **Test improvement:**
   ```bash
   python scripts/test-incident-generator.py --type INTERFACE_FLAPPING
   ```

5. **Scale up:** Repeat until you have 100+ articles

---

## Support

**Issues?** Check [docs/KB_EXPANSION_PLAN.md](../docs/KB_EXPANSION_PLAN.md) for comprehensive planning guide.

**Questions?** Review individual service documentation in [docs/10-services/](../docs/10-services/).

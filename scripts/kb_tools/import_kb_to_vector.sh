#!/bin/bash
# Import KB articles to ChromaDB using vector service container
# This avoids installing heavy dependencies (PyTorch, etc.) on host
# Usage: 
#   bash import_kb_to_vector.sh <file.json>           # Import single file
#   bash import_kb_to_vector.sh <directory>           # Import all files in directory

echo "======================================================================"
echo "KB Article Importer (Using Vector Service Container)"
echo "======================================================================"

INPUT_PATH="${1:-kb_sources/validated_articles}"

# Check if input is a file or directory
if [ -f "$INPUT_PATH" ]; then
    # Single file mode
    echo ""
    echo "Mode: Single file"
    echo "File: $INPUT_PATH"
    
    if [[ ! "$INPUT_PATH" =~ \.json$ ]]; then
        echo "✗ Error: File must be a .json file"
        exit 1
    fi
    
    JSON_FILES=("$INPUT_PATH")
    ARTICLE_COUNT=1
elif [ -d "$INPUT_PATH" ]; then
    # Directory mode
    echo ""
    echo "Mode: Directory"
    echo "Path: $INPUT_PATH"
    
    ARTICLE_COUNT=$(find "$INPUT_PATH" -name "*.json" -type f | wc -l)
    
    if [ "$ARTICLE_COUNT" -eq 0 ]; then
        echo "✗ No articles found in directory"
        exit 1
    fi
    
    # Build array of files
    JSON_FILES=()
    while IFS= read -r -d '' file; do
        JSON_FILES+=("$file")
    done < <(find "$INPUT_PATH" -name "*.json" -type f -print0)
else
    echo ""
    echo "✗ Error: '$INPUT_PATH' is not a valid file or directory"
    exit 1
fi

echo "Found $ARTICLE_COUNT article(s)"

echo ""
echo "Converting JSON articles to YAML format for vector service..."

# Create temporary YAML file
TEMP_YAML="/tmp/kb_import_$(date +%s).yaml"
echo "articles:" > "$TEMP_YAML"

# Convert each JSON article to YAML format
for json_file in "${JSON_FILES[@]}"; do
    [ -f "$json_file" ] || continue
    
    filename=$(basename "$json_file")
    echo "  Processing: $filename"
    
    # Extract fields using python
    python3 << EOF >> "$TEMP_YAML"
import json
import sys

with open("$json_file", "r") as f:
    article = json.load(f)

# Format as YAML
print(f"""
  - id: "{article['article_id']}"
    title: "{article['title']}"
    event_type: "{article.get('event_type', article.get('category', 'general')).upper()}"
    vendor: "extreme"
    platform: "{article.get('platform', 'EXOS').lower()}"
    category: "{article.get('category', 'general')}"
    success_rate: {article.get('confidence', 0.85)}
    content: |
      Title: {article['title']}
      
      Platform: {article.get('platform', 'EXOS')}
      Category: {article.get('category', 'general')} / {article.get('subcategory', '')}
      
      Symptoms:
""")

for symptom in article.get('symptoms', []):
    print(f"      - {symptom}")

print("      ")
print("      Root Causes:")
for cause in article.get('root_causes', []):
    print(f"      - {cause}")

print("      ")
print("      Diagnostic Commands:")
for cmd in article.get('diagnostic_commands', []):
    print(f"      - {cmd}")

print("      ")
print("      Remediation Steps:")
for i, step in enumerate(article.get('remediation_steps', []), 1):
    step_desc = step.get('step', step.get('description', 'Unknown step'))
    print(f"      {i}. {step_desc}")
    if step.get('commands'):
        for cmd in step['commands']:
            print(f"         > {cmd}")
EOF
done

echo ""
echo "YAML file created: $TEMP_YAML"
echo ""

# Copy YAML to vector service container
echo "Copying to vector service container..."
docker cp "$TEMP_YAML" smart-noc-vector-service:/tmp/kb_import.yaml

if [ $? -ne 0 ]; then
    echo "✗ Failed to copy to container"
    rm "$TEMP_YAML"
    exit 1
fi

echo "✓ File copied to container"
echo ""

# Create inline Python script to import articles directly (bypasses populate_kb.py bug)
echo "Importing to ChromaDB..."

cat > /tmp/import_articles.py << 'PYTHONSCRIPT'
import sys
import os
import yaml
sys.path.insert(0, '/app')
from vector_service import VectorKnowledgeBase

# Read YAML file passed as argument
yaml_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/kb_import.yaml'
print(f"Loading articles from: {yaml_file}")

with open(yaml_file, 'r') as f:
    data = yaml.safe_load(f)

articles = data.get('articles', [])
print(f"Found {len(articles)} article(s) to import")

# Initialize vector KB
vector_kb = VectorKnowledgeBase(
    chromadb_host=os.getenv("CHROMADB_HOST", "chromadb"),
    chromadb_port=int(os.getenv("CHROMADB_PORT", "8000"))
)

# Import each article
success_count = 0
for article in articles:
    article_id = article['id']
    title = article['title']
    content = article['content']
    
    metadata = {
        'event_type': article.get('event_type', 'UNKNOWN'),
        'vendor': article.get('vendor', 'Extreme Networks'),
        'platform': article.get('platform', 'EXOS'),
        'category': article.get('category', 'general'),
        'success_rate': article.get('success_rate', 0.85)
    }
    
    result = vector_kb.add_kb_article(
        article_id=article_id,
        title=title,
        content=content,
        metadata=metadata
    )
    
    if result:
        success_count += 1
        print(f"  ✓ {article_id}: {title}")
    else:
        print(f"  ✗ {article_id}: Failed")

print(f"\n{'='*70}")
print(f"Successfully imported {success_count}/{len(articles)} article(s)")
print(f"{'='*70}")

# Get final stats
stats = vector_kb.get_stats()
print(f"\nVector DB Statistics:")
print(f"  - KB Articles: {stats['kb_articles']}")
print(f"  - Incidents: {stats['incidents']}")
print(f"  - Commands: {stats['commands']}")

sys.exit(0 if success_count == len(articles) else 1)
PYTHONSCRIPT

# Copy import script to container
docker cp /tmp/import_articles.py smart-noc-vector-service:/tmp/import_articles.py

# Execute import
docker exec smart-noc-vector-service python /tmp/import_articles.py /tmp/kb_import.yaml

EXIT_CODE=$?

# Cleanup
rm "$TEMP_YAML"
rm /tmp/import_articles.py
docker exec smart-noc-vector-service rm /tmp/kb_import.yaml /tmp/import_articles.py 2>/dev/null

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "✓ Import completed successfully!"
    echo "======================================================================"
    exit 0
else
    echo ""
    echo "✗ Import failed with exit code: $EXIT_CODE"
    exit $EXIT_CODE
fi

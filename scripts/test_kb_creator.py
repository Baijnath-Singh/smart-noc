#!/usr/bin/env python3
"""
Test script for kb_article_creator
Tests auto-extraction with a real Extreme Networks article
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Simulate the workflow
from scripts.kb_article_creator import (
    fetch_article_content, 
    parse_extreme_article,
    auto_extract_platform,
    auto_extract_category,
    auto_extract_subcategory,
    auto_extract_symptoms,
    auto_extract_root_causes,
    auto_extract_keywords,
    auto_extract_version,
    extract_exos_commands,
    create_kb_article,
    save_article
)

# Test URL
test_url = "https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408"

print("="*70)
print("Testing KB Article Creator")
print("="*70)

# Step 1: Fetch content
print(f"\n1. Fetching content from: {test_url}")
html_content = fetch_article_content(test_url)

if not html_content:
    print("❌ Failed to fetch content")
    sys.exit(1)

print("✓ Content fetched successfully")

# Step 2: Parse content
print("\n2. Parsing article content...")
parsed_data = parse_extreme_article(html_content)

print(f"✓ Title: {parsed_data['title']}")
print(f"✓ Objective: {parsed_data['objective'][:100]}...")
print(f"✓ Environment: {len(parsed_data['environment'])} items")
print(f"✓ Procedure steps: {len(parsed_data['procedure_steps'])}")
print(f"✓ Commands found: {len(parsed_data['commands'])}")

# Step 3: Auto-extract metadata
print("\n3. Auto-extracting metadata...")

metadata = {
    'title': parsed_data['title'],
    'platform': auto_extract_platform(parsed_data, html_content),
    'category': auto_extract_category(parsed_data),
    'subcategory': auto_extract_subcategory(parsed_data),
    'symptoms': auto_extract_symptoms(parsed_data),
    'root_causes': auto_extract_root_causes(parsed_data),
    'keywords': auto_extract_keywords(parsed_data),
    'tested': False,
    'version': auto_extract_version(parsed_data),
    'article_number': 999  # Test number
}

print(f"✓ Platform: {metadata['platform']}")
print(f"✓ Category: {metadata['category']}")
print(f"✓ Subcategory: {metadata['subcategory']}")
print(f"✓ Symptoms: {len(metadata['symptoms'])} extracted")
for symptom in metadata['symptoms']:
    print(f"  - {symptom}")
print(f"✓ Root Causes: {len(metadata['root_causes'])} extracted")
for cause in metadata['root_causes'][:3]:
    print(f"  - {cause}")
print(f"✓ Keywords: {', '.join(metadata['keywords'][:5])}")
print(f"✓ Version: {metadata['version']}")

# Step 4: Create KB article
print("\n4. Creating KB article structure...")
article = create_kb_article(test_url, parsed_data, metadata)

print(f"✓ Article ID: {article['article_id']}")
print(f"✓ Diagnostic commands: {len(article['diagnostic_commands'])}")
for cmd in article['diagnostic_commands'][:5]:
    print(f"  - {cmd}")
if len(article['diagnostic_commands']) > 5:
    print(f"  ... and {len(article['diagnostic_commands']) - 5} more")

print(f"✓ Remediation steps: {len(article['remediation_steps'])}")
for step in article['remediation_steps'][:3]:
    print(f"  {step['step']}. {step['description'][:60]}...")
if len(article['remediation_steps']) > 3:
    print(f"  ... and {len(article['remediation_steps']) - 3} more steps")

# Step 5: Save article
print("\n5. Saving article...")
output_dir = "kb_sources/test_articles"
filepath = save_article(article, output_dir)
print(f"✓ Article saved: {filepath}")

# Step 6: Validate saved content
print("\n6. Validating saved article...")
import json
with open(filepath, 'r') as f:
    saved_article = json.load(f)

# Check critical fields
checks = {
    "Article ID": saved_article.get('article_id', 'MISSING'),
    "Title": saved_article.get('title', 'MISSING')[:50],
    "Platform": saved_article.get('platform', 'MISSING'),
    "Category": saved_article.get('category', 'MISSING'),
    "Symptoms count": len(saved_article.get('symptoms', [])),
    "Root causes count": len(saved_article.get('root_causes', [])),
    "Diagnostic commands": len(saved_article.get('diagnostic_commands', [])),
    "Remediation steps": len(saved_article.get('remediation_steps', [])),
    "Keywords": len(saved_article.get('keywords', []))
}

print("\nValidation Results:")
print("-" * 70)
for key, value in checks.items():
    status = "✓" if value and value != 'MISSING' and (not isinstance(value, int) or value > 0) else "❌"
    print(f"{status} {key}: {value}")

print("\n" + "="*70)
print("Test Complete!")
print("="*70)

# Show sample diagnostic commands
print("\nSample Diagnostic Commands (first 10):")
for i, cmd in enumerate(saved_article['diagnostic_commands'][:10], 1):
    print(f"{i}. {cmd}")

print("\nArticle file location:")
print(f"  {filepath}")

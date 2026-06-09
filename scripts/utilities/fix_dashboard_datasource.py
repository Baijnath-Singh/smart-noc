#!/usr/bin/env python3
"""Fix datasource UIDs in incidents dashboard"""

import sys

# Read the dashboard file
with open('dashboards/smart-noc-incidents-dashboard.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace hardcoded UID with template variable
original_count = content.count('"uid": "elasticsearch"')
content = content.replace('"uid": "elasticsearch"', '"uid": "${DS_ELASTICSEARCH}"')
updated_count = content.count('"uid": "${DS_ELASTICSEARCH}"')

# Write back
with open('dashboards/smart-noc-incidents-dashboard.json', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed datasource UIDs")
print(f"   Replacements: {original_count} → {updated_count} references to DS_ELASTICSEARCH")

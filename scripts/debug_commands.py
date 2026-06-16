#!/usr/bin/env python3
"""Quick test to see what commands are in the article"""

import requests
from bs4 import BeautifulSoup

url = "https://extreme-networks.my.site.com/ExtrArticleDetail?an=000122408"

headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(response.text, 'html.parser')

# Look for all text
text = soup.get_text()

# Find lines with common EXOS commands
command_keywords = ['show bgp', 'configure bgp', 'create bgp', 'enable bgp', 'show vlan', 'show iproute', 'show configuration']

print("Commands found in article:")
print("="*70)

lines = text.split('\n')
found_commands = []

for line in lines:
    line_clean = line.strip()
    for keyword in command_keywords:
        if keyword in line_clean.lower() and len(line_clean) < 150:
            if line_clean not in found_commands:
                print(f"  {line_clean}")
                found_commands.append(line_clean)
                break

print(f"\nTotal unique commands found: {len(found_commands)}")

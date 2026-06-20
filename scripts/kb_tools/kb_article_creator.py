#!/usr/bin/env python3
"""
Interactive KB Article Creator

Fetches Extreme Networks articles from URLs, intelligently parses content,
and creates structured KB articles for ChromaDB import.

Features:
- Auto-extracts metadata from article content (platform, category, symptoms, etc.)
- Smart command detection and parsing
- Interactive mode with preview before saving
- Optional manual override for all fields
- Direct import to ChromaDB

Usage:
    # Auto-extraction mode (recommended)
    python scripts/kb_article_creator.py
    
    # With direct import to ChromaDB
    python scripts/kb_article_creator.py --import
"""

import os
import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import LLM extraction and validation (if available)
try:
    from llm_extractor import LLMArticleExtractor
    from article_validator import ArticleValidator
    LLM_AVAILABLE = True
except ImportError as e:
    LLM_AVAILABLE = False
    print(f"⚠️  LLM extraction not available: {e}")

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def get_user_input(prompt: str, default: str = None, required: bool = True) -> str:
    """Get user input with optional default value."""
    if default:
        prompt_text = f"{Colors.CYAN}{prompt} [{default}]: {Colors.ENDC}"
    else:
        prompt_text = f"{Colors.CYAN}{prompt}: {Colors.ENDC}"
    
    while True:
        value = input(prompt_text).strip()
        
        if not value and default:
            return default
        elif not value and not required:
            return ""
        elif not value and required:
            print_error("This field is required. Please provide a value.")
            continue
        else:
            return value

def get_multiline_input(prompt: str) -> List[str]:
    """Get multiple lines of input (end with empty line)."""
    print(f"{Colors.CYAN}{prompt} (one per line, empty line to finish):{Colors.ENDC}")
    lines = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        lines.append(line)
    return lines

def fetch_article_content(url: str) -> Optional[str]:
    """Fetch article HTML content from URL."""
    print_info(f"Fetching content from: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print_success("Content fetched successfully")
        return response.text
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to fetch content: {e}")
        return None

def parse_extreme_article(html_content: str) -> Dict:
    """Parse Extreme Networks article HTML and extract key information."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    parsed_data = {
        'title': '',
        'objective': '',
        'environment': [],
        'procedure_steps': [],
        'commands': [],
        'additional_notes': ''
    }
    
    # Extract title
    title_elem = soup.find('h2')
    if title_elem:
        parsed_data['title'] = title_elem.get_text(strip=True)
    
    # Extract objective
    objective_section = soup.find('h3', string=re.compile('Objective', re.I))
    if objective_section:
        objective_content = objective_section.find_next('p')
        if objective_content:
            parsed_data['objective'] = objective_content.get_text(strip=True)
    
    # Extract environment
    env_section = soup.find('h3', string=re.compile('Environment', re.I))
    if env_section:
        env_list = env_section.find_next(['ul', 'p'])
        if env_list:
            if env_list.name == 'ul':
                parsed_data['environment'] = [li.get_text(strip=True) for li in env_list.find_all('li')]
            else:
                parsed_data['environment'] = [env_list.get_text(strip=True)]
    
    # Extract procedure steps
    procedure_section = soup.find('h3', string=re.compile('Procedure', re.I))
    if procedure_section:
        # Find all list items under procedure
        procedure_list = procedure_section.find_next('ol')
        if procedure_list:
            for li in procedure_list.find_all('li', recursive=False):
                step_text = li.get_text(strip=True, separator=' ')
                parsed_data['procedure_steps'].append(step_text)
    
    # Extract commands from procedure text and body
    # Look for lines that contain EXOS commands
    all_text = soup.get_text(separator='\n')
    
    # More specific command patterns with common EXOS syntax
    command_patterns = [
        r'^\s*(show\s+bgp(?:\s+\w+)*)',
        r'^\s*(show\s+vlan(?:\s+\w+)*)',
        r'^\s*(show\s+iproute(?:\s+\w+)*)',
        r'^\s*(show\s+port(?:\s+[\d:]+)?(?:\s+\w+)*)',
        r'^\s*(show\s+configuration(?:\s+\w+)*)',
        r'^\s*(show\s+\w+(?:\s+\w+)*)',
        r'^\s*(configure\s+bgp\s+(?:routerid|AS-number|neighbor|add)[\s\S]{0,80})',
        r'^\s*(configure\s+vlan\s+[\w<>]+\s+\w+[\s\S]{0,60})',
        r'^\s*(configure\s+iproute\s+add[\s\S]{0,60})',
        r'^\s*(create\s+bgp\s+neighbor[\s\S]{0,80})',
        r'^\s*(create\s+vlan\s+[\w<>-]+)',
        r'^\s*(enable\s+bgp(?:\s+neighbor)?[\s\S]{0,60})',
        r'^\s*(enable\s+ipforwarding\s+[\w<>]+)',
        r'^\s*(enable\s+loopback-mode\s+vlan[\s\S]{0,40})',
        r'^\s*(disable\s+\w+(?:\s+\w+)*)',
    ]
    
    lines = all_text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Skip lines that are too short, too long, or clearly not commands
        if len(line) < 7 or len(line) > 200:
            continue
        
        # Skip lines with too many special characters (likely formatting)
        special_count = line.count('-') + line.count('=') + line.count('|')
        if special_count > 10:
            continue
        
        # Try to match command patterns
        for pattern in command_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                cmd = match.group(1).strip()
                # Clean up the command
                cmd = re.sub(r'\s+', ' ', cmd)  # Normalize whitespace
                cmd = re.sub(r'\s*NOTE:.*$', '', cmd,  flags=re.IGNORECASE)  # Remove NOTE comments
                
                if len(cmd) > 5 and cmd not in parsed_data['commands']:
                    parsed_data['commands'].append(cmd)
                break
    
    # Extract additional notes
    notes_section = soup.find('h3', string=re.compile('Additional notes|Note', re.I))
    if notes_section:
        notes_content = notes_section.find_next(['p', 'div'])
        if notes_content:
            parsed_data['additional_notes'] = notes_content.get_text(strip=True)
    
    return parsed_data

def extract_exos_commands(text: str) -> List[str]:
    """Extract EXOS commands from text."""
    if not text:
        return []
    
    # Common EXOS command patterns - more specific
    exos_patterns = [
        r'^\s*(show\s+[\w\-]+(?:\s+[\w\-]+)*)',
        r'^\s*(configure\s+[\w\-]+(?:\s+[\w\-]+)*)',
        r'^\s*(create\s+[\w\-]+(?:\s+[\w\-]+)*)',
        r'^\s*(enable\s+[\w\-]+(?:\s+[\w\-]+)*)',
        r'^\s*(disable\s+[\w\-]+(?:\s+[\w\-]+)*)',
        r'^\s*(delete\s+[\w\-]+(?:\s+[\w\-]+)*)',
        r'^\s*(unconfigure\s+[\w\-]+(?:\s+[\w\-]+)*)',
    ]
    
    commands = []
    
    # Split text into lines
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and very long lines (likely not commands)
        if not line or len(line) > 200:
            continue
        
        # Skip lines with too many special characters (likely formatting)
        if line.count('-') > 20 or line.count('=') > 10:
            continue
        
        # Check each pattern
        for pattern in exos_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                cmd = match.group(1).strip()
                if len(cmd) > 5 and cmd not in commands:
                    commands.append(cmd)
                break
    
    # Remove duplicates while preserving order
    seen = set()
    unique_commands = []
    for cmd in commands:
        cmd_lower = cmd.lower()
        if cmd_lower not in seen:
            seen.add(cmd_lower)
            unique_commands.append(cmd)
    
    return unique_commands

def auto_extract_platform(parsed_data: Dict, html_content: str) -> str:
    """Auto-detect platform from article content."""
    text = f"{parsed_data['title']} {parsed_data['objective']} {' '.join(parsed_data['environment'])}".lower()
    
    if 'exos' in text or 'switch engine' in text:
        return 'EXOS'
    elif 'voss' in text or 'fabric engine' in text or 'vsp' in text:
        return 'VOSS'
    elif 'eos' in text or 'slx' in text:
        return 'EOS'
    
    return 'EXOS'  # Default

def auto_extract_category(parsed_data: Dict) -> str:
    """Auto-detect category from article title and content."""
    text = f"{parsed_data['title']} {parsed_data['objective']}".lower()
    
    # Check for keywords
    if any(word in text for word in ['bgp', 'ospf', 'routing', 'route', 'rip', 'isis']):
        return 'routing'
    elif any(word in text for word in ['interface', 'port', 'link', 'cable', 'sfp', 'transceiver']):
        return 'interface'
    elif any(word in text for word in ['vlan', 'stp', 'lag', 'mlag', 'eaps', 'switch', 'mac', 'fdb']):
        return 'switching'
    elif any(word in text for word in ['cpu', 'memory', 'performance', 'bandwidth', 'throughput', 'buffer']):
        return 'performance'
    elif any(word in text for word in ['auth', 'radius', 'tacacs', '802.1x', 'security', 'acl', 'firewall']):
        return 'security'
    elif any(word in text for word in ['configure', 'setup', 'installation', 'deployment']):
        return 'configuration'
    
    return 'configuration'  # Default

def auto_extract_subcategory(parsed_data: Dict) -> str:
    """Auto-extract subcategory from title."""
    title = parsed_data['title'].lower()
    
    # Extract key technology names
    keywords = ['bgp', 'ospf', 'vlan', 'lag', 'mlag', 'stp', 'eaps', 'cpu', 'memory', 
                'radius', '802.1x', 'authentication', 'interface', 'port', 'flapping']
    
    for keyword in keywords:
        if keyword in title:
            return keyword.upper() if keyword in ['bgp', 'ospf', 'vlan', 'lag', 'stp', 'cpu'] else keyword.title()
    
    return ''

def auto_extract_symptoms(parsed_data: Dict) -> List[str]:
    """Auto-extract symptoms from article content."""
    symptoms = []
    text = f"{parsed_data['title']} {parsed_data['objective']}".lower()
    
    # Common symptom patterns
    symptom_patterns = {
        'bgp': ['BGP neighbor not establishing', 'BGP session down', 'Routes not being advertised'],
        'ospf': ['OSPF neighbor down', 'OSPF adjacency failure', 'Routes not learned'],
        'interface': ['Interface down', 'Link flapping', 'Port not coming up', 'High error rate'],
        'port': ['Port down', 'Link down', 'No connectivity'],
        'link': ['Link down', 'Connection lost', 'Link flapping'],
        'vlan': ['VLAN connectivity issues', 'Traffic not forwarding', 'VLAN misconfiguration'],
        'lag': ['LAG not forming', 'Port not joining LAG', 'LAG member down'],
        'mlag': ['MLAG peer down', 'MLAG synchronization issues', 'Split-brain scenario'],
        'stp': ['STP loop detected', 'Broadcast storm', 'Topology change'],
        'eaps': ['EAPS ring failure', 'Primary port down', 'Ring protection issues'],
        'cpu': ['High CPU utilization', 'System slow', 'Process consuming CPU'],
        'memory': ['Memory exhaustion', 'Out of memory errors', 'Memory leak'],
        'radius': ['RADIUS authentication failure', 'AAA server unreachable', 'Login denied'],
        '802.1x': ['802.1X authentication failure', 'Client cannot connect', 'Port not authorized'],
        'authentication': ['Authentication failure', 'Login denied', 'Access denied'],
        'flapping': ['Port flapping', 'Link up/down cycling', 'Unstable connection']
    }
    
    for keyword, symptom_list in symptom_patterns.items():
        if keyword in text:
            symptoms.extend(symptom_list)
            break
    
    if not symptoms:
        symptoms = ['See article for specific symptoms']
    
    return symptoms[:5]  # Limit to 5

def auto_extract_root_causes(parsed_data: Dict) -> List[str]:
    """Auto-extract common root causes based on category."""
    text = f"{parsed_data['title']} {parsed_data['objective']}".lower()
    
    # Category-specific root causes
    if 'bgp' in text:
        return [
            'Incorrect AS number configuration',
            'Loopback interface misconfiguration',
            'Missing route to BGP neighbor',
            'Authentication mismatch',
            'Firewall blocking BGP port (179)'
        ]
    elif 'ospf' in text:
        return [
            'Area mismatch',
            'Network type mismatch',
            'Hello/Dead timer mismatch',
            'MTU mismatch',
            'Authentication failure'
        ]
    elif any(word in text for word in ['interface', 'port', 'link', 'flapping']):
        return [
            'Defective SFP/transceiver',
            'Cable issues (damaged, incorrect type)',
            'Duplex mismatch',
            'Speed mismatch',
            'Physical layer issues'
        ]
    elif 'vlan' in text:
        return [
            'VLAN not created',
            'Port not assigned to correct VLAN',
            'Trunk configuration incorrect',
            'Native VLAN mismatch',
            'VLAN pruning issues'
        ]
    elif any(word in text for word in ['lag', 'mlag']):
        return [
            'LACP configuration mismatch',
            'LAG member port issues',
            'Speed/duplex mismatch on members',
            'Peer configuration mismatch',
            'ISC link issues'
        ]
    elif 'stp' in text or 'loop' in text:
        return [
            'STP not enabled',
            'Incorrect bridge priority',
            'Port in wrong STP state',
            'Duplicate bridge IDs',
            'Physical loop in topology'
        ]
    elif 'cpu' in text or 'memory' in text:
        return [
            'Software bug causing resource leak',
            'Excessive logging',
            'Protocol instability',
            'DoS attack',
            'Insufficient system resources'
        ]
    elif any(word in text for word in ['auth', 'radius', '802.1x']):
        return [
            'Incorrect RADIUS server configuration',
            'Authentication credentials mismatch',
            'RADIUS server unreachable',
            'Shared secret mismatch',
            'Port security configuration error'
        ]
    
    return ['See article for root cause analysis']

def auto_extract_keywords(parsed_data: Dict) -> List[str]:
    """Auto-extract keywords from title and content."""
    # Extract from title
    title_words = re.findall(r'\b[A-Z][A-Za-z0-9.]+\b', parsed_data['title'])
    
    # Common network keywords
    network_keywords = ['BGP', 'OSPF', 'VLAN', 'STP', 'LAG', 'MLAG', 'EAPS', 'interface', 
                       'port', 'routing', 'switching', 'troubleshooting', 'configuration',
                       'EXOS', 'VOSS', 'authentication', 'RADIUS', 'CPU', 'memory']
    
    keywords = []
    text = parsed_data['title'].lower()
    
    for keyword in network_keywords:
        if keyword.lower() in text:
            keywords.append(keyword)
    
    # Add title words
    keywords.extend([w for w in title_words if len(w) > 3 and w not in keywords])
    
    return list(set(keywords))[:10]  # Limit to 10 unique

def auto_extract_version(parsed_data: Dict) -> str:
    """Auto-extract EXOS version from environment section."""
    env_text = ' '.join(parsed_data['environment']).lower()
    
    # Look for version patterns
    version_pattern = r'(\d+\.\d+(?:\.\d+)?)'
    matches = re.findall(version_pattern, env_text)
    
    if matches:
        return f"EXOS {matches[0]}+"
    
    # Check for "all versions" or similar
    if 'all' in env_text or not matches:
        return 'All versions'
    
    return 'All versions'

def extract_with_llm(url: str, parsed_data: Dict, article_number: int) -> Dict:
    """
    Extract KB article metadata using LLM (Llama 3.3 70B)
    
    Args:
        url: Source URL
        parsed_data: Parsed HTML content
        article_number: Sequential article number
    
    Returns:
        Complete KB article dictionary with LLM-extracted metadata
    """
    if not LLM_AVAILABLE:
        print_error("LLM extraction not available. Install dependencies: pip install openai tenacity loguru")
        return None
    
    try:
        # Initialize LLM extractor
        print_info("Initializing LLM extractor (Llama 3.3 70B via Groq)...")
        extractor = LLMArticleExtractor()
        
        # Extract metadata
        print_info("🤖 Extracting metadata with AI... (this may take 10-30 seconds)")
        metadata = extractor.extract_metadata(parsed_data)
        
        # Show LLM stats
        if '_llm_stats' in metadata:
            stats = metadata['_llm_stats']
            print_success(f"Extraction completed in {stats['duration_ms']}ms")
            print_info(f"Tokens used: {stats['tokens_used']} (${stats['cost_usd']:.4f})")
            print_info(f"Model: {stats['model']}")
        
        # Generate article ID based on extracted platform and category
        platform = metadata.get('platform', 'EXOS')
        category = metadata.get('category', 'GENERAL').upper()
        article_id = f"KB-{platform}-{category}-{article_number:03d}"
        
        # Build complete article
        article = {
            'article_id': article_id,
            'title': metadata.get('title') or parsed_data.get('title', 'Untitled Article'),
            'source_url': url,
            'platform': metadata.get('platform', 'EXOS'),
            'category': metadata.get('category', 'general'),
            'subcategory': metadata.get('subcategory', ''),
            'version': metadata.get('version', 'All versions'),
            'symptoms': metadata.get('symptoms', []),
            'root_causes': metadata.get('root_causes', []),
            'diagnostic_commands': metadata.get('diagnostic_commands', []),
            'remediation_steps': metadata.get('remediation_steps', []),
            'keywords': metadata.get('keywords', []),
            'tested': False,
            'confidence': 0.85,  # High confidence for LLM extraction
            'extraction_method': 'llm',
            'llm_model': metadata.get('_llm_stats', {}).get('model', 'llama-3.3-70b-versatile'),
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Validate article
        print_info("Validating extracted data...")
        validator = ArticleValidator()
        is_valid, quality_score, errors, warnings = validator.validate_article(article)
        
        # Show validation results
        print(f"\n{'='*70}")
        print(f"Quality Score: {quality_score}/100 ({validator.get_quality_label(quality_score)})")
        
        if errors:
            print(f"\n🔴 Errors: {len(errors)}")
            for error in errors[:5]:  # Show first 5
                print(f"  - {error}")
        
        if warnings:
            print(f"\n⚠️  Warnings: {len(warnings)}")
            for warning in warnings[:5]:  # Show first 5
                print(f"  - {warning}")
        
        print(f"{'='*70}\n")
        
        # Add quality score to article
        article['quality_score'] = quality_score
        article['validation_errors'] = errors
        article['validation_warnings'] = warnings
        
        return article
        
    except Exception as e:
        print_error(f"LLM extraction failed: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def create_kb_article(url: str, parsed_data: Dict, user_metadata: Dict) -> Dict:
    """Create structured KB article from parsed data and user input."""
    
    # Generate article ID
    article_id = f"KB-EXOS-{user_metadata['category'].upper()}-{user_metadata['article_number']:03d}"
    
    # Extract commands from parsed data
    all_text = ' '.join(parsed_data['procedure_steps'])
    all_commands = extract_exos_commands(all_text)
    
    # Add commands from the commands list (already extracted)
    for cmd in parsed_data['commands']:
        # Clean and validate each command
        cmd_clean = cmd.strip()
        if len(cmd_clean) > 5 and len(cmd_clean) < 200:
            # Check if it starts with a valid EXOS command
            if any(cmd_clean.lower().startswith(verb) for verb in ['show', 'configure', 'create', 'enable', 'disable', 'delete', 'unconfigure']):
                all_commands.append(cmd_clean)
    
    # Remove duplicates
    all_commands = list(dict.fromkeys(all_commands))[:20]  # Max 20 commands
    
    # Build article structure
    article = {
        "article_id": article_id,
        "source_url": url,
        "title": parsed_data['title'] or user_metadata['title'],
        "vendor": "Extreme Networks",
        "platform": user_metadata['platform'],
        "category": user_metadata['category'],
        "subcategory": user_metadata['subcategory'],
        "symptoms": user_metadata['symptoms'],
        "root_causes": user_metadata['root_causes'],
        "diagnostic_commands": [],
        "remediation_steps": [],
        "configuration_example": {
            "scenario": parsed_data['objective'],
            "commands": all_commands[:10] if all_commands else []  # Top 10 commands
        },
        "additional_notes": parsed_data['additional_notes'],
        "related_articles": [],
        "keywords": user_metadata['keywords'],
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "confidence_tags": {
            "official_source": True,
            "tested": user_metadata.get('tested', False),
            "version_specific": user_metadata.get('version', "All versions")
        }
    }
    
    # Process procedure steps into remediation steps
    for idx, step in enumerate(parsed_data['procedure_steps'][:10], 1):  # Max 10 steps
        # Extract commands from step description
        step_commands = []
        
        # Split step into lines
        lines = step.split('\n')
        for line in lines:
            line_clean = line.strip()
            
            # Look for patterns like "description: command" or just "command"
            if ':' in line_clean:
                parts = line_clean.split(':', 1)
                if len(parts) == 2:
                    potential_cmd = parts[1].strip()
                    # Check if it's an actual EXOS command (starts with lowercase command verb)
                    if any(potential_cmd.lower().startswith(cmd) for cmd in ['show ', 'configure ', 'create ', 'enable ', 'disable ', 'delete ', 'unconfigure ']):
                        if 5 < len(potential_cmd) < 150 and not potential_cmd[0].isupper():
                            step_commands.append(potential_cmd)
            
            # Also check if line itself is a command (lowercase start)
            if any(line_clean.lower().startswith(cmd) for cmd in ['show ', 'configure ', 'create ', 'enable ', 'disable ', 'delete ', 'unconfigure ']):
                if 5 < len(line_clean) < 150 and not line_clean[0].isupper():
                    step_commands.append(line_clean)
        
        # If no commands extracted, try the extract_exos_commands function
        if not step_commands:
            extracted = extract_exos_commands(step)
            # Filter out lines that start with uppercase (likely descriptions)
            step_commands = [cmd for cmd in extracted if cmd and not cmd[0].isupper()]
        
        article['remediation_steps'].append({
            "step": idx,
            "description": step[:250],  # Limit description length
            "commands": step_commands[:5] if step_commands else [],  # Max 5 commands per step
            "expected_output": ""  # Can be filled manually or left for user to add
        })
    
    # Identify diagnostic commands (show commands only)
    diagnostic_cmds = []
    for cmd in all_commands:
        cmd_lower = cmd.lower().strip()
        # Only "show" commands are diagnostic
        if cmd_lower.startswith('show ') and len(cmd) < 100:
            diagnostic_cmds.append(cmd)
    
    # Limit and deduplicate
    article['diagnostic_commands'] = list(dict.fromkeys(diagnostic_cmds))[:10]  # Top 10 unique
    
    return article

def save_article(article: Dict, output_dir: str) -> str:
    """Save article as JSON file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{article['article_id']}.json"
    filepath = output_path / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(article, f, indent=2, ensure_ascii=False)
    
    return str(filepath)

def import_to_chromadb(article: Dict, chromadb_host: str = 'localhost', chromadb_port: int = 8000):
    """Import article to ChromaDB."""
    try:
        import chromadb
        
        print_info(f"Connecting to ChromaDB at {chromadb_host}:{chromadb_port}")
        client = chromadb.HttpClient(host=chromadb_host, port=chromadb_port)
        
        # Get or create collection
        collection = client.get_or_create_collection(
            name="kb_articles",
            metadata={"description": "Network troubleshooting knowledge base"}
        )
        
        # Create document text for embedding
        doc_text = f"""
        {article['title']}
        
        Vendor: {article['vendor']}
        Platform: {article['platform']}
        Category: {article['category']} - {article['subcategory']}
        
        Symptoms: {', '.join(article['symptoms'])}
        Root Causes: {', '.join(article['root_causes'])}
        
        Diagnostic Commands: {', '.join(article['diagnostic_commands'])}
        
        Remediation:
        {chr(10).join([f"Step {s['step']}: {s['description']}" for s in article['remediation_steps']])}
        
        Keywords: {', '.join(article['keywords'])}
        """
        
        # Add to collection
        collection.add(
            documents=[doc_text],
            metadatas=[{
                "article_id": article['article_id'],
                "title": article['title'],
                "vendor": article['vendor'],
                "platform": article['platform'],
                "category": article['category'],
                "subcategory": article['subcategory'],
                "source_url": article['source_url']
            }],
            ids=[article['article_id']]
        )
        
        print_success(f"Article imported to ChromaDB: {article['article_id']}")
        print_info(f"Collection now has {collection.count()} articles")
        
    except Exception as e:
        print_error(f"Failed to import to ChromaDB: {e}")
        print_warning("Article saved as JSON but not imported to ChromaDB")

def display_article_preview(article: Dict):
    """Display a preview of the created article."""
    print_header("Article Preview")
    
    print(f"{Colors.BOLD}Article ID:{Colors.ENDC} {article['article_id']}")
    print(f"{Colors.BOLD}Title:{Colors.ENDC} {article['title']}")
    print(f"{Colors.BOLD}Platform:{Colors.ENDC} {article['platform']}")
    print(f"{Colors.BOLD}Category:{Colors.ENDC} {article['category']} / {article['subcategory']}")
    
    print(f"\n{Colors.BOLD}Symptoms:{Colors.ENDC}")
    for symptom in article['symptoms']:
        print(f"  • {symptom}")
    
    print(f"\n{Colors.BOLD}Root Causes:{Colors.ENDC}")
    for cause in article['root_causes']:
        print(f"  • {cause}")
    
    print(f"\n{Colors.BOLD}Diagnostic Commands ({len(article['diagnostic_commands'])}):{Colors.ENDC}")
    for cmd in article['diagnostic_commands'][:5]:
        print(f"  • {cmd}")
    if len(article['diagnostic_commands']) > 5:
        print(f"  ... and {len(article['diagnostic_commands']) - 5} more")
    
    print(f"\n{Colors.BOLD}Remediation Steps ({len(article['remediation_steps'])}):{Colors.ENDC}")
    for idx, step in enumerate(article['remediation_steps'][:3], 1):
        description = step.get('description') or step.get('step', 'No description')
        print(f"  {idx}. {description[:80]}...")
    if len(article['remediation_steps']) > 3:
        print(f"  ... and {len(article['remediation_steps']) - 3} more steps")
    
    print(f"\n{Colors.BOLD}Keywords:{Colors.ENDC} {', '.join(article['keywords'])}")

def main():
    """Main interactive workflow."""
    print_header("KB Article Creator for Smart NOC")
    
    print_info("This tool intelligently creates structured KB articles from Extreme Networks support articles.")
    print_info("✨ Auto-extracts: platform, category, symptoms, root causes, keywords, and more!")
    print_info("📝 You can process articles one at a time or in batch mode.\n")
    
    # Check if import to ChromaDB is requested
    import_to_db = '--import' in sys.argv or '--load' in sys.argv
    
    # Get output directory
    default_output = "kb_sources/validated_articles"
    output_dir = get_user_input("Output directory for JSON files", default=default_output, required=False)
    if not output_dir:
        output_dir = default_output
    
    # Get article number counter
    existing_files = list(Path(output_dir).glob("KB-EXOS-*.json")) if Path(output_dir).exists() else []
    next_article_num = len(existing_files) + 1
    
    # Main processing loop
    while True:
        print_header(f"Article #{next_article_num}")
        
        # Step 1: Get URL
        url = get_user_input("Enter Extreme Networks article URL")
        
        if not url:
            print_warning("No URL provided. Exiting.")
            break
        
        # Validate URL
        if 'extreme-networks.my.site.com' not in url:
            print_warning("URL doesn't appear to be from Extreme Networks support portal.")
            confirm = get_user_input("Continue anyway? (y/n)", default="y")
            if confirm.lower() != 'y':
                continue
        
        # Step 2: Fetch content
        html_content = fetch_article_content(url)
        if not html_content:
            print_error("Failed to fetch article. Try another URL.")
            continue
        
        # Step 3: Parse content
        print_info("Parsing article content...")
        parsed_data = parse_extreme_article(html_content)
        
        if parsed_data['title']:
            print_success(f"Article parsed: {parsed_data['title']}")
        
        # Step 4: Collect user metadata
        print_header("Article Metadata")
        
        # Choose extraction method
        article = None
        
        if LLM_AVAILABLE:
            print_info("📊 Extraction Methods Available:")
            print("  1. 🤖 LLM Extraction (Llama 3.3 70B) - Best quality, AI-powered")
            print("  2. 📝 Regex Extraction - Fast, rule-based, manual review recommended")
            
            extraction_method = get_user_input(
                "Choose extraction method (1=LLM, 2=Regex)", 
                default="1"
            )
            
            use_llm = extraction_method == "1"
        else:
            print_warning("LLM extraction not available. Using regex extraction.")
            print_info("To enable LLM: pip install openai tenacity loguru")
            use_llm = False
        
        if use_llm:
            # LLM extraction (recommended)
            article = extract_with_llm(url, parsed_data, next_article_num)
            
            if not article:
                print_error("LLM extraction failed. Falling back to regex extraction.")
                use_llm = False
        
        # Only do regex extraction if LLM didn't succeed
        if not use_llm:
            # Regex extraction (legacy method)
            print_info("Using regex-based extraction...")
            
            # Ask if user wants auto-extraction
            auto_extract = get_user_input(
                "Auto-extract metadata from article content? (Recommended) (y/n)", 
                default="y"
            ).lower() == 'y'
            
            user_metadata = {}
            
            if auto_extract:
                print_info("Auto-extracting metadata from article...")
                
                # Auto-extract all fields
                user_metadata['title'] = parsed_data['title'] if parsed_data['title'] else "Untitled Article"
                user_metadata['platform'] = auto_extract_platform(parsed_data, html_content)
                user_metadata['category'] = auto_extract_category(parsed_data)
                user_metadata['subcategory'] = auto_extract_subcategory(parsed_data)
                user_metadata['symptoms'] = auto_extract_symptoms(parsed_data)
                user_metadata['root_causes'] = auto_extract_root_causes(parsed_data)
                user_metadata['keywords'] = auto_extract_keywords(parsed_data)
                user_metadata['tested'] = False
                user_metadata['version'] = auto_extract_version(parsed_data)
                
                # Show extracted metadata
                print_success(f"Platform detected: {user_metadata['platform']}")
                print_success(f"Category detected: {user_metadata['category']}")
                print_success(f"Subcategory detected: {user_metadata['subcategory']}")
                print_success(f"Extracted {len(user_metadata['symptoms'])} symptoms")
                print_success(f"Extracted {len(user_metadata['root_causes'])} root causes")
                print_success(f"Extracted {len(user_metadata['keywords'])} keywords")
                
                # Allow user to override if needed
                print()
                override = get_user_input("Override any fields? (y/n)", default="n").lower() == 'y'
                
                if override:
                    print_info("\nEnter new value or press Enter to keep auto-extracted value")
                    
                    title_override = get_user_input(f"Title", default=user_metadata['title'], required=False)
                    if title_override:
                        user_metadata['title'] = title_override
                    
                    platform_override = get_user_input(f"Platform", default=user_metadata['platform'], required=False)
                    if platform_override:
                        user_metadata['platform'] = platform_override
                    
                    category_override = get_user_input(f"Category", default=user_metadata['category'], required=False)
                    if category_override:
                        user_metadata['category'] = category_override
                    
                    subcategory_override = get_user_input(f"Subcategory", default=user_metadata['subcategory'], required=False)
                    if subcategory_override:
                        user_metadata['subcategory'] = subcategory_override
            
            else:
                # Manual entry (original behavior)
                print_info("Manual metadata entry mode")
                
                user_metadata['title'] = get_user_input(
                    "Article title", 
                    default=parsed_data['title'] if parsed_data['title'] else None
                )
                
                user_metadata['platform'] = get_user_input("Platform (EXOS/VOSS/EOS)", default="EXOS")
                
                print_info("\nCategories: interface, routing, switching, performance, security, configuration")
                user_metadata['category'] = get_user_input("Category", default="interface")
                
                user_metadata['subcategory'] = get_user_input(
                    "Subcategory (e.g., flapping, BGP, VLAN, CPU)", 
                    default=""
                )
                
                user_metadata['symptoms'] = get_multiline_input("\nSymptoms/Issues")
                if not user_metadata['symptoms']:
                    user_metadata['symptoms'] = ["No symptoms provided"]
                
                user_metadata['root_causes'] = get_multiline_input("\nCommon Root Causes")
                if not user_metadata['root_causes']:
                    user_metadata['root_causes'] = ["See remediation steps"]
                
                user_metadata['keywords'] = get_multiline_input("\nKeywords/Tags")
                if not user_metadata['keywords']:
                    # Auto-generate from title
                    user_metadata['keywords'] = user_metadata['title'].lower().split()[:5]
                
                user_metadata['tested'] = get_user_input("Have you tested this? (y/n)", default="n").lower() == 'y'
                
                user_metadata['version'] = get_user_input("EXOS version (or 'All versions')", default="All versions")
            
            user_metadata['article_number'] = next_article_num
            
            # Step 5: Create article (for regex extraction only)
            print_info("\nCreating KB article...")
            article = create_kb_article(url, parsed_data, user_metadata)
        
        # If we don't have an article yet, something went wrong
        if not article:
            print_error("Failed to create article. Please try again.")
            continue
        
        # Step 6: Display preview
        display_article_preview(article)
        
        # Step 7: Confirm and save
        print()
        confirm = get_user_input("Save this article? (y/n)", default="y")
        
        if confirm.lower() == 'y':
            filepath = save_article(article, output_dir)
            print_success(f"Article saved: {filepath}")
            
            # Step 8: Import to ChromaDB if requested
            if import_to_db:
                chromadb_host = get_user_input("ChromaDB host", default="localhost", required=False) or "localhost"
                chromadb_port = int(get_user_input("ChromaDB port", default="8000", required=False) or "8000")
                import_to_chromadb(article, chromadb_host, chromadb_port)
            
            next_article_num += 1
        else:
            print_warning("Article discarded.")
        
        # Step 9: Continue or exit
        print()
        another = get_user_input("Process another article? (y/n)", default="y")
        if another.lower() != 'y':
            break
    
    print_header("Summary")
    print_success(f"Created {next_article_num - 1} KB articles")
    print_info(f"Articles saved in: {output_dir}")
    
    if not import_to_db:
        print_info("\nTo import articles to ChromaDB later, run:")
        print(f"  python scripts/kb_bulk_import.py --input {output_dir}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Operation cancelled by user.{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

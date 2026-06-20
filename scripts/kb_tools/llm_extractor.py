"""
LLM-Based KB Article Extractor
Uses Groq's Llama 3.3 70B model for intelligent metadata extraction
"""

import json
import os
import time
from typing import Dict, Any, Optional
from loguru import logger
import openai
from tenacity import retry, stop_after_attempt, wait_exponential


class LLMArticleExtractor:
    """Extract structured metadata from KB articles using LLM"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM extractor with Llama 3.3 70B model
        
        Args:
            api_key: Groq API key (reads from .env if not provided)
        """
        # Hardcoded configuration (Option 2 - simple approach)
        self.model = "llama-3.3-70b-versatile"  # Llama 3.3 70B (128K context)
        self.api_base = "https://api.groq.com/openai/v1"
        self.max_tokens = 2500  # Enough for structured output
        self.temperature = 0.1  # Low temperature for consistent extraction
        self.timeout = 45  # Longer timeout for complex articles
        
        # Get API key from parameter or environment
        if api_key:
            self.api_key = api_key
        else:
            # Try to read from root .env file
            env_file = "/home/user/ng-iam/smart-noc/.env"
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('LLM_API_KEY='):
                            self.api_key = line.split('=', 1)[1].strip()
                            break
            else:
                raise ValueError("No API key provided and .env file not found")
        
        # Initialize OpenAI client (Groq uses OpenAI-compatible API)
        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=float(self.timeout)
            )
            logger.info(f"LLM Extractor initialized: {self.model} via Groq")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise
    
    def build_extraction_prompt(self, article_data: Dict[str, Any]) -> str:
        """
        Build extraction prompt with examples
        
        Args:
            article_data: Parsed article data from BeautifulSoup
        
        Returns:
            Formatted prompt for LLM
        """
        title = article_data.get('title', '')
        objective = article_data.get('objective', '')
        environment = article_data.get('environment', '')
        procedure = article_data.get('procedure', '')
        
        # Truncate procedure if too long (keep first 3000 chars)
        if len(procedure) > 3000:
            procedure = procedure[:3000] + "...[truncated]"
        
        prompt = f"""You are an expert network engineer analyzing Extreme Networks technical documentation.

Extract structured metadata from this KB article and return ONLY valid JSON (no markdown, no explanation).

ARTICLE TITLE: {title}

OBJECTIVE: {objective}

ENVIRONMENT: {environment}

PROCEDURE:
{procedure}

Extract the following information:

1. **title**: Concise article title (use the ARTICLE TITLE above or create descriptive title from content)

2. **platform**: Exact platform name (EXOS, VOSS, EOS, IQEngine, XIQ, SLX, or Multi-Platform)
   - Look for keywords: "EXOS", "VOSS", "Fabric Engine", "VSP", "ERS", "SLX", "XIQ"
   
3. **category**: Main technical category (routing, interface, switching, vlan, security, performance, configuration, monitoring)

4. **subcategory**: Specific protocol or feature (BGP, OSPF, VLAN, LAG, ACL, QoS, SNMP, etc.)

5. **version**: Software version if mentioned (e.g., "22.1", "8.10", "16.1")

6. **symptoms**: Array of 3-5 observable symptoms that would lead to this article
   - Write from NOC operator perspective
   - Focus on what they would see in logs/monitoring
   
7. **root_causes**: Array of 5 common root causes for these symptoms
   - Technical, specific, actionable
   
8. **diagnostic_commands**: Array of CLI commands to diagnose the issue
   - MUST be valid CLI commands starting with: show, display, trace, ping, debug
   - NO descriptions or explanations
   - Format: ["show bgp", "show vlan", "show port 1:1 statistics"]
   
9. **remediation_steps**: Array of objects with "step" (description) and "commands" (array of CLI commands)
   - Commands MUST be action commands: configure, create, enable, disable, set, delete
   - NO show commands in remediation
   - Format: {{"step": "Enable BGP", "commands": ["enable bgp", "configure bgp AS 65000"]}}
   
10. **keywords**: Array of 5-10 relevant technical keywords
   - Include protocol names, hardware models, technical terms

CRITICAL COMMAND SYNTAX RULES (VENDOR-SPECIFIC):

**EXOS Commands (Extreme Networks Switch Engine):**
- Diagnostic: "show configuration", "show ports", "show vlan", "show switch", "show version"
- Configuration: "configure vlan <name>", "create vlan <name>", "enable ipforwarding"
- NO "configure terminal" (that's Cisco IOS)
- NO "set interface" (that's Cisco/Juniper)
- NO "show running-config" (use "show configuration")
- Format: Single-line commands without config mode

**VOSS/Fabric Engine Commands:**
- Diagnostic: "show running-config", "show interface", "show ip route"
- Configuration: "interface vlan <id>", "ip address <ip> <mask>"
- Uses config hierarchy like Cisco but different syntax

**General Rules:**
- If platform is EXOS: Use EXOS syntax exclusively
- If platform is VOSS: Use VOSS/Fabric Engine syntax
- If platform is Multi-Platform or unsure: Use generic descriptions instead of specific commands
- NEVER mix Cisco IOS syntax with EXOS (common mistake!)
- If source article shows actual commands, prefer those over generating new ones
- If uncertain about exact syntax: Use generic action descriptions like "Configure interface settings" instead of wrong commands

**Invalid Command Examples to AVOID:**
❌ "configure terminal" (Cisco, not EXOS)
❌ "set interface ge-0/0/1" (Juniper, not EXOS)
❌ "show running-config" (Cisco, EXOS uses "show configuration")
❌ "interface vlan 10" (Cisco/VOSS, EXOS uses "configure vlan")

EXAMPLE 1 - EXOS BGP Configuration:
{{
  "title": "Configure BGP Routing on EXOS",
  "platform": "EXOS",
  "category": "routing",
  "subcategory": "BGP",
  "version": "22.1",
  "symptoms": [
    "BGP neighbor state showing Idle or Connect",
    "Routes not being learned from BGP peer",
    "BGP session flapping in logs"
  ],
  "root_causes": [
    "BGP neighbor misconfiguration",
    "Routing policy blocking updates",
    "TCP port 179 blocked by firewall",
    "AS number mismatch",
    "Authentication failure"
  ],
  "diagnostic_commands": [
    "show bgp neighbor",
    "show bgp routes all",
    "show configuration bgp"
  ],
  "remediation_steps": [
    {{
      "step": "Configure BGP neighbor",
      "commands": [
        "configure bgp neighbor 192.168.1.1 remote-as 65001",
        "enable bgp neighbor 192.168.1.1"
      ]
    }},
    {{
      "step": "Verify BGP policy",
      "commands": [
        "configure bgp export policy allow-all"
      ]
    }}
  ],
  "keywords": ["BGP", "routing", "neighbor", "AS", "peer", "EXOS", "configuration"]
}}

EXAMPLE 2 - EXOS Interface Configuration:
{{
  "title": "Configure VLAN and Port Settings on EXOS",
  "platform": "EXOS",
  "category": "configuration",
  "subcategory": "interface",
  "version": "32.6",
  "diagnostic_commands": [
    "show ports",
    "show vlan",
    "show configuration",
    "show switch"
  ],
  "remediation_steps": [
    {{
      "step": "Create and configure VLAN",
      "commands": [
        "create vlan data",
        "configure vlan data ipaddress 192.168.1.1/24",
        "enable ipforwarding vlan data"
      ]
    }},
    {{
      "step": "Assign ports to VLAN",
      "commands": [
        "configure vlan data add ports 1:1-1:10 untagged"
      ]
    }}
  ]
}}

CRITICAL RULES:
- Return ONLY the JSON object, no markdown code blocks
- All commands must be valid CLI syntax FOR THE SPECIFIC PLATFORM (EXOS ≠ Cisco ≠ Juniper)
- Diagnostic commands: show/display/trace only (platform-specific syntax)
- Remediation commands: configure/create/enable/set/delete only (platform-specific syntax)
- No descriptions in command arrays
- NEVER use Cisco IOS syntax for EXOS platforms
- If uncertain about command syntax, use generic descriptions instead of wrong commands
- If a field cannot be determined, use reasonable defaults
- Prefer extracting actual commands from article content over generating new ones

Extract now:"""
        
        return prompt
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def extract_metadata(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata using LLM
        
        Args:
            article_data: Parsed article data from BeautifulSoup
        
        Returns:
            Extracted metadata dictionary
        
        Raises:
            Exception if extraction fails after retries
        """
        start_time = time.time()
        
        try:
            # Build prompt
            user_prompt = self.build_extraction_prompt(article_data)
            
            logger.info(f"Sending extraction request to {self.model}...")
            
            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured data from technical documentation. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.timeout
            )
            
            # Extract response
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            try:
                metadata = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Response content: {content[:500]}")
                raise
            
            # Calculate metrics
            duration_ms = int((time.time() - start_time) * 1000)
            tokens_used = response.usage.total_tokens
            
            logger.info(f"✅ LLM extraction completed in {duration_ms}ms, {tokens_used} tokens")
            
            # Add metadata
            metadata['_llm_stats'] = {
                'model': self.model,
                'duration_ms': duration_ms,
                'tokens_used': tokens_used,
                'cost_usd': tokens_used * 0.00000027  # $0.27 per 1M tokens
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            raise
    
    def extract_with_fallback(
        self, 
        article_data: Dict[str, Any],
        fallback_extractor=None
    ) -> Dict[str, Any]:
        """
        Extract with fallback to regex-based extraction
        
        Args:
            article_data: Parsed article data
            fallback_extractor: Function to call if LLM fails
        
        Returns:
            Extracted metadata (LLM or fallback)
        """
        try:
            return self.extract_metadata(article_data)
        except Exception as e:
            logger.warning(f"LLM extraction failed, using fallback: {e}")
            if fallback_extractor:
                return fallback_extractor(article_data)
            else:
                raise


# Convenience function for simple usage
def extract_with_llm(article_data: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple function to extract metadata using LLM
    
    Args:
        article_data: Parsed article from BeautifulSoup
        api_key: Optional Groq API key
    
    Returns:
        Extracted metadata dictionary
    """
    extractor = LLMArticleExtractor(api_key=api_key)
    return extractor.extract_metadata(article_data)


if __name__ == "__main__":
    # Test extraction
    logger.info("LLM Extractor module loaded successfully")
    logger.info(f"Model: llama-3.3-70b-versatile via Groq")
    logger.info("Usage: extractor = LLMArticleExtractor(); metadata = extractor.extract_metadata(article_data)")

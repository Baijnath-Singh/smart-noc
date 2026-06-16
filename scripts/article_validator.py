"""
KB Article Validator
Validates quality and completeness of extracted KB articles
"""

import re
from typing import Dict, Any, List, Tuple
from loguru import logger


class ArticleValidator:
    """Validate KB article quality and structure"""
    
    # Valid platform values
    VALID_PLATFORMS = [
        'EXOS', 'VOSS', 'EOS', 'IQEngine', 'XIQ', 
        'SLX', 'Multi-Platform', 'Unknown'
    ]
    
    # Valid category values
    VALID_CATEGORIES = [
        'routing', 'interface', 'switching', 'vlan', 
        'security', 'performance', 'configuration', 
        'monitoring', 'hardware', 'general'
    ]
    
    # Command prefixes
    DIAGNOSTIC_PREFIXES = ['show', 'display', 'trace', 'ping', 'debug', 'get']
    REMEDIATION_PREFIXES = ['configure', 'create', 'enable', 'disable', 'set', 'delete', 'unconfigure', 'modify']
    
    def __init__(self):
        """Initialize validator"""
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_article(self, article: Dict[str, Any]) -> Tuple[bool, int, List[str], List[str]]:
        """
        Validate complete article structure and quality
        
        Args:
            article: Complete KB article dictionary
        
        Returns:
            (is_valid, quality_score, errors, warnings)
            - is_valid: True if article meets minimum requirements
            - quality_score: 0-100 score
            - errors: List of critical errors
            - warnings: List of quality warnings
        """
        self.validation_errors = []
        self.validation_warnings = []
        
        score = 100  # Start with perfect score, deduct for issues
        
        # Required fields
        required_fields = [
            'article_id', 'title', 'platform', 'category',
            'symptoms', 'root_causes', 'diagnostic_commands',
            'remediation_steps', 'keywords'
        ]
        
        for field in required_fields:
            if field not in article or not article[field]:
                self.validation_errors.append(f"Missing required field: {field}")
                score -= 15
        
        if self.validation_errors:
            return False, max(0, score), self.validation_errors, self.validation_warnings
        
        # Validate platform
        if article['platform'] not in self.VALID_PLATFORMS:
            self.validation_warnings.append(f"Invalid platform: {article['platform']}")
            score -= 5
        
        # Validate category
        if article['category'] not in self.VALID_CATEGORIES:
            self.validation_warnings.append(f"Invalid category: {article['category']}")
            score -= 5
        
        # Validate symptoms (should have 3-5)
        symptom_count = len(article['symptoms'])
        if symptom_count < 3:
            self.validation_warnings.append(f"Only {symptom_count} symptoms (recommend 3-5)")
            score -= 5
        elif symptom_count > 7:
            self.validation_warnings.append(f"Too many symptoms: {symptom_count} (recommend 3-5)")
            score -= 3
        
        # Validate root causes (should have 3-7)
        cause_count = len(article['root_causes'])
        if cause_count < 3:
            self.validation_warnings.append(f"Only {cause_count} root causes (recommend 5)")
            score -= 5
        elif cause_count > 10:
            self.validation_warnings.append(f"Too many root causes: {cause_count}")
            score -= 3
        
        # Validate diagnostic commands
        diag_score = self._validate_diagnostic_commands(article['diagnostic_commands'])
        score += diag_score  # This adds negative value if issues found
        
        # Validate remediation steps
        remed_score = self._validate_remediation_steps(article['remediation_steps'])
        score += remed_score  # This adds negative value if issues found
        
        # Validate keywords (should have 5-10)
        keyword_count = len(article['keywords'])
        if keyword_count < 5:
            self.validation_warnings.append(f"Only {keyword_count} keywords (recommend 5-10)")
            score -= 3
        
        # Check for junk data patterns
        junk_score = self._check_for_junk_data(article)
        score += junk_score
        
        # Final score
        final_score = max(0, min(100, score))
        is_valid = final_score >= 60  # 60+ is acceptable
        
        return is_valid, final_score, self.validation_errors, self.validation_warnings
    
    def _validate_diagnostic_commands(self, commands: List[str]) -> int:
        """
        Validate diagnostic commands
        
        Returns:
            Score adjustment (negative for issues)
        """
        if not commands:
            self.validation_errors.append("No diagnostic commands found")
            return -20
        
        score_adjustment = 0
        
        for i, cmd in enumerate(commands):
            cmd_lower = cmd.lower().strip()
            
            # Check if empty
            if not cmd_lower:
                self.validation_warnings.append(f"Empty diagnostic command at index {i}")
                score_adjustment -= 5
                continue
            
            # Check if too short (likely invalid)
            if len(cmd_lower) < 5:
                self.validation_warnings.append(f"Suspicious short command: '{cmd}'")
                score_adjustment -= 3
            
            # Check if starts with valid prefix
            starts_valid = any(cmd_lower.startswith(prefix) for prefix in self.DIAGNOSTIC_PREFIXES)
            if not starts_valid:
                self.validation_warnings.append(f"Diagnostic command doesn't start with show/display/trace: '{cmd}'")
                score_adjustment -= 5
            
            # Check for description patterns (not actual commands)
            description_patterns = [
                r'^[A-Z][a-z]+\s+[a-z]+',  # "Check the configuration"
                r'\s+to\s+',  # "Use this to check"
                r'\s+for\s+checking',  # "Command for checking"
            ]
            for pattern in description_patterns:
                if re.search(pattern, cmd):
                    self.validation_warnings.append(f"Looks like description, not command: '{cmd}'")
                    score_adjustment -= 5
                    break
            
            # Check for HTML artifacts
            if '<' in cmd or '>' in cmd or '&' in cmd:
                self.validation_warnings.append(f"HTML artifacts in command: '{cmd[:50]}'")
                score_adjustment -= 10
        
        return score_adjustment
    
    def _validate_remediation_steps(self, steps: List[Dict[str, Any]]) -> int:
        """
        Validate remediation steps
        
        Returns:
            Score adjustment (negative for issues)
        """
        if not steps:
            self.validation_warnings.append("No remediation steps found")
            return -10
        
        score_adjustment = 0
        
        for i, step in enumerate(steps):
            # Check structure
            if not isinstance(step, dict):
                self.validation_errors.append(f"Step {i+1} is not a dictionary")
                score_adjustment -= 10
                continue
            
            if 'step' not in step:
                self.validation_errors.append(f"Step {i+1} missing 'step' field")
                score_adjustment -= 5
            
            if 'commands' not in step:
                self.validation_errors.append(f"Step {i+1} missing 'commands' field")
                score_adjustment -= 5
                continue
            
            commands = step['commands']
            
            # Check if commands is array
            if not isinstance(commands, list):
                self.validation_errors.append(f"Step {i+1} commands is not an array")
                score_adjustment -= 10
                continue
            
            # Allow empty commands for some steps (verification steps)
            if len(commands) == 0:
                self.validation_warnings.append(f"Step {i+1} has no commands: {step.get('step', '')}")
                score_adjustment -= 2
                continue
            
            # Validate each command
            for j, cmd in enumerate(commands):
                cmd_lower = cmd.lower().strip()
                
                if not cmd_lower:
                    self.validation_warnings.append(f"Empty command in step {i+1}")
                    score_adjustment -= 3
                    continue
                
                # Check if action command (not diagnostic)
                starts_valid = any(cmd_lower.startswith(prefix) for prefix in self.REMEDIATION_PREFIXES)
                if not starts_valid:
                    # Check if it's a show command (wrong type)
                    if any(cmd_lower.startswith(prefix) for prefix in self.DIAGNOSTIC_PREFIXES):
                        self.validation_warnings.append(f"Diagnostic command in remediation step {i+1}: '{cmd}'")
                        score_adjustment -= 3
                    else:
                        self.validation_warnings.append(f"Remediation command doesn't start with action verb: '{cmd}'")
                        score_adjustment -= 5
                
                # Check for description patterns
                if len(cmd) > 100 and not cmd_lower.startswith('configure'):
                    self.validation_warnings.append(f"Suspiciously long command in step {i+1}: '{cmd[:50]}...'")
                    score_adjustment -= 3
        
        return score_adjustment
    
    def _check_for_junk_data(self, article: Dict[str, Any]) -> int:
        """
        Check for HTML artifacts, malformed data, etc.
        
        Returns:
            Score adjustment (negative for issues)
        """
        score_adjustment = 0
        
        # Check all string fields for HTML artifacts
        def check_string(s: str, field_name: str):
            nonlocal score_adjustment
            if '<table' in s or '<tr' in s or '<td' in s:
                self.validation_errors.append(f"HTML table in {field_name}")
                score_adjustment -= 20
            if '&nbsp;' in s or '&gt;' in s or '&lt;' in s:
                self.validation_warnings.append(f"HTML entities in {field_name}")
                score_adjustment -= 5
        
        # Check title
        if 'title' in article:
            check_string(str(article['title']), 'title')
        
        # Check symptoms
        if 'symptoms' in article:
            for symptom in article['symptoms']:
                check_string(str(symptom), 'symptoms')
        
        # Check diagnostic commands
        if 'diagnostic_commands' in article:
            for cmd in article['diagnostic_commands']:
                if len(str(cmd)) > 500:
                    self.validation_errors.append(f"Extremely long diagnostic command (junk data?): {len(cmd)} chars")
                    score_adjustment -= 15
        
        return score_adjustment
    
    def get_quality_label(self, score: int) -> str:
        """Get quality label from score"""
        if score >= 90:
            return "EXCELLENT"
        elif score >= 80:
            return "GOOD"
        elif score >= 70:
            return "ACCEPTABLE"
        elif score >= 60:
            return "NEEDS_REVIEW"
        else:
            return "POOR"
    
    def print_validation_report(
        self, 
        is_valid: bool, 
        score: int, 
        errors: List[str], 
        warnings: List[str]
    ):
        """Print formatted validation report"""
        print(f"\n{'='*70}")
        print(f"VALIDATION REPORT")
        print(f"{'='*70}")
        print(f"Status: {'✅ VALID' if is_valid else '❌ INVALID'}")
        print(f"Quality Score: {score}/100 ({self.get_quality_label(score)})")
        
        if errors:
            print(f"\n🔴 ERRORS ({len(errors)}):")
            for error in errors:
                print(f"  - {error}")
        
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"  - {warning}")
        
        if not errors and not warnings:
            print(f"\n✨ Perfect! No issues found.")
        
        print(f"{'='*70}\n")


# Convenience function
def validate_kb_article(article: Dict[str, Any]) -> Tuple[bool, int, List[str], List[str]]:
    """
    Validate KB article
    
    Returns:
        (is_valid, quality_score, errors, warnings)
    """
    validator = ArticleValidator()
    return validator.validate_article(article)


if __name__ == "__main__":
    logger.info("Article Validator module loaded successfully")
    logger.info("Usage: validator = ArticleValidator(); is_valid, score, errors, warnings = validator.validate_article(article)")

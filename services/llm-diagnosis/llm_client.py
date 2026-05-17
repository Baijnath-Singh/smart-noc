"""
LLM Client - Handles communication with OpenAI/Anthropic APIs
Supports multiple providers with unified interface
"""

import json
import time
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import openai
from anthropic import Anthropic

import config


class LLMClient:
    """Unified LLM client supporting multiple providers"""
    
    def __init__(self):
        self.provider = config.LLM_PROVIDER
        self.model = config.LLM_MODEL
        self.max_tokens = config.LLM_MAX_TOKENS
        self.temperature = config.LLM_TEMPERATURE
        self.timeout = config.LLM_TIMEOUT
        
        # Initialize provider clients
        try:
            if self.provider == 'openai':
                logger.info("Initializing OpenAI client...")
                # Use modern OpenAI client (v1.0+)
                client_kwargs = {
                    'api_key': config.LLM_API_KEY,
                    'timeout': float(self.timeout)  # Set default timeout in client
                }
                if config.LLM_API_BASE:
                    client_kwargs['base_url'] = config.LLM_API_BASE
                logger.debug(f"OpenAI client kwargs: {list(client_kwargs.keys())}")
                logger.info(f"Setting timeout: {self.timeout}s")
                self.client = openai.OpenAI(**client_kwargs)
                logger.info("OpenAI client initialized successfully")
            elif self.provider == 'anthropic':
                logger.info("Initializing Anthropic client...")
                self.client = Anthropic(api_key=config.LLM_API_KEY)
                logger.info("Anthropic client initialized successfully")
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
        except Exception as e:
            logger.error(f"Failed to initialize {self.provider} client: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        logger.info(f"LLM Client initialized: {self.provider}/{self.model}")
    
    @retry(
        stop=stop_after_attempt(config.DIAGNOSIS_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def generate_diagnosis(
        self, 
        system_prompt: str, 
        user_message: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate diagnosis using LLM
        
        Returns:
            (diagnosis_dict, metadata_dict)
        """
        start_time = time.time()
        
        try:
            if self.provider == 'openai':
                response, metadata = self._call_openai(system_prompt, user_message)
            elif self.provider == 'anthropic':
                response, metadata = self._call_anthropic(system_prompt, user_message)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            duration_ms = int((time.time() - start_time) * 1000)
            metadata['duration_ms'] = duration_ms
            metadata['model'] = self.model
            metadata['provider'] = self.provider
            
            logger.info(f"LLM diagnosis completed in {duration_ms}ms, tokens: {metadata.get('total_tokens', 0)}")
            
            return response, metadata
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    def _call_openai(self, system_prompt: str, user_message: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Call OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
                timeout=self.timeout
            )
            
            # Extract response
            content = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {content[:500]}...")  # Log first 500 chars
            diagnosis = json.loads(content)
            logger.debug(f"Parsed diagnosis keys: {list(diagnosis.keys())}")  # Log keys
            
            # Extract metadata
            metadata = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
                'finish_reason': response.choices[0].finish_reason,
                'response_id': response.id,
            }
            
            # Calculate cost
            if config.ENABLE_COST_TRACKING:
                cost = config.get_estimated_cost(
                    self.model,
                    metadata['prompt_tokens'],
                    metadata['completion_tokens']
                )
                metadata['estimated_cost_usd'] = round(cost, 4)
            
            return diagnosis, metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.debug(f"Raw response: {content}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _call_anthropic(self, system_prompt: str, user_message: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Call Anthropic Claude API"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                timeout=self.timeout
            )
            
            # Extract response
            content = response.content[0].text
            diagnosis = json.loads(content)
            
            # Extract metadata
            metadata = {
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens,
                'finish_reason': response.stop_reason,
                'response_id': response.id,
            }
            
            # Calculate cost
            if config.ENABLE_COST_TRACKING:
                cost = config.get_estimated_cost(
                    self.model,
                    metadata['prompt_tokens'],
                    metadata['completion_tokens']
                )
                metadata['estimated_cost_usd'] = round(cost, 4)
            
            return diagnosis, metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Anthropic response as JSON: {e}")
            logger.debug(f"Raw response: {content}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def validate_diagnosis(self, diagnosis: Dict[str, Any]) -> bool:
        """Validate diagnosis response structure"""
        required_fields = ['root_cause', 'confidence', 'remediation_plan']
        
        for field in required_fields:
            if field not in diagnosis:
                logger.warning(f"Missing required field in diagnosis: {field}")
                return False
        
        # Validate confidence score
        confidence = diagnosis.get ('confidence', 0)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            logger.warning(f"Invalid confidence score: {confidence}")
            return False
        
        # Check minimum confidence threshold
        if confidence < config.DIAGNOSIS_MIN_CONFIDENCE:
            logger.warning(f"Confidence {confidence} below minimum {config.DIAGNOSIS_MIN_CONFIDENCE}")
            return False
        
        # Validate remediation plan structure
        remediation = diagnosis.get('remediation_plan', [])
        if not isinstance(remediation, list):
            logger.warning("Remediation plan is not a list")
            return False
        
        return True

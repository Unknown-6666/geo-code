"""
AIML API Client for Discord Bot

This module provides integration with aimlapi.com services
for AI capabilities. It supports text generation and other AI features.
"""

import os
import json
import logging
import requests
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger('discord')

class AIMLAPIClient:
    """Client for interacting with aimlapi.com services"""
    
    def __init__(self, api_key=None):
        """Initialize the AIML API client with API key"""
        self.api_key = api_key or os.environ.get('AIML_API_KEY')
        self.base_url = "https://api.aimlapi.com"  # Base URL for the API
        self.initialized = bool(self.api_key)
        
        if not self.initialized:
            logger.warning("AIML API is not configured (missing API key)")
        else:
            logger.info("AIML API client initialized successfully")
    
    async def generate_text(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> Optional[str]:
        """Generate text response from the AIML API"""
        if not self.initialized:
            logger.error("AIML API client not initialized (missing API key)")
            return None
            
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Adjust the endpoint and payload format based on the actual API documentation
            endpoint = f"{self.base_url}/v1/generate"
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"AIML API error: {response.status} - {error_text}")
                        return None
                        
                    response_json = await response.json()
                    # Extract the text from the response based on the API's response format
                    # Adjust this extraction logic based on the actual API response structure
                    if "text" in response_json:
                        return response_json["text"]
                    elif "choices" in response_json and len(response_json["choices"]) > 0:
                        return response_json["choices"][0].get("text", "")
                    else:
                        logger.error(f"Unexpected response format: {response_json}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error generating text with AIML API: {str(e)}")
            return None
            
    async def analyze_content(self, content: str) -> Dict[str, Any]:
        """Analyze content for toxicity, sentiment, etc."""
        if not self.initialized:
            logger.error("AIML API client not initialized (missing API key)")
            return {"error": "API not initialized"}
            
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Adjust the endpoint and payload format based on the actual API documentation
            endpoint = f"{self.base_url}/v1/analyze"
            payload = {
                "content": content
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"AIML API error: {response.status} - {error_text}")
                        return {"error": f"API error: {response.status}"}
                        
                    response_json = await response.json()
                    return response_json
                    
        except Exception as e:
            logger.error(f"Error analyzing content with AIML API: {str(e)}")
            return {"error": str(e)}
            
    async def summarize(self, content: str, max_length: int = 200) -> Optional[str]:
        """Summarize content using the AIML API"""
        if not self.initialized:
            logger.error("AIML API client not initialized (missing API key)")
            return None
            
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Adjust the endpoint and payload format based on the actual API documentation
            endpoint = f"{self.base_url}/v1/summarize"
            payload = {
                "content": content,
                "max_length": max_length
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"AIML API error: {response.status} - {error_text}")
                        return None
                        
                    response_json = await response.json()
                    # Extract the summary from the response based on the API's response format
                    if "summary" in response_json:
                        return response_json["summary"]
                    else:
                        logger.error(f"Unexpected response format: {response_json}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error summarizing content with AIML API: {str(e)}")
            return None
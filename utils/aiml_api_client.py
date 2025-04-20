"""
AIML API Client for Discord Bot

This module provides integration with aimlapi.com services
for AI capabilities. It supports text generation and other AI features.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional
import asyncio

# We'll use requests for async operations with async/await syntax
# instead of aiohttp since it might not be available
logger = logging.getLogger('discord')

class AIMLAPIClient:
    """Client for interacting with aimlapi.com services"""
    
    def __init__(self, api_key=None):
        """Initialize the AIML API client with API key"""
        self.api_key = api_key or os.environ.get('AIML_API_KEY')
        self.base_url = "https://api.aimlapi.com/v1"  # Base URL for the API
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
            
            # AIML API endpoint for text generation
            endpoint = f"{self.base_url}/chat/completions"
            # Format payload for the AIML API's completion endpoint
            payload = {
                "model": "gpt-3.5-turbo",  # Using a standard model supported by AIML API
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Use requests in a non-blocking way with asyncio.to_thread
            # This runs the HTTP request in a background thread
            def make_request():
                response = requests.post(endpoint, headers=headers, json=payload)
                return response.status_code, response.text
                
            status_code, response_text = await asyncio.get_event_loop().run_in_executor(None, make_request)
            
            if status_code != 200:
                logger.error(f"AIML API error: {status_code} - {response_text}")
                return None
                
            # Parse the JSON response
            try:
                response_json = json.loads(response_text)
                
                # Extract the text from the response based on the AIML API's response format
                # Which follows the OpenAI API format standards
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    choice = response_json["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        return choice["message"]["content"]
                    elif "text" in choice:
                        return choice["text"]
                
                logger.error(f"Unexpected AIML API response format: {response_json}")
                return None
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response: {response_text}")
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
            
            # Use the general chat completions endpoint with content analysis prompt
            endpoint = f"{self.base_url}/chat/completions"
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You analyze content for tone, sentiment, toxicity, and other characteristics. Provide your analysis in JSON format."},
                    {"role": "user", "content": f"Analyze the following content and provide a structured assessment:\n\n{content}"}
                ],
                "max_tokens": 500,
                "temperature": 0.3  # Lower temperature for more deterministic analysis
            }
            
            # Use requests in a non-blocking way with asyncio executor
            def make_request():
                response = requests.post(endpoint, headers=headers, json=payload)
                return response.status_code, response.text
                
            status_code, response_text = await asyncio.get_event_loop().run_in_executor(None, make_request)
            
            if status_code != 200:
                logger.error(f"AIML API error: {status_code} - {response_text}")
                return {"error": f"API error: {status_code}"}
                
            # Parse the JSON response
            try:
                response_json = json.loads(response_text)
                # Extract the analysis from the chat completion response
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    choice = response_json["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        analysis_text = choice["message"]["content"]
                        
                        # Try to parse the analysis text as JSON if it's in JSON format
                        try:
                            # Find JSON content (often models will include explanatory text before/after JSON)
                            import re
                            json_match = re.search(r'({[\s\S]*})', analysis_text)
                            if json_match:
                                analysis_json = json.loads(json_match.group(1))
                                return analysis_json
                            else:
                                # Return as text object if not valid JSON
                                return {
                                    "analysis": analysis_text,
                                    "format": "text"
                                }
                        except json.JSONDecodeError:
                            # If not valid JSON, return the text as is
                            return {
                                "analysis": analysis_text,
                                "format": "text"
                            }
                
                logger.error(f"Unexpected AIML API response format for analysis: {response_json}")
                return {"error": "Unexpected response format"}
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response: {response_text}")
                return {"error": "Invalid JSON response"}
                
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
            
            # Use the general chat completions endpoint with a summarization prompt
            endpoint = f"{self.base_url}/chat/completions"
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI that summarizes content accurately and concisely."},
                    {"role": "user", "content": f"Please summarize the following text in about {max_length} words or less:\n\n{content}"}
                ],
                "max_tokens": max_length * 4,  # Approximate tokens needed for word count
                "temperature": 0.5  # Lower temperature for more focused summaries
            }
            
            # Use requests in a non-blocking way with asyncio executor
            def make_request():
                response = requests.post(endpoint, headers=headers, json=payload)
                return response.status_code, response.text
                
            status_code, response_text = await asyncio.get_event_loop().run_in_executor(None, make_request)
            
            if status_code != 200:
                logger.error(f"AIML API error: {status_code} - {response_text}")
                return None
                
            # Parse the JSON response
            try:
                response_json = json.loads(response_text)
                # Extract the summary using the same logic as generate_text 
                # since we're using the same endpoint
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    choice = response_json["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        return choice["message"]["content"]
                    elif "text" in choice:
                        return choice["text"]
                
                logger.error(f"Unexpected AIML API response format for summarization: {response_json}")
                return None
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response: {response_text}")
                return None
                
        except Exception as e:
            logger.error(f"Error summarizing content with AIML API: {str(e)}")
            return None
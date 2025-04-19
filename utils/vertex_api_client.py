"""
Simplified Vertex AI REST API Client

This module provides a simplified client for accessing Vertex AI
using direct REST API calls instead of relying on the google-cloud-aiplatform package.
This provides a fallback when the package cannot be installed due to compatibility issues.
"""

import os
import json
import logging
import requests
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger('discord')

class VertexRESTClient:
    """A simplified client for Vertex AI using REST API calls"""
    
    def __init__(self):
        """Initialize the Vertex REST API client"""
        self.initialized = False
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.location = os.environ.get('VERTEX_LOCATION', 'us-central1')
        self.model_id = "text-bison@002"  # Default model for text generation
        self.chat_model_id = "chat-bison@002"  # Default model for chat
        
        # Attempt to create auth token
        self.auth_token = None
        self.token_expiry = 0
        
        # Initialize client
        if self.project_id:
            self.setup_credentials()
        else:
            logger.error("GOOGLE_CLOUD_PROJECT environment variable not set")
            
    def setup_credentials(self):
        """Set up the credentials and authentication"""
        try:
            # We'll need the GOOGLE_APPLICATION_CREDENTIALS env var to be set
            creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_file:
                creds_json = os.environ.get('GOOGLE_CREDENTIALS')
                if creds_json:
                    # Try to find actual JSON content if mixed with other text
                    if '{' in creds_json and '}' in creds_json:
                        start = creds_json.find('{')
                        end = creds_json.rfind('}') + 1
                        if start >= 0 and end > start:
                            try:
                                creds_json = creds_json[start:end]
                                # Write to file
                                creds_file = '/tmp/vertex_rest_credentials.json'
                                with open(creds_file, 'w') as f:
                                    f.write(creds_json)
                                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_file
                                logger.info(f"Credentials written to {creds_file}")
                            except Exception as e:
                                logger.error(f"Error writing credentials file: {str(e)}")
                                return
                else:
                    logger.error("No credentials environment variables found")
                    return
            
            # Try to get an auth token
            if self._get_auth_token():
                self.initialized = True
                logger.info("Successfully initialized Vertex REST API client")
            else:
                logger.error("Failed to get auth token for Vertex AI")
        except Exception as e:
            logger.error(f"Error setting up Vertex API client: {str(e)}")
            
    def _get_auth_token(self):
        """Get or refresh the authentication token"""
        try:
            # Check if token is still valid
            if self.auth_token and time.time() < self.token_expiry - 60:  # Buffer of 1 minute
                return True
                
            # Read credentials from file
            creds_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if not creds_file or not os.path.exists(creds_file):
                logger.error("Credentials file not found")
                return False
                
            with open(creds_file, 'r') as f:
                creds = json.load(f)
                
            client_email = creds.get('client_email')
            private_key = creds.get('private_key')
            
            if not client_email or not private_key:
                logger.error("Missing client_email or private_key in credentials")
                return False
                
            # Create JWT assertions for OAuth token request
            import jwt  # Import locally to not fail if jwt isn't installed
            from datetime import datetime, timedelta
            
            now = datetime.utcnow()
            expiry = now + timedelta(hours=1)
            
            claims = {
                'iss': client_email,
                'scope': 'https://www.googleapis.com/auth/cloud-platform',
                'aud': 'https://oauth2.googleapis.com/token',
                'exp': int(expiry.timestamp()),
                'iat': int(now.timestamp())
            }
            
            # Create signed JWT
            signed_jwt = jwt.encode(
                claims,
                private_key,
                algorithm='RS256'
            )
            
            # Exchange JWT for access token
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                    'assertion': signed_jwt
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Error getting auth token: {response.text}")
                return False
                
            data = response.json()
            self.auth_token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            self.token_expiry = time.time() + expires_in
            
            logger.info(f"Successfully obtained auth token (expires in {expires_in} seconds)")
            return True
        except ImportError:
            logger.error("PyJWT package not installed - required for Vertex AI REST authentication")
            return False
        except Exception as e:
            logger.error(f"Error getting auth token: {str(e)}")
            return False
            
    async def generate_text(self, prompt: str, max_output_tokens: int = 1024, temperature: float = 0.7):
        """Generate text using Vertex AI text model via REST API"""
        if not self.initialized or not self.auth_token:
            logger.error("Vertex REST client not initialized")
            return None
            
        # Refresh token if needed
        if not self._get_auth_token():
            logger.error("Failed to refresh auth token")
            return None
            
        try:
            url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_id}:predict"
            
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "instances": [
                    {"prompt": prompt}
                ],
                "parameters": {
                    "temperature": temperature,
                    "maxOutputTokens": max_output_tokens,
                    "topK": 40,
                    "topP": 0.95
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"Error generating text: {response.status_code} - {response.text}")
                return None
                
            data = response.json()
            if 'predictions' in data and data['predictions']:
                return data['predictions'][0].get('content', '')
                
            logger.error(f"Unexpected response format: {json.dumps(data)[:200]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error generating text with Vertex REST API: {str(e)}")
            return None
            
    async def generate_chat_response(self, message: str, history: Optional[List[Dict]] = None, 
                                   system_prompt: Optional[str] = None,
                                   temperature: float = 0.7, max_output_tokens: int = 1024):
        """Generate chat response using Vertex AI chat model via REST API"""
        if not self.initialized or not self.auth_token:
            logger.error("Vertex REST client not initialized")
            return None
            
        # Refresh token if needed
        if not self._get_auth_token():
            logger.error("Failed to refresh auth token")
            return None
            
        try:
            url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.chat_model_id}:predict"
            
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Format system prompt and conversation context
            context = system_prompt if system_prompt else ""
            
            # Format messages
            messages = []
            if history and isinstance(history, list):
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    
                    # Bison API uses "author" instead of "role"
                    if role == "user":
                        messages.append({"author": "user", "content": content})
                    elif role == "assistant":
                        messages.append({"author": "bot", "content": content})
            
            # Add the current message
            messages.append({"author": "user", "content": message})
            
            payload = {
                "instances": [
                    {
                        "context": context,
                        "messages": messages
                    }
                ],
                "parameters": {
                    "temperature": temperature,
                    "maxOutputTokens": max_output_tokens,
                    "topK": 40,
                    "topP": 0.95
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"Error generating chat response: {response.status_code} - {response.text}")
                return None
                
            data = response.json()
            if 'predictions' in data and data['predictions']:
                prediction = data['predictions'][0]
                if isinstance(prediction, dict) and 'candidates' in prediction:
                    return prediction['candidates'][0].get('content', '')
                else:
                    return prediction.get('content', '')
                
            logger.error(f"Unexpected response format: {json.dumps(data)[:200]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error generating chat response with Vertex REST API: {str(e)}")
            return None
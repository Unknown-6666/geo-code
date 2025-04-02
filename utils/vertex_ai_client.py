"""
Vertex AI Client Module for Discord Bot

This module provides a client for interacting with Google's Vertex AI API.
It handles authentication, conversation formatting, and API requests.
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Optional

# Import Vertex AI dependencies - these will only be used if the client is initialized
# Set a flag to track if we can import the library
HAS_VERTEX_AI = False
aiplatform = None  # Initialize globally to avoid unbound variable errors

try:
    # Try to import the module
    from google.cloud import aiplatform as vertex_ai
    # If successful, set the flag and assign to global
    HAS_VERTEX_AI = True
    aiplatform = vertex_ai
except ImportError:
    # If import fails, log it (will be done in methods when they check HAS_VERTEX_AI)
    pass
    
logger = logging.getLogger('discord')

class VertexAIClient:
    """Client for interacting with Google's Vertex AI services"""
    
    def __init__(self):
        """Initialize the Vertex AI client"""
        self.initialized = False
        
        # Early return if the library isn't available
        if not HAS_VERTEX_AI:
            logger.warning("Google Cloud Vertex AI library not available. Vertex AI features disabled.")
            return
            
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.location = os.environ.get('VERTEX_LOCATION', 'us-central1')
        self.credentials_path = None
        
        # Try to initialize with credentials
        self._setup_credentials()
        
    def _setup_credentials(self):
        """Set up the credentials from environment variables"""
        try:
            # Check if credentials file path is provided
            if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                self.credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
                logger.info(f"Using Google credentials from: {self.credentials_path}")
                self.initialized = True
                return
            
            # Check if credentials JSON is provided as environment variable
            if os.environ.get('GOOGLE_CREDENTIALS'):
                # Write the credentials to a temporary file
                creds_content = os.environ.get('GOOGLE_CREDENTIALS')
                creds_path = '/tmp/vertex_credentials.json'
                
                if creds_content:
                    with open(creds_path, 'w') as f:
                        f.write(creds_content)
                else:
                    logger.error("GOOGLE_CREDENTIALS environment variable is empty or None")
                    self.initialized = False
                    return
                
                # Set the credentials path
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
                self.credentials_path = creds_path
                logger.info(f"Created temporary credentials file at: {creds_path}")
                self.initialized = True
                return
            
            logger.warning("No Google Cloud credentials found. Vertex AI will not be available.")
            self.initialized = False
        
        except Exception as e:
            logger.error(f"Error setting up Google Cloud credentials: {str(e)}")
            self.initialized = False
    
    def _format_conversation_history(self, history: List[Dict[str, str]]) -> List[Dict]:
        """
        Format conversation history for Vertex AI
        
        Args:
            history: List of conversation messages in {"role": role, "content": content} format
            
        Returns:
            Formatted history for Vertex AI
        """
        # This method can be expanded as needed for more complex formatting
        return history
    
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, 
                           temperature: float = 0.7, max_output_tokens: int = 1024):
        """
        Generate text using Vertex AI text models
        
        Args:
            prompt: The user's input prompt
            system_prompt: Optional system instructions
            temperature: Controls randomness (0.0 to 1.0)
            max_output_tokens: Maximum length of generated text
            
        Returns:
            Generated text response or None if error
        """
        if not self.initialized:
            logger.error("Vertex AI client is not initialized. Cannot generate text.")
            return None
            
        if not HAS_VERTEX_AI:
            logger.error("Vertex AI library is not installed. Cannot generate text.")
            return None

        try:
            
            # Format the prompt with system instructions if provided
            formatted_prompt = prompt
            if system_prompt:
                formatted_prompt = f"[System: {system_prompt}]\n\nUser: {prompt}"
            
            # Initialize the Vertex AI SDK
            aiplatform.init(project=self.project_id, location=self.location)
            
            # Select the text model
            # Note: model names may change, check the Vertex AI documentation for the latest models
            model_name = "text-bison@002"  # General purpose text model
            
            # Get the text generation model
            model = aiplatform.TextGenerationModel.from_pretrained(model_name)
            
            # Prepare parameters
            parameters = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "top_p": 0.95,
                "top_k": 40,
            }
            
            # Generate response - run in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.predict(
                    formatted_prompt,
                    **parameters
                )
            )
            
            logger.info(f"Vertex AI text response generated successfully")
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating text with Vertex AI: {str(e)}")
            return None
    
    async def generate_chat_response(self, message: str, history: Optional[List[Dict]] = None, 
                                   system_prompt: Optional[str] = None,
                                   temperature: float = 0.7, max_output_tokens: int = 1024):
        """
        Generate chat response using Vertex AI chat models
        
        Args:
            message: The user's message
            history: Optional conversation history
            system_prompt: Optional system instructions
            temperature: Controls randomness (0.0 to 1.0)
            max_output_tokens: Maximum length of generated text
            
        Returns:
            Generated chat response or None if error
        """
        if not self.initialized:
            logger.error("Vertex AI client is not initialized. Cannot generate chat response.")
            return None
            
        if not HAS_VERTEX_AI:
            logger.error("Vertex AI library is not installed. Cannot generate chat response.")
            return None
        
        try:
            
            # Initialize the Vertex AI SDK
            aiplatform.init(project=self.project_id, location=self.location)
            
            # Select a chat model
            # Note: model names may change, check the Vertex AI documentation for the latest models
            model_name = "chat-bison@002"  # Chat-optimized model
            
            # Get the chat model
            model = aiplatform.ChatModel.from_pretrained(model_name)
            
            # Prepare parameters
            parameters = {
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "top_p": 0.95,
                "top_k": 40,
            }
            
            # Run in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Define the chat processing function
            def process_chat():
                # Start a chat with context if provided
                chat = model.start_chat(
                    context=system_prompt if system_prompt else ""
                )
                
                # Add previous messages to history if provided
                if history and isinstance(history, list):
                    for msg in history:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        
                        if role == "user":
                            # We need to send these but don't care about responses for history
                            chat.send_message(content)
                        # Note: The chat model will automatically include assistant responses in context
                
                # Send the current message and get response
                response = chat.send_message(
                    message,
                    **parameters
                )
                return response.text
            
            # Execute the chat processing in a thread
            response_text = await loop.run_in_executor(None, process_chat)
            
            logger.info(f"Vertex AI chat response generated successfully")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating chat response with Vertex AI: {str(e)}")
            return None
            
    async def list_available_models(self):
        """
        List available Vertex AI models
        
        Returns:
            List of available models or None if error
        """
        if not self.initialized:
            logger.error("Vertex AI client is not initialized. Cannot list models.")
            return None
            
        if not HAS_VERTEX_AI:
            logger.error("Vertex AI library is not installed. Cannot list models.")
            return None
            
        try:
            
            # Initialize the Vertex AI SDK
            aiplatform.init(project=self.project_id, location=self.location)
            
            # Run in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            models = await loop.run_in_executor(
                None,
                lambda: aiplatform.Model.list()
            )
            
            # Format the results
            model_list = [
                {
                    "name": model.display_name,
                    "id": model.name,
                    "create_time": model.create_time,
                }
                for model in models
            ]
            
            return model_list
            
        except Exception as e:
            logger.error(f"Error listing Vertex AI models: {str(e)}")
            return None
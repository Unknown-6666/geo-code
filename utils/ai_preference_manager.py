import os
import json
import logging
import random

logger = logging.getLogger('discord')

# AI Preferences
AI_PREFERENCES_FILE = "data/ai_preferences.json"

class AIPreferences:
    def __init__(self):
        self.preferences = self.load_preferences()
        self.current_personality = self.preferences.get("personality", "default")

    def load_preferences(self):
        """Load AI preferences from JSON file"""
        try:
            if os.path.exists(AI_PREFERENCES_FILE):
                with open(AI_PREFERENCES_FILE, 'r') as f:
                    preferences = json.load(f)
                logger.info(f"Loaded AI preferences with {len(preferences.get('keyword_triggers', {}))} custom response patterns")
                return preferences
            else:
                logger.warning(f"AI preferences file not found at {AI_PREFERENCES_FILE}. Using defaults.")
                return {
                    "system_prompts": {"default": "You are a friendly and helpful chat bot. Keep responses concise and engaging."},
                    "keyword_triggers": {},
                    "personality": "default",
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
        except Exception as e:
            logger.error(f"Error loading AI preferences: {str(e)}")
            return {
                "system_prompts": {"default": "You are a friendly and helpful chat bot. Keep responses concise and engaging."},
                "keyword_triggers": {},
                "personality": "default",
                "temperature": 0.7,
                "max_tokens": 1000
            }

    def save_preferences(self):
        """Save current preferences to JSON file"""
        try:
            os.makedirs(os.path.dirname(AI_PREFERENCES_FILE), exist_ok=True)
            with open(AI_PREFERENCES_FILE, 'w') as f:
                json.dump(self.preferences, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving AI preferences: {str(e)}")
            return False

    def get_system_prompt(self, personality=None):
        """Get the system prompt for a specific personality"""
        if not personality:
            personality = self.current_personality

        system_prompts = self.preferences.get("system_prompts", {})
        if personality in system_prompts:
            return system_prompts[personality]
        return system_prompts.get("default", "You are a helpful assistant.")

    def set_personality(self, personality):
        """Set the current personality for the AI"""
        system_prompts = self.preferences.get("system_prompts", {})
        if personality in system_prompts:
            self.current_personality = personality
            self.preferences["personality"] = personality
            self.save_preferences()
            return True
        return False

    def get_temperature(self):
        """Get the temperature setting for the AI"""
        return self.preferences.get("temperature", 0.7)

    def get_max_tokens(self):
        """Get the max tokens setting for the AI"""
        return self.preferences.get("max_tokens", 1000)

    def check_keyword_triggers(self, message):
        """Check if a message contains any keyword triggers and return the response if found"""
        message_lower = message.lower()
        keyword_triggers = self.preferences.get("keyword_triggers", {})
        
        for keyword, response in keyword_triggers.items():
            if keyword.lower() in message_lower:
                return response
        return None
        
    def get_custom_response(self, message):
        """Alternative name for check_keyword_triggers method for backward compatibility"""
        return self.check_keyword_triggers(message)
        
    def reload_preferences(self):
        """Reload AI preferences from the JSON file"""
        self.preferences = self.load_preferences()
        self.current_personality = self.preferences.get("personality", "default")
        return self.preferences

    def get_available_personalities(self):
        """Get a list of all available personality options"""
        return list(self.preferences.get("system_prompts", {}).keys())
        
    def add_custom_response(self, category, patterns, responses):
        """Add a custom response pattern and response to a category"""
        # Initialize structured custom responses if they don't exist
        if not "custom_responses" in self.preferences:
            self.preferences["custom_responses"] = {}
            
        # Initialize category if it doesn't exist
        if category not in self.preferences["custom_responses"]:
            self.preferences["custom_responses"][category] = {
                "patterns": [],
                "responses": []
            }
            
        # Add patterns and responses
        for pattern in patterns:
            if pattern not in self.preferences["custom_responses"][category]["patterns"]:
                self.preferences["custom_responses"][category]["patterns"].append(pattern)
                
        for response in responses:
            if response not in self.preferences["custom_responses"][category]["responses"]:
                self.preferences["custom_responses"][category]["responses"].append(response)
        
        # Also add as keyword triggers for backward compatibility
        for pattern in patterns:
            # Use the first response for the keyword trigger
            if responses and len(responses) > 0:
                self.preferences["keyword_triggers"][pattern] = responses[0]
        
        return self.save_preferences()
        
    def remove_custom_response(self, category):
        """Remove a custom response category"""
        if category in self.preferences.get("custom_responses", {}):
            # Remove from keyword triggers for backward compatibility
            for pattern in self.preferences["custom_responses"][category].get("patterns", []):
                if pattern in self.preferences.get("keyword_triggers", {}):
                    del self.preferences["keyword_triggers"][pattern]
            
            # Remove the category
            del self.preferences["custom_responses"][category]
            return self.save_preferences()
        return False

    def add_keyword_trigger(self, keyword, response):
        """Add a new keyword trigger"""
        if not "keyword_triggers" in self.preferences:
            self.preferences["keyword_triggers"] = {}
        
        self.preferences["keyword_triggers"][keyword] = response
        return self.save_preferences()

    def remove_keyword_trigger(self, keyword):
        """Remove a keyword trigger"""
        if keyword in self.preferences.get("keyword_triggers", {}):
            del self.preferences["keyword_triggers"][keyword]
            return self.save_preferences()
        return False

    def add_personality(self, name, prompt):
        """Add a new personality with system prompt"""
        if not "system_prompts" in self.preferences:
            self.preferences["system_prompts"] = {}
        
        self.preferences["system_prompts"][name] = prompt
        return self.save_preferences()

    def remove_personality(self, name):
        """Remove a personality"""
        if name in self.preferences.get("system_prompts", {}) and name != "default":
            del self.preferences["system_prompts"][name]
            if self.current_personality == name:
                self.current_personality = "default"
                self.preferences["personality"] = "default"
            return self.save_preferences()
        return False

# Create a global instance for easy import
ai_preferences = AIPreferences()
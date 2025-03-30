"""
Simple implementation of AI preferences manager
This is a basic version without all the customized features
"""

class AIPreferences:
    def __init__(self):
        self.preferences = {}
        
    def check_keyword_triggers(self, message):
        """Check for keyword triggers (stub method)"""
        return None
        
    def get_custom_response(self, message):
        """Get custom response for message (stub method)"""
        return None
        
    def get_system_prompt(self):
        """Get system prompt (returns a default)"""
        return "You are a friendly and helpful chat bot. Keep responses concise and engaging."
        
    def get_temperature(self):
        """Get temperature setting (default)"""
        return 0.7
        
    def get_max_tokens(self):
        """Get max tokens (default)"""
        return 1000
        
    def reload_preferences(self):
        """Reload preferences (stub method)"""
        return {}
        
    def save_preferences(self):
        """Save preferences (stub method)"""
        return True
        
    def add_custom_response(self, category, patterns, responses):
        """Add custom response (stub method)"""
        return True
        
    def remove_custom_response(self, category):
        """Remove custom response (stub method)"""
        return True

# Create a global instance
ai_preferences = AIPreferences()
from typing import Optional, Dict
import json
import logging
from pathlib import Path
from .response_gen import ResponseGenerator
from .query_handler import QueryHandler

logger = logging.getLogger(__name__)

class InteractionFlow:
    def __init__(self, state_file: str = "bot_state.json"):
        self.state_file = Path(state_file)
        self.response_gen = ResponseGenerator()
        self.query_handler = QueryHandler()
        self.state = self._load_state()
        
    def _load_state(self) -> Dict:
        """Load bot state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            return {'last_interaction': None, 'conversation_context': {}}
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return {'last_interaction': None, 'conversation_context': {}}
    
    def _save_state(self):
        """Save bot state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def _update_context(self, user_id: str, query_text: str, response: str):
        """Update conversation context for a user."""
        if user_id not in self.state['conversation_context']:
            self.state['conversation_context'][user_id] = []
        
        self.state['conversation_context'][user_id].append({
            'query': query_text,
            'response': response,
            'timestamp': str(datetime.datetime.now())
        })
        
        # Keep only last 5 interactions
        self.state['conversation_context'][user_id] = \
            self.state['conversation_context'][user_id][-5:]
    
    def handle_interaction(self, tweet_text: str, author_id: str, 
                         author_username: str) -> str:
        """
        Handle an incoming interaction and generate appropriate response.
        """
        try:
            # Generate response
            response = self.response_gen.generate_response(tweet_text, author_username)
            
            # Update conversation context
            self._update_context(author_id, tweet_text, response)
            
            # Save updated state
            self._save_state()
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling interaction: {e}")
            return f"@{author_username} I apologize, but I encountered an error processing your request."

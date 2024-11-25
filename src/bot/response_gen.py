class ResponseGenerator:
    def __init__(self):
        self.default_response = "Thank you for mentioning me! I'm here to help identify Sanskrit loanwords."
    
    def generate_response(self, tweet_text, author_username):
        """
        Generate a response to a tweet. Currently returns a simple response,
        will be enhanced later with actual loanword detection.
        """
        return f"@{author_username} {self.default_response}"

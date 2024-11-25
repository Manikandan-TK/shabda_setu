"""Configuration settings for the Twitter bot."""

# API Endpoints
API_BASE_URL = "https://api.twitter.com/2"
MENTIONS_ENDPOINT = "/users/{user_id}/mentions"
TWEETS_ENDPOINT = "/tweets"
USER_LOOKUP_ENDPOINT = "/users/me"  # Endpoint to get authenticated user's information

# API Rate Limits
MAX_MONTHLY_READS = 100
MAX_MONTHLY_WRITES = 500
DEFAULT_CHECK_INTERVAL = 300  # 5 minutes
MIN_CHECK_INTERVAL = 60  # 1 minute
MAX_CHECK_INTERVAL = 3600  # 1 hour

# Request Parameters
MAX_RESULTS_PER_REQUEST = 5
TWEET_FIELDS = [
    'author_id',
    'created_at',
    'conversation_id',
    'in_reply_to_user_id',
    'referenced_tweets'
]
USER_FIELDS = ['username', 'name']
EXPANSIONS = ['author_id', 'referenced_tweets.id']

# Response Settings
MAX_RETRIES = 3
BACKOFF_FACTOR = 2
JITTER_RANGE = (-30, 30)  # seconds

# Error Messages
ERROR_MESSAGES = {
    'rate_limit': "Rate limit exceeded. Waiting for reset.",
    'auth_error': "Authentication failed. Please check your credentials.",
    'api_error': "Twitter API error: {error_message}",
    'network_error': "Network error occurred: {error_message}",
}

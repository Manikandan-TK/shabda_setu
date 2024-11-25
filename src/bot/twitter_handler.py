import os
import time
import requests
from dotenv import load_dotenv
import json
from datetime import datetime, timezone
import random
from requests_oauthlib import OAuth1
import logging
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from config import bot_config as cfg

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)

# Disable debug logging from requests and urllib3
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('requests_oauthlib').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('oauthlib').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# State file path
STATE_FILE = os.path.join(os.path.dirname(__file__), 'bot_state.json')

class TwitterBot:
    def __init__(self):
        # Initialize Twitter API credentials
        load_dotenv()
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.bot_username = os.getenv('BOT_USERNAME')
        self.owner_id = os.getenv('OWNER_TWITTER_ID')
        
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            raise ValueError("Missing required environment variables")
        
        # Set up OAuth 1.0a
        self.auth = OAuth1(
            self.api_key,
            self.api_secret,
            self.access_token,
            self.access_token_secret
        )
        
        # API usage tracking
        self.monthly_reads = 0
        self.monthly_writes = 0
        self.max_monthly_reads = cfg.MAX_MONTHLY_READS
        self.max_monthly_writes = cfg.MAX_MONTHLY_WRITES
        self.last_reset_time = datetime.now(timezone.utc)
        
        # Load state
        self.state = self._load_state()
        
        logger.info("=== Bot Initialization ===")
        logger.info(f"Initializing bot as {self.bot_username}")
        
        # Get the bot's user ID
        self.user_id = self._get_user_id()
        if not self.user_id:
            raise Exception("Failed to get bot's user ID")
            
        logger.info(f"(+) Successfully got bot's user ID: {self.user_id}")
        logger.info("(+) Successfully set up OAuth authentication")
        logger.info(f"(+) Free API limits: {self.max_monthly_reads} reads, {self.max_monthly_writes} writes per month")
        logger.info("=========================")

    def _get_user_id(self):
        """Get the bot's user ID"""
        logger.info("Getting bot's user ID...")
        url = f"{cfg.API_BASE_URL}{cfg.USER_LOOKUP_ENDPOINT}"
        
        try:
            response = requests.get(url, auth=self.auth)
            if response.status_code == 200:
                return response.json()['data']['id']
            else:
                logger.error(f"Failed to get user ID: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return None

    def _handle_rate_limit(self, response):
        """Handle rate limiting with exponential backoff"""
        if response.status_code == 429:
            remaining = int(response.headers.get('x-rate-limit-remaining', 0))
            limit = int(response.headers.get('x-rate-limit-limit', 1))
            reset_time = int(response.headers.get('x-rate-limit-reset', 0))
            
            if reset_time:
                current_time = int(time.time())
                wait_time = reset_time - current_time + 5  # Add 5 seconds buffer
                reset_datetime = datetime.fromtimestamp(reset_time)
                logger.warning(f"Rate limited. Limit: {limit}, Remaining: {remaining}")
                logger.warning(f"Rate limit resets at: {reset_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                wait_time = cfg.DEFAULT_CHECK_INTERVAL * (cfg.BACKOFF_FACTOR ** random.randint(0, 2))
                logger.warning(f"No reset time found. Using exponential backoff: {wait_time} seconds")
            
            logger.info(f"Sleeping for {wait_time} seconds...")
            time.sleep(wait_time)
            return True
        return False

    def _check_api_limits(self, is_write=False):
        """Check if we're within API limits"""
        current_time = datetime.now(timezone.utc)
        
        # Reset counters if it's a new month
        if current_time.month != self.last_reset_time.month:
            logger.info("\n=== Monthly Reset ===")
            logger.info("New month detected - resetting API counters")
            self.monthly_reads = 0
            self.monthly_writes = 0
            self.last_reset_time = current_time
            logger.info("=====================\n")

        if is_write:
            if self.monthly_writes >= self.max_monthly_writes:
                logger.error("Monthly write limit reached!")
                return False
            self.monthly_writes += 1
            logger.info(f"[W] Write counter: {self.monthly_writes}/{self.max_monthly_writes}")
        else:
            if self.monthly_reads >= self.max_monthly_reads:
                logger.error("Monthly read limit reached!")
                return False
            self.monthly_reads += 1
            logger.info(f"[R] Read counter: {self.monthly_reads}/{self.max_monthly_reads}")
        return True

    def _make_request(self, url, method='GET', params=None, json_data=None):
        """Make an authenticated request to Twitter API with rate limit handling"""
        if not self._check_api_limits(is_write=(method == 'POST')):
            return None

        headers = {'Content-Type': 'application/json'}
        
        for retry in range(cfg.MAX_RETRIES):
            try:
                logger.info(f"\n>>> Making {method} request to {url} (attempt {retry + 1}/{cfg.MAX_RETRIES})")
                if method == 'GET':
                    response = requests.get(url, auth=self.auth, headers=headers, params=params)
                elif method == 'POST':
                    response = requests.post(url, auth=self.auth, headers=headers, json=json_data)
                
                if self._handle_rate_limit(response):
                    continue
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    if retry < cfg.MAX_RETRIES - 1:
                        wait_time = cfg.DEFAULT_CHECK_INTERVAL * (cfg.BACKOFF_FACTOR ** retry)
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if retry < cfg.MAX_RETRIES - 1:
                    wait_time = cfg.DEFAULT_CHECK_INTERVAL * (cfg.BACKOFF_FACTOR ** retry)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                continue
        
        return None

    def _load_state(self):
        """Load bot state from file"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state: {e}")
        return {"last_mention_id": None, "last_check_time": None}
    
    def _save_state(self):
        """Save bot state to file"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def check_mentions(self, since_id=None):
        """Check for mentions and return new mentions"""
        logger.info("\n=== Checking Mentions ===")
        logger.info(f"Last mention ID: {since_id}")
        
        url = f"{cfg.API_BASE_URL}{cfg.MENTIONS_ENDPOINT.format(user_id=self.user_id)}"
        params = {
            'tweet.fields': ','.join(cfg.TWEET_FIELDS),
            'expansions': ','.join(cfg.EXPANSIONS),
            'user.fields': ','.join(cfg.USER_FIELDS),
            'max_results': cfg.MAX_RESULTS_PER_REQUEST
        }
        
        if since_id:
            params['since_id'] = since_id
            
        logger.info(f"Making mentions request to URL: {url}")
        logger.info(f"Request params: {params}")
            
        try:
            response = self._make_request(url, params=params)
            if response:
                logger.info(f"Full response: {json.dumps(response, indent=2)}")
                if 'data' in response:
                    mentions = response['data']
                    logger.info(f"(+) Found {len(mentions)} new mentions!")
                    return mentions
                else:
                    logger.warning(f"No 'data' field in response: {response}")
                    if 'meta' in response and response['meta']['result_count'] == 0:
                        logger.info("No new mentions found since last check")
            return []
        except Exception as e:
            logger.error(f"Error checking mentions: {e}")
            return []

    def reply_to_tweet(self, tweet_id, message):
        """Reply to a tweet"""
        logger.info("\n=== Replying to Tweet ===")
        logger.info(f"Tweet ID: {tweet_id}")
        url = f"{cfg.API_BASE_URL}{cfg.TWEETS_ENDPOINT}"
        data = {
            'text': message,
            'reply': {'in_reply_to_tweet_id': tweet_id}
        }
        
        try:
            response = self._make_request(url, method='POST', json_data=data)
            if response:
                logger.info(f"(+) Successfully replied to tweet {tweet_id}")
                return response
            return None
        except Exception as e:
            logger.error(f"Error replying to tweet: {e}")
            return None

    def run_bot(self, check_interval=cfg.DEFAULT_CHECK_INTERVAL):
        """Run the bot continuously"""
        logger.info("\n=== Starting Bot ===")
        logger.info(f"[BOT] Username: {self.bot_username}")
        logger.info(f"[BOT] User ID: {self.user_id}")
        logger.info(f"[TIME] Check interval: {check_interval} seconds")
        logger.info("[API] Using Free API tier limits:")
        logger.info(f"      - {self.max_monthly_reads} reads per month")
        logger.info(f"      - {self.max_monthly_writes} writes per month")
        logger.info("==================\n")
        
        check_count = 0
        since_id = self.state.get('last_mention_id')
        
        while True:
            try:
                check_count += 1
                logger.info(f"\n=== Check #{check_count} ===")
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"[TIME] Current: {current_time}")
                
                if not self._check_api_limits(is_write=False):
                    sleep_time = (24 * 60 * 60)  # 24 hours
                    logger.warning(f"API limit reached. Sleeping for {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    continue

                mentions = self.check_mentions(since_id)
                
                if mentions:
                    since_id = mentions[0]['id']
                    self.state['last_mention_id'] = since_id
                    self._save_state()
                    for mention in mentions:
                        if not self._check_api_limits(is_write=True):
                            logger.warning("Write limit reached, skipping replies...")
                            break
                        
                        reply = f"Thank you for mentioning me! I'm here to help identify Sanskrit loanwords. (Tweet ID: {mention['id']})"
                        self.reply_to_tweet(mention['id'], reply)
                        time.sleep(5)  # Delay between replies
                
                # Add jitter to check interval
                jitter = random.randint(*cfg.JITTER_RANGE)
                adjusted_interval = max(cfg.MIN_CHECK_INTERVAL, 
                                     min(check_interval + jitter, cfg.MAX_CHECK_INTERVAL))
                logger.info(f"\n... Waiting {adjusted_interval} seconds before next check ...")
                time.sleep(adjusted_interval)
                
            except KeyboardInterrupt:
                logger.info("\n>>> Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                logger.info(f"... Waiting {check_interval} seconds before retry ...")
                time.sleep(check_interval)

if __name__ == "__main__":
    try:
        bot = TwitterBot()
        bot.run_bot()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

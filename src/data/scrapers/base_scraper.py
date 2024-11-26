"""Base scraper 
logger = setup_logging("base")
class for Shabda Setu project."""

import abc
import time
from typing import List, Dict, Optional
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from config.logging_config import setup_logging
from config.logging_config import setup_logging

logger = setup_logging('scraper')

class BaseScraper(abc.ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, base_url: str, delay: float = 1.0):
        """Initialize the scraper.
        
        Args:
            base_url: The base URL of the website to scrape
            delay: Minimum delay between requests in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.delay = delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ShabdaSetu/1.0 (Sanskrit-Tamil Loanword Research Project)'
        })
        self._setup_robots_parser()

    def _setup_robots_parser(self):
        """Set up and parse robots.txt."""
        self.robots_parser = RobotFileParser()
        try:
            self.robots_parser.set_url(f"{self.base_url}/robots.txt")
            self.robots_parser.read()
        except Exception as e:
            logger.warning(f"Could not parse robots.txt: {e}")
            self.robots_parser = None

    def _can_fetch(self, url: str) -> bool:
        """Check if we're allowed to fetch the URL according to robots.txt."""
        if not self.robots_parser:
            return True
        return self.robots_parser.can_fetch("ShabdaSetu", url)

    def _respect_rate_limit(self):
        """Ensure we respect the rate limit between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()

    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return its BeautifulSoup object.
        
        Args:
            url: The URL to fetch
            
        Returns:
            BeautifulSoup object or None if fetch failed
        """
        if not self._can_fetch(url):
            logger.warning(f"Robots.txt disallows fetching {url}")
            return None

        self._respect_rate_limit()
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    @abc.abstractmethod
    def scrape_words(self) -> List[Dict[str, str]]:
        """Scrape Sanskrit-Tamil word pairs from the source.
        
        Returns:
            List of dictionaries containing word pairs and metadata
            Example: [
                {
                    'tamil_word': 'அகம்',
                    'sanskrit_word': 'अहम्',
                    'meaning': 'self, ego',
                    'source_url': 'https://example.com/word/123',
                    'confidence': 0.9
                }
            ]
        """
        pass

    def cleanup(self):
        """Clean up resources."""
        self.session.close()

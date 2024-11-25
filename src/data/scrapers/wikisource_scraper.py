"""Scraper for Wikisource's multilingual classical texts."""

import re
from typing import List, Dict, Optional, Set
import logging
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ...utils.script_utils import ScriptUtils, Script

logger = logging.getLogger(__name__)

class WikisourceScraper(BaseScraper):
    """Scraper for parallel texts in Sanskrit and other Indic languages from Wikisource."""
    
    def __init__(self, language: str):
        """Initialize the scraper.
        
        Args:
            language: Target language for parallel texts
        """
        super().__init__(
            base_url=f"https://{language}.wikisource.org",
            delay=1.0  # Respect Wikimedia rate limits
        )
        self.language = language
        
        # Map languages to their Wikisource categories containing Sanskrit translations
        self.category_map = {
            'tamil': 'சமஸ்கிருதத்திலிருந்து_மொழிபெயர்ப்புகள்',
            'telugu': 'సంస్కృత_అనువాదాలు',
            'kannada': 'ಸಂಸ್ಕೃತದಿಂದ_ಅನುವಾದಗಳು',
            'malayalam': 'സംസ്കൃതത്തിൽ_നിന്നുള്ള_പരിഭാഷകൾ',
            'bengali': 'সংস্কৃত_থেকে_অনুবাদ',
            'hindi': 'संस्कृत_से_अनुवाद'
        }
        
        # Known parallel text collections
        self.collections = {
            'bhagavad_gita': {
                'confidence': 0.9,  # Well-studied text
                'patterns': {
                    'sanskrit': r'श्लोक[:\s]+([^\n]+)',
                    'translation': r'अनुवाद[:\s]+([^\n]+)'
                }
            },
            'upanishads': {
                'confidence': 0.85,
                'patterns': {
                    'sanskrit': r'मूल[:\s]+([^\n]+)',
                    'translation': r'भाषा[:\s]+([^\n]+)'
                }
            }
        }
    
    def _extract_parallel_text(self, text: str, collection: str) -> List[Dict[str, str]]:
        """Extract parallel Sanskrit-target language text pairs.
        
        Args:
            text: Text content to process
            collection: Name of the collection (determines patterns to use)
            
        Returns:
            List of word pairs with metadata
        """
        pairs = []
        collection_info = self.collections[collection]
        
        # Find all Sanskrit-translation pairs
        sanskrit_matches = re.finditer(collection_info['patterns']['sanskrit'], text)
        translation_matches = re.finditer(collection_info['patterns']['translation'], text)
        
        for sanskrit_match, trans_match in zip(sanskrit_matches, translation_matches):
            sanskrit_text = sanskrit_match.group(1)
            translated_text = trans_match.group(1)
            
            # Extract individual words
            sanskrit_words = set(re.findall(r'[\u0900-\u097F]+', sanskrit_text))
            translated_words = set(re.findall(r'[\u0B80-\u0BFF]+', translated_text))  # Adjust range per language
            
            # Process each Sanskrit word
            for sanskrit_word in sanskrit_words:
                if not ScriptUtils.validate_script(sanskrit_word, Script.DEVANAGARI):
                    continue
                
                # Find potential translations in the target text
                for translated_word in translated_words:
                    # Validate script based on language
                    script_map = {
                        'tamil': Script.TAMIL,
                        'telugu': Script.TELUGU,
                        'kannada': Script.KANNADA,
                        'malayalam': Script.MALAYALAM,
                        'bengali': Script.BENGALI,
                        'hindi': Script.DEVANAGARI
                    }
                    
                    if self.language in script_map:
                        if not ScriptUtils.validate_script(translated_word, script_map[self.language]):
                            continue
                    
                    pairs.append({
                        'word': translated_word,
                        'sanskrit_word': sanskrit_word,
                        'language': self.language,
                        'confidence': collection_info['confidence'],
                        'source_url': self.current_url,
                        'context': {
                            'sanskrit': sanskrit_text,
                            'translation': translated_text,
                            'collection': collection
                        }
                    })
        
        return pairs
    
    def _get_category_pages(self, category: str) -> List[str]:
        """Get all pages in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of page URLs
        """
        pages = []
        next_url = f"/wiki/Category:{category}"
        
        while next_url:
            soup = self.get_page(self.base_url + next_url)
            if not soup:
                break
            
            # Get all page links
            mw_category = soup.find('div', {'class': 'mw-category'})
            if mw_category:
                for link in mw_category.find_all('a'):
                    pages.append(link['href'])
            
            # Find next page link
            next_link = soup.find('a', text=re.compile('next|अगला|తరువాత|ಮುಂದಿನ|അടുത്തത്|পরবর্তী|अगला'))
            next_url = next_link['href'] if next_link else None
        
        return pages
    
    def scrape_words(self) -> List[Dict[str, str]]:
        """Scrape Sanskrit-target language word pairs from parallel texts.
        
        Returns:
            List of dictionaries containing word pairs and metadata
        """
        words = []
        category = self.category_map.get(self.language)
        
        if not category:
            logger.warning(f"No category mapping for language: {self.language}")
            return words
        
        # Get all pages in the category
        pages = self._get_category_pages(category)
        
        # Process each page
        for page_url in pages:
            try:
                self.current_url = self.base_url + page_url
                soup = self.get_page(self.current_url)
                if not soup:
                    continue
                
                # Get page content
                content = soup.find('div', {'class': 'mw-parser-output'})
                if not content:
                    continue
                
                # Try to identify which collection this text belongs to
                page_text = content.get_text()
                for collection in self.collections:
                    pairs = self._extract_parallel_text(page_text, collection)
                    if pairs:
                        words.extend(pairs)
                        logger.info(
                            f"Found {len(pairs)} word pairs in {collection} "
                            f"({self.language})"
                        )
            
            except Exception as e:
                logger.error(f"Error processing page {page_url}: {e}")
        
        return words

"""Scraper for Sanskrit-Dictionary.com and other open dictionary sources."""

import re
from typing import List, Dict, Optional
import logging
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ...utils.script_utils import ScriptUtils, Script

logger = logging.getLogger(__name__)

class SanskritDictScraper(BaseScraper):
    """Scraper for Sanskrit-Dictionary.com, which provides free access to Sanskrit dictionaries."""
    
    def __init__(self, language: str):
        """Initialize the scraper.
        
        Args:
            language: Target language for loanwords
        """
        super().__init__(
            base_url="https://www.sanskrit-dictionary.com",
            delay=1.0
        )
        self.language = language
        
        # Map target language to search terms
        self.language_map = {
            'tamil': ['tamil', 'dravidian'],
            'telugu': ['telugu', 'andhra'],
            'kannada': ['kannada', 'karnataka'],
            'malayalam': ['malayalam', 'kerala'],
            'bengali': ['bengali', 'bangla'],
            'hindi': ['hindi', 'hindustani']
        }
    
    def _extract_word_info(self, soup: BeautifulSoup, url: str) -> Optional[Dict[str, str]]:
        """Extract word information from dictionary page.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page
            
        Returns:
            Dictionary containing word information or None if extraction failed
        """
        try:
            # Get Sanskrit word
            sanskrit_div = soup.find('div', class_='sanskrit-word')
            if not sanskrit_div:
                return None
            
            sanskrit_word = sanskrit_div.text.strip()
            if not ScriptUtils.validate_script(sanskrit_word, Script.DEVANAGARI):
                return None
            
            # Look for target language references
            target_langs = self.language_map.get(self.language, [])
            if not target_langs:
                return None
            
            # Search in etymology and definition sections
            etymology = soup.find('div', class_='etymology')
            definition = soup.find('div', class_='definition')
            
            if not etymology and not definition:
                return None
            
            text_to_search = ' '.join(
                div.text.lower() for div in [etymology, definition] 
                if div is not None
            )
            
            # Check if target language is mentioned
            if not any(lang in text_to_search for lang in target_langs):
                return None
            
            # Try to extract the word in target language
            word_pattern = rf'(?i)(?:{"|".join(target_langs)}).*?([^\s.,;]+)'
            match = re.search(word_pattern, text_to_search)
            if not match:
                return None
            
            word = match.group(1)
            
            # Validate word script
            script_map = {
                'tamil': Script.TAMIL,
                'telugu': Script.TELUGU,
                'kannada': Script.KANNADA,
                'malayalam': Script.MALAYALAM,
                'bengali': Script.BENGALI,
                'hindi': Script.DEVANAGARI
            }
            
            if self.language in script_map:
                if not ScriptUtils.validate_script(word, script_map[self.language]):
                    return None
            
            return {
                'word': word,
                'sanskrit_word': sanskrit_word,
                'language': self.language,
                'confidence': 0.7,  # Conservative confidence score
                'source_url': url
            }
            
        except Exception as e:
            logger.error(f"Error extracting word info: {e}")
            return None
    
    def scrape_words(self) -> List[Dict[str, str]]:
        """Scrape Sanskrit loanwords from the dictionary.
        
        Returns:
            List of dictionaries containing word pairs and metadata
        """
        words = []
        
        # Get list of letters to search
        letters = 'aāiīuūṛṝḷḹeēoōṃḥkgṅcjñṭḍṇtdnpbmyrlvśṣsh'
        
        for letter in letters:
            try:
                # Search for words starting with the letter
                search_url = f"{self.base_url}/dictionary/search"
                params = {
                    'q': letter,
                    'start': 0,
                    'rows': 100  # Limit results per page
                }
                
                response = self.session.get(search_url, params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Process each word entry
                for entry in soup.find_all('div', class_='dictionary-entry'):
                    entry_url = entry.find('a')['href']
                    entry_response = self.session.get(entry_url)
                    entry_response.raise_for_status()
                    
                    entry_soup = BeautifulSoup(entry_response.text, 'html.parser')
                    word_info = self._extract_word_info(entry_soup, entry_url)
                    
                    if word_info:
                        words.append(word_info)
                        logger.info(
                            f"Found Sanskrit loanword: {word_info['word']} <- "
                            f"{word_info['sanskrit_word']} ({self.language})"
                        )
            
            except Exception as e:
                logger.error(f"Error processing letter {letter}: {e}")
        
        return words

"""Scraper for Shabdanjali Digital Sanskrit Dictionary."""

import re
from typing import List, Dict, Optional
import logging
from bs4 import BeautifulSoup
from ..base_scraper import BaseScraper
from ...utils.script_utils import ScriptUtils, Script

logger = logging.getLogger(__name__)

class ShabdanjaliScraper(BaseScraper):
    """Scraper for Shabdanjali, a digital corpus of Sanskrit dictionaries."""
    
    def __init__(self, language: str):
        """Initialize the scraper.
        
        Args:
            language: Target language for translations
        """
        super().__init__(
            base_url="https://sanskrit.jnu.ac.in/shabdanjali",
            delay=1.0
        )
        self.language = language
        
        # Map languages to their codes in Shabdanjali
        self.language_map = {
            'hindi': 'hi',
            'bengali': 'bn',
            'tamil': 'ta',
            'telugu': 'te',
            'kannada': 'kn',
            'malayalam': 'ml'
        }
        
        # Dictionary types available
        self.dictionaries = {
            'amarakosha': {
                'confidence': 0.9,  # Classical Sanskrit thesaurus
                'endpoint': '/amara'
            },
            'sanskrit_hindi': {
                'confidence': 0.85,  # Modern Sanskrit-Hindi dictionary
                'endpoint': '/dict'
            }
        }
    
    def _extract_word_info(self, soup: BeautifulSoup, dictionary: str) -> Optional[Dict[str, str]]:
        """Extract word information from dictionary page.
        
        Args:
            soup: BeautifulSoup object of the page
            dictionary: Dictionary being used
            
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
            
            # Get translation
            trans_div = soup.find('div', {'lang': self.language_map.get(self.language)})
            if not trans_div:
                return None
            
            word = trans_div.text.strip()
            
            # Validate translation script
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
                'confidence': self.dictionaries[dictionary]['confidence'],
                'source_url': self.current_url,
                'context': {
                    'dictionary': dictionary,
                    'source': 'shabdanjali'
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting word info: {e}")
            return None
    
    def scrape_words(self) -> List[Dict[str, str]]:
        """Scrape Sanskrit-target language word pairs.
        
        Returns:
            List of dictionaries containing word pairs and metadata
        """
        words = []
        lang_code = self.language_map.get(self.language)
        
        if not lang_code:
            logger.warning(f"Language {self.language} not supported by Shabdanjali")
            return words
        
        # Process each dictionary
        for dict_name, dict_info in self.dictionaries.items():
            try:
                # Get dictionary index
                index_url = f"{self.base_url}{dict_info['endpoint']}/index.php"
                params = {'lang': lang_code}
                
                response = self.session.get(index_url, params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Get all word links
                word_links = soup.find_all('a', class_='word-link')
                
                for link in word_links:
                    try:
                        word_url = f"{self.base_url}{dict_info['endpoint']}/{link['href']}"
                        self.current_url = word_url
                        
                        word_response = self.session.get(word_url)
                        word_response.raise_for_status()
                        
                        word_soup = BeautifulSoup(word_response.text, 'html.parser')
                        word_info = self._extract_word_info(word_soup, dict_name)
                        
                        if word_info:
                            words.append(word_info)
                            logger.info(
                                f"Found Sanskrit word in {dict_name}: {word_info['word']} <- "
                                f"{word_info['sanskrit_word']} ({self.language})"
                            )
                    
                    except Exception as e:
                        logger.error(f"Error processing word link {link.get('href')}: {e}")
                        continue
            
            except Exception as e:
                logger.error(f"Error processing dictionary {dict_name}: {e}")
                continue
        
        return words

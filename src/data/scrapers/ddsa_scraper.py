"""Scraper for Digital Dictionaries of South Asia."""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from ...utils.script_utils import ScriptUtils, Script
from config.logging_config import setup_logging



logger = setup_logging("ddsa")
class DDSAScraper(BaseScraper):
    """Scraper for Digital Dictionaries of South Asia (University of Chicago)."""
    
    def __init__(self, language: str):
        """Initialize the scraper.
        
        Args:
            language: Target language for translations
        """
        super().__init__(
            base_url="https://dsal.uchicago.edu/dictionaries",
            delay=1.0
        )
        self.language = language
        
        # Available dictionaries by language
        self.dictionaries = {
            'tamil': [
                {
                    'name': 'tamil-tamil-sanskrit',
                    'confidence': 0.85,
                    'path': '/tamil/tamil-tamil-sanskrit'
                }
            ],
            'telugu': [
                {
                    'name': 'brown',  # Brown's Telugu-English Dictionary
                    'confidence': 0.8,
                    'path': '/telugu/brown'
                }
            ],
            'hindi': [
                {
                    'name': 'platts',  # Platts Hindi-Urdu-English Dictionary
                    'confidence': 0.8,
                    'path': '/hindi/platts'
                }
            ],
            'bengali': [
                {
                    'name': 'biswas-bengali-sanskrit',
                    'confidence': 0.85,
                    'path': '/bengali/biswas'
                }
            ]
        }
    
    def _extract_word_info(self, soup: BeautifulSoup, dictionary: Dict) -> Optional[Dict[str, str]]:
        """Extract word information from dictionary page.
        
        Args:
            soup: BeautifulSoup object of the page
            dictionary: Dictionary information
            
        Returns:
            Dictionary containing word information or None if extraction failed
        """
        try:
            # Extract entry content
            entry_div = soup.find('div', class_='entry')
            if not entry_div:
                return None
            
            # Look for Sanskrit words (in Devanagari)
            sanskrit_matches = re.findall(r'[\u0900-\u097F]+', entry_div.text)
            if not sanskrit_matches:
                return None
            
            # Get the main headword
            headword_div = soup.find('div', class_='headword')
            if not headword_div:
                return None
            
            word = headword_div.text.strip()
            
            # Validate scripts
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
            
            # Process each Sanskrit word found
            results = []
            for sanskrit_word in sanskrit_matches:
                if ScriptUtils.validate_script(sanskrit_word, Script.DEVANAGARI):
                    results.append({
                        'word': word,
                        'sanskrit_word': sanskrit_word,
                        'language': self.language,
                        'confidence': dictionary['confidence'],
                        'source_url': self.current_url,
                        'context': {
                            'dictionary': dictionary['name'],
                            'source': 'ddsa'
                        }
                    })
            
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error extracting word info: {e}")
            return None
    
    def scrape_words(self) -> List[Dict[str, str]]:
        """Scrape Sanskrit-target language word pairs.
        
        Returns:
            List of dictionaries containing word pairs and metadata
        """
        words = []
        
        # Get dictionaries for the target language
        lang_dicts = self.dictionaries.get(self.language, [])
        if not lang_dicts:
            logger.warning(f"No dictionaries available for language: {self.language}")
            return words
        
        # Process each dictionary
        for dictionary in lang_dicts:
            try:
                # Get dictionary index
                index_url = f"{self.base_url}{dictionary['path']}/index.html"
                response = self.session.get(index_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Get all entry links
                entry_links = soup.find_all('a', class_='entry-link')
                
                for link in entry_links:
                    try:
                        entry_url = f"{self.base_url}{dictionary['path']}/{link['href']}"
                        self.current_url = entry_url
                        
                        entry_response = self.session.get(entry_url)
                        entry_response.raise_for_status()
                        
                        entry_soup = BeautifulSoup(entry_response.text, 'html.parser')
                        word_info = self._extract_word_info(entry_soup, dictionary)
                        
                        if word_info:
                            words.append(word_info)
                            logger.info(
                                f"Found Sanskrit word in {dictionary['name']}: "
                                f"{word_info['word']} <- {word_info['sanskrit_word']} "
                                f"({self.language})"
                            )
                    
                    except Exception as e:
                        logger.error(f"Error processing entry {link.get('href')}: {e}")
                        continue
            
            except Exception as e:
                logger.error(f"Error processing dictionary {dictionary['name']}: {e}")
                continue
        
        return words

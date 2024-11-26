"""Scraper for Srujanika's Digital Archive and other Odia resources."""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from ...utils.script_utils import ScriptUtils, Script
from config.logging_config import setup_logging



logger = setup_logging("odia_dict")
class OdiaDictScraper(BaseScraper):
    def __init__(self, language: str):
        """Initialize the scraper.
        
        Args:
            language: Target language for translations (should be 'odia')
        """
        if language != 'odia':
            raise ValueError("OdiaDictScraper only supports Odia language")
            
        super().__init__(
            base_url="https://srujanika.org/dict",
            delay=1.0
        )
        self.language = language
        
        # Available dictionaries
        self.dictionaries = {
            'purnnachandra': {
                'name': 'Purnachandra Odia Dictionary',
                'confidence': 0.85,
                'endpoint': '/purnnachandra'
            },
            'sanskrit_odia': {
                'name': 'Sanskrit-Odia Dictionary',
                'confidence': 0.9,
                'endpoint': '/sanskrit'
            }
        }
        
        # Sanskrit word patterns in Odia text
        self.sanskrit_patterns = [
            r'ତତ୍ସମ\s*:\s*([^\n]+)',  # Tatsama words
            r'ସଂସ୍କୃତ\s*:\s*([^\n]+)',  # Sanskrit origin
            r'ବ୍ୟୁତ୍ପତ୍ତି\s*:\s*([^\n]+)'  # Etymology
        ]
    
    def scrape_words(self) -> List[Dict[str, str]]:
        """Scrape Sanskrit-Odia word pairs.
        
        Returns:
            List of dictionaries containing word pairs and metadata
        """
        words = []
        
        # Process each dictionary
        for dict_id, dict_info in self.dictionaries.items():
            try:
                logger.info(f"Processing {dict_info['name']} dictionary...")
                dict_url = f"{self.base_url}{dict_info['endpoint']}/index"
                
                # Get dictionary index
                soup = self.get_page(dict_url)
                if not soup:
                    continue
                
                # Get all word entries
                entries = soup.find_all('div', class_='word-entry')
                for entry in entries:
                    try:
                        word_info = self._extract_word_info(entry, dict_info)
                        if word_info:
                            words.append(word_info)
                            logger.info(
                                f"Found Sanskrit word in {dict_info['name']}: "
                                f"{word_info['word']} <- {word_info['sanskrit_word']}"
                            )
                    except Exception as e:
                        logger.error(f"Error processing entry in {dict_info['name']}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error processing dictionary {dict_info['name']}: {e}")
                continue
        
        return words
    
    def _extract_word_info(self, entry_soup: BeautifulSoup, dict_info: Dict) -> Optional[Dict[str, str]]:
        """Extract word information from dictionary entry.
        
        Args:
            entry_soup: BeautifulSoup object of the entry
            dict_info: Dictionary information
            
        Returns:
            Dictionary containing word information or None if extraction failed
        """
        try:
            # Get Odia word
            odia_div = entry_soup.find('div', class_='odia-word')
            if not odia_div:
                return None
                
            odia_word = odia_div.text.strip()
            if not ScriptUtils.validate_script(odia_word, Script.ODIA):
                return None
            
            # Get Sanskrit word and etymology
            definition_div = entry_soup.find('div', class_='definition')
            if not definition_div:
                return None
                
            definition_text = definition_div.text
            
            # Try to find Sanskrit word using patterns
            sanskrit_word = None
            etymology = None
            
            for pattern in self.sanskrit_patterns:
                match = re.search(pattern, definition_text)
                if match:
                    potential_word = match.group(1).strip()
                    if ScriptUtils.validate_script(potential_word, Script.DEVANAGARI):
                        sanskrit_word = potential_word
                        etymology = match.group(0)
                        break
            
            if not sanskrit_word:
                return None
            
            # Get usage examples if available
            examples_div = entry_soup.find('div', class_='examples')
            examples = [ex.text.strip() for ex in examples_div.find_all('li')] if examples_div else []
            
            return {
                'word': odia_word,
                'sanskrit_word': sanskrit_word,
                'language': self.language,
                'confidence': dict_info['confidence'],
                'source_url': self.current_url,
                'context': {
                    'dictionary': dict_info['name'],
                    'etymology': etymology,
                    'examples': examples,
                    'source': 'srujanika'
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting word info: {e}")
            return None
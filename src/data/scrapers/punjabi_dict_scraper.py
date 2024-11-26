"""Scraper for Punjabi University's Digital Dictionary and other Punjabi resources."""

import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from ...utils.script_utils import ScriptUtils, Script
from config.logging_config import setup_logging



logger = setup_logging("punjabi_dict")
class PunjabiDictScraper(BaseScraper):
    def __init__(self, language: str):
        """Initialize the scraper.
        
        Args:
            language: Target language for translations (should be 'punjabi')
        """
        if language != 'punjabi':
            raise ValueError("PunjabiDictScraper only supports Punjabi language")
            
        super().__init__(
            base_url="https://www.punjabidict.edu.in",
            delay=1.0
        )
        self.language = language
        
        # Available dictionaries
        self.dictionaries = {
            'mahan_kosh': {
                'name': 'Mahan Kosh',
                'confidence': 0.85,
                'endpoint': '/mahan-kosh'
            },
            'punjabi_sanskrit': {
                'name': 'Punjabi-Sanskrit Dictionary',
                'confidence': 0.9,
                'endpoint': '/sanskrit'
            }
        }
    
    def scrape_words(self) -> List[Dict[str, str]]:
        """Scrape Sanskrit-Punjabi word pairs.
        
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
            # Get Punjabi word
            punjabi_div = entry_soup.find('div', class_='punjabi-word')
            if not punjabi_div:
                return None
                
            punjabi_word = punjabi_div.text.strip()
            if not ScriptUtils.validate_script(punjabi_word, Script.GURMUKHI):
                return None
            
            # Get Sanskrit word
            sanskrit_div = entry_soup.find('div', class_='sanskrit-word')
            if not sanskrit_div:
                return None
                
            sanskrit_word = sanskrit_div.text.strip()
            if not ScriptUtils.validate_script(sanskrit_word, Script.DEVANAGARI):
                return None
            
            # Get etymology information if available
            etymology_div = entry_soup.find('div', class_='etymology')
            etymology = etymology_div.text.strip() if etymology_div else None
            
            # Get usage examples if available
            examples_div = entry_soup.find('div', class_='examples')
            examples = [ex.text.strip() for ex in examples_div.find_all('li')] if examples_div else []
            
            return {
                'word': punjabi_word,
                'sanskrit_word': sanskrit_word,
                'language': self.language,
                'confidence': dict_info['confidence'],
                'source_url': self.current_url,
                'context': {
                    'dictionary': dict_info['name'],
                    'etymology': etymology,
                    'examples': examples,
                    'source': 'punjabi_university'
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting word info: {e}")
            return None

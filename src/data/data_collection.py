"""Data collection module for Shabda Setu project."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from ..core.database import Database
from ..core.word_reconciliation import WordReconciliation
from .scrapers.base_scraper import BaseScraper
from .scrapers.wiktionary_scraper import WiktionaryScraper
from .scrapers.sanskrit_dict_scraper import SanskritDictScraper
from .scrapers.wikisource_scraper import WikisourceScraper
from .scrapers.ddsa_scraper import DDSAScraper
from .scrapers.punjabi_dict_scraper import PunjabiDictScraper
from .scrapers.gujarati_dict_scraper import GujaratiDictScraper
from .scrapers.odia_dict_scraper import OdiaDictScraper
from ..utils.script_utils import ScriptUtils, Script
from config.logging_config import setup_logging

logger = setup_logging("data_collector")

class DataCollector:
    """Main class for collecting Sanskrit loanwords across Indic languages."""
    
    # Dictionary source weights for confidence calculation
    SCRAPERS = {
        'wiktionary': {
            'class': WiktionaryScraper,
            'weight': 0.7,
            'description': 'Wiktionary Sanskrit loanwords'
        },
        'sanskrit_dict': {
            'class': SanskritDictScraper,
            'weight': 0.8,
            'description': 'Sanskrit Dictionary etymologies'
        },
        'wikisource': {
            'class': WikisourceScraper,
            'weight': 0.9,
            'description': 'Classical texts with translations'
        },
        'ddsa': {
            'class': DDSAScraper,
            'weight': 0.85,
            'description': 'Digital Dictionaries of South Asia'
        },
        'punjabi_dict': {
            'class': PunjabiDictScraper,
            'weight': 0.85,
            'description': 'Punjabi University Digital Dictionary'
        },
        'gujarati_dict': {
            'class': GujaratiDictScraper,
            'weight': 0.85,
            'description': 'Gujarat Vidyapith Dictionary'
        },
        'odia_dict': {
            'class': OdiaDictScraper,
            'weight': 0.85,
            'description': "Srujanika's Odia Dictionary"
        }
    }
    
    def __init__(self, db: Database, languages: List[str] = None, scrapers: List[str] = None):
        """Initialize the data collector.
        
        Args:
            db: Database instance to store collected words
            languages: List of languages to collect words for. If None, collects for all supported languages.
            scrapers: List of scrapers to use. If None, uses all available scrapers.
        """
        self.db = db
        self.languages = languages or list(WiktionaryScraper.SUPPORTED_LANGUAGES.keys())
        self.active_scrapers = scrapers or list(self.SCRAPERS.keys())
        
        # Initialize scrapers for each language
        self.scrapers = []
        for lang in self.languages:
            for scraper_id in self.active_scrapers:
                try:
                    scraper_info = self.SCRAPERS[scraper_id]
                    scraper = scraper_info['class'](lang)
                    self.scrapers.append((scraper, scraper_info['weight']))
                    logger.info(
                        f"Initialized {scraper_id} for {lang}: "
                        f"{scraper_info['description']}"
                    )
                except ValueError as e:
                    logger.warning(f"Skipping {scraper_id} for language '{lang}': {e}")
    
    def _adjust_confidence(self, word_info: Dict[str, str], scraper_weight: float) -> Dict[str, str]:
        """Adjust confidence score based on scraper weight and validation.
        
        Args:
            word_info: Word information dictionary
            scraper_weight: Weight of the scraper
            
        Returns:
            Updated word information dictionary
        """
        base_confidence = word_info['confidence']
        
        # Validate scripts
        script_map = {
            'tamil': Script.TAMIL,
            'telugu': Script.TELUGU,
            'kannada': Script.KANNADA,
            'malayalam': Script.MALAYALAM,
            'bengali': Script.BENGALI,
            'hindi': Script.DEVANAGARI,
            'punjabi': Script.GURMUKHI,
            'gujarati': Script.GUJARATI,
            'odia': Script.ODIA
        }
        
        script_validation = 1.0
        if word_info['language'] in script_map:
            # Check target language word
            if not ScriptUtils.validate_script(
                word_info['word'], 
                script_map[word_info['language']], 
                allow_diacritics=True
            ):
                script_validation *= 0.8
            
            # Check Sanskrit word
            if not ScriptUtils.validate_script(
                word_info['sanskrit_word'],
                Script.DEVANAGARI,
                allow_diacritics=True
            ):
                script_validation *= 0.8
        
        # Additional context-based adjustments
        if 'context' in word_info:
            # Higher confidence for words from classical texts
            if word_info['context'].get('collection') in ['bhagavad_gita', 'upanishads']:
                script_validation *= 1.1
        
        # Adjust confidence
        word_info['confidence'] = min(1.0, base_confidence * scraper_weight * script_validation)
        return word_info
        
    def collect_and_store(self, cache_dir: str = None):
        """Collect words from all sources and store them in the database.
        
        Args:
            cache_dir: Optional directory to cache scraped data
        """
        all_words = []
        
        # Create cache directory if specified
        if cache_dir:
            cache_path = Path(cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)
        
        # Collect words from each scraper
        for scraper, weight in self.scrapers:
            try:
                logger.info(f"Starting scraping {scraper.language} with {scraper.__class__.__name__}")
                words = scraper.scrape_words()
                logger.debug(f"Scraped {len(words)} words from {scraper.language} using {scraper.__class__.__name__}")
                
                # Adjust confidence scores
                words = [self._adjust_confidence(word, weight) for word in words]
                logger.debug(f"Adjusted confidence for {len(words)} words from {scraper.language}")
                
                # Cache results if directory specified
                if cache_dir:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    cache_file = cache_path / f"{scraper.__class__.__name__}_{scraper.language}_{timestamp}.json"
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(words, f, ensure_ascii=False, indent=2)
                    logger.debug(f"Cached {len(words)} words to {cache_file}")
                
                all_words.extend(words)
                logger.info(
                    f"Collected {len(words)} words from {scraper.language} using "
                    f"{scraper.__class__.__name__} (confidence: {weight:.2f})"
                )
                
            except Exception as e:
                logger.error(f"Error in {scraper.__class__.__name__} for {scraper.language}: {e}")
            finally:
                scraper.cleanup()
        
        # Reconcile conflicting information
        reconciliation = WordReconciliation()
        reconciled_words = reconciliation.reconcile(all_words)
        logger.info(
            f"Reconciled {len(all_words)} raw entries into {len(reconciled_words)} "
            "unique word pairs"
        )
        
        # Store reconciled words in database
        stored_count = 0
        for word_info in reconciled_words:
            try:
                logger.debug(f"Storing word: {word_info}")
                self.db.add_word(
                    word=word_info['word'],
                    sanskrit_word=word_info['sanskrit_word'],
                    language=word_info['language'],
                    confidence=word_info['confidence'],
                    source_url=word_info['source_url'],
                    meanings=word_info.get('meanings'),
                    usage_examples=word_info.get('usage_examples'),
                    context=word_info.get('context')
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"Error storing word {word_info}: {e}")
        
        logger.info(
            f"Successfully stored {stored_count} reconciled entries in the database"
        )
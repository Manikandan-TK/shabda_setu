"""Tests for the web scraping infrastructure."""

import unittest
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
import tempfile
import json
from pathlib import Path
import logging
import sys
import responses

from src.data.scrapers.wiktionary_scraper import WiktionaryScraper
from src.data.data_collection import DataCollector
from src.core.database import Database

class VerboseLogger:
    """A helper class to capture and print detailed logging information."""
    def __init__(self):
        self.log_capture = []
        self.logger = logging.getLogger('test_debug')
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Capture handler
        self.capture_handler = logging.StreamHandler()
        self.capture_handler.setLevel(logging.DEBUG)
        self.capture_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(self.capture_handler)

class TestWiktionaryScraper(unittest.TestCase):
    """Test cases for the WiktionaryScraper class."""
    
    def setUp(self):
        self.tamil_scraper = WiktionaryScraper('tamil')
        self.hindi_scraper = WiktionaryScraper('hindi')
    
    def test_invalid_language(self):
        """Test initialization with invalid language."""
        with self.assertRaises(ValueError):
            WiktionaryScraper('invalid_language')
    
    def test_extract_word_info_tamil(self):
        """Test word info extraction with valid Tamil HTML."""
        html = '''
        <html>
            <h1 id="firstHeading">அகம்</h1>
            <h2>மொழியாக்கம்</h2>
            <p>संस्कृतम् अहम् (aham) என்ற சொல்லிலிருந்து வந்தது.</p>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        self.tamil_scraper.current_url = "https://ta.wiktionary.org/wiki/அகம்"
        
        result = self.tamil_scraper._extract_word_info(soup)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['word'], 'அகம்')
        self.assertEqual(result['sanskrit_word'], 'अहम्')
        self.assertEqual(result['language'], 'tamil')
        self.assertEqual(result['confidence'], 0.8)
    
    def test_extract_word_info_hindi(self):
        """Test word info extraction with valid Hindi HTML."""
        html = '''
        <html>
            <h1 id="firstHeading">आकाश</h1>
            <h2>व्युत्पत्ति</h2>
            <p>संस्कृत आकाश (ākāśa) से</p>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        self.hindi_scraper.current_url = "https://hi.wiktionary.org/wiki/आकाश"
        
        result = self.hindi_scraper._extract_word_info(soup)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['word'], 'आकाश')
        self.assertEqual(result['sanskrit_word'], 'आकाश')
        self.assertEqual(result['language'], 'hindi')
        self.assertEqual(result['confidence'], 0.8)
    
    def test_extract_word_info_invalid_script(self):
        """Test word info extraction with invalid script."""
        html = '''
        <html>
            <h1 id="firstHeading">hello</h1>
            <h2>मौलिक</h2>
            <p>संस्कृत से</p>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        result = self.hindi_scraper._extract_word_info(soup)
        self.assertIsNone(result)

class TestDataCollector(unittest.TestCase):
    """Test cases for the DataCollector class."""
    
    def setUp(self):
        # Setup verbose logging
        self.verbose_logger = VerboseLogger()
        
        # Mock database
        self.db = MagicMock(spec=Database)
        self.db.add_word.return_value = True
    
    @responses.activate
    @patch('src.data.data_collection.WiktionaryScraper')
    @patch('src.data.data_collection.SanskritDictScraper')
    @patch('src.data.data_collection.WikisourceScraper')
    @patch('src.data.data_collection.DDSAScraper')
    @patch('src.data.data_collection.ScriptUtils')
    @patch('src.data.data_collection.WordReconciliation')
    @patch('src.data.data_collection.logger')  # Patch the logger in data_collection
    def test_collect_and_store_multiple_languages(
        self, 
        mock_data_collection_logger, 
        MockReconciliation, 
        MockScriptUtils, 
        MockDDSA, 
        MockWikisource, 
        MockSanskritDict, 
        MockWiktionary
    ):
        """Test collecting and storing words from multiple languages."""
        # Configure mock logger to use our verbose logger
        mock_data_collection_logger.info = self.verbose_logger.logger.info
        mock_data_collection_logger.error = self.verbose_logger.logger.error
        mock_data_collection_logger.warning = self.verbose_logger.logger.warning
        mock_data_collection_logger.debug = self.verbose_logger.logger.debug
        
        # Mock SUPPORTED_LANGUAGES
        supported_languages = {
            'tamil': 'ta',
            'hindi': 'hi'
        }
        MockWiktionary.SUPPORTED_LANGUAGES = supported_languages
        MockSanskritDict.SUPPORTED_LANGUAGES = supported_languages
        MockWikisource.SUPPORTED_LANGUAGES = supported_languages
        MockDDSA.SUPPORTED_LANGUAGES = supported_languages
        
        # Mock script validation to always return True
        MockScriptUtils.validate_script.return_value = True
        
        # Mock word reconciliation to return input unchanged
        mock_reconciliation = MagicMock()
        def mock_reconcile(words):
            self.verbose_logger.logger.info(f"Reconciling {len(words)} words")
            return words
        mock_reconciliation.reconcile.side_effect = mock_reconcile
        MockReconciliation.return_value = mock_reconciliation
        
        # Mock HTTP responses for external requests
        responses.add(responses.GET, 'https://www.sanskrit-dictionary.com', json={'words': []}, status=200)
        responses.add(responses.GET, 'https://hindi.wikisource.org', json={'words': []}, status=200)
        responses.add(responses.GET, 'https://dsal.uchicago.edu/dictionaries/hindi/platts/index.html', json={'words': []}, status=200)
        
        # Mock data - each scraper returns a unique word for each language
        mock_words = {
            'tamil': {
                'wiktionary': [{
                    'word': 'அகம்',
                    'sanskrit_word': 'अहम्',
                    'language': 'tamil',
                    'confidence': 0.8,
                    'source_url': 'https://ta.wiktionary.org/wiki/அகம்'
                }],
                'sanskrit_dict': [{
                    'word': 'ஆகாசம்',
                    'sanskrit_word': 'आकाश',
                    'language': 'tamil',
                    'confidence': 0.8,
                    'source_url': 'https://www.sanskrit-dictionary.com/ta/ஆகாசம்'
                }],
                'wikisource': [{
                    'word': 'தர்மம்',
                    'sanskrit_word': 'धर्म',
                    'language': 'tamil',
                    'confidence': 0.8,
                    'source_url': 'https://ta.wikisource.org/wiki/தர்மம்'
                }],
                'ddsa': [{
                    'word': 'கர்மம்',
                    'sanskrit_word': 'कर्म',
                    'language': 'tamil',
                    'confidence': 0.8,
                    'source_url': 'https://dsal.uchicago.edu/dictionaries/tamil/கர்மம்'
                }]
            },
            'hindi': {
                'wiktionary': [{
                    'word': 'आकाश',
                    'sanskrit_word': 'आकाश',
                    'language': 'hindi',
                    'confidence': 0.8,
                    'source_url': 'https://hi.wiktionary.org/wiki/आकाश'
                }],
                'sanskrit_dict': [{
                    'word': 'कर्म',
                    'sanskrit_word': 'कर्म',
                    'language': 'hindi',
                    'confidence': 0.8,
                    'source_url': 'https://www.sanskrit-dictionary.com/hi/कर्म'
                }],
                'wikisource': [{
                    'word': 'धर्म',
                    'sanskrit_word': 'धर्म',
                    'language': 'hindi',
                    'confidence': 0.8,
                    'source_url': 'https://hi.wikisource.org/wiki/धर्म'
                }],
                'ddsa': [{
                    'word': 'अहम्',
                    'sanskrit_word': 'अहम्',
                    'language': 'hindi',
                    'confidence': 0.8,
                    'source_url': 'https://dsal.uchicago.edu/dictionaries/hindi/अहम्'
                }]
            }
        }
        
        # Create mock instances for each language and scraper
        mock_instances = {}
        scrapers = ['wiktionary', 'sanskrit_dict', 'wikisource', 'ddsa']
        for lang in ['tamil', 'hindi']:
            lang_instances = {}
            for scraper_name in scrapers:
                mock_instance = MagicMock()
                mock_instance.language = lang
                mock_instance.scrape_words.return_value = mock_words[lang][scraper_name]
                mock_instance.cleanup.return_value = None
                # Add supported languages to instance
                mock_instance.SUPPORTED_LANGUAGES = supported_languages
                lang_instances[scraper_name] = mock_instance
            mock_instances[lang] = lang_instances
        
        # Configure mock classes to return appropriate instances
        def create_mock_instance(lang, scraper_name):
            self.verbose_logger.logger.info(f"Creating mock instance for {lang} - {scraper_name}")
            instance = mock_instances[lang][scraper_name.lower()]
            instance.language = lang
            return instance
        
        # Patch each scraper to use our mock creation function
        MockWiktionary.side_effect = lambda lang: create_mock_instance(lang, 'wiktionary')
        MockSanskritDict.side_effect = lambda lang: create_mock_instance(lang, 'sanskrit_dict')
        MockWikisource.side_effect = lambda lang: create_mock_instance(lang, 'wikisource')
        MockDDSA.side_effect = lambda lang: create_mock_instance(lang, 'ddsa')
        
        # Create collector with our mocked classes
        self.verbose_logger.logger.info("\nInitializing DataCollector...")
        self.collector = DataCollector(self.db, languages=['tamil', 'hindi'])
        
        # Run the collection process
        self.verbose_logger.logger.info("\nStarting collection process...")
        with tempfile.TemporaryDirectory() as temp_dir:
            self.collector.collect_and_store(cache_dir=temp_dir)
            
            # Print out all collected logs for debugging
            print("\n--- CAPTURED LOGS ---")
            for record in self.verbose_logger.log_capture:
                print(record)
            
            self.verbose_logger.logger.info(f"\nWords added to DB: {self.db.add_word.call_count}")
            
            # We expect 8 words to be added (2 languages * 4 scrapers * 1 word each)
            self.assertEqual(self.db.add_word.call_count, 8)
            
            # Verify words were stored with correct data
            for lang in ['tamil', 'hindi']:
                for scraper_name in scrapers:
                    word_data = mock_words[lang][scraper_name][0]
                    self.db.add_word.assert_any_call(
                        word=word_data['word'],
                        sanskrit_word=word_data['sanskrit_word'],
                        language=word_data['language'],
                        confidence=word_data['confidence'],
                        source_url=word_data['source_url'],
                        meanings=word_data.get('meanings'),
                        usage_examples=word_data.get('usage_examples'),
                        context=word_data.get('context')
                    )

if __name__ == '__main__':
    unittest.main()

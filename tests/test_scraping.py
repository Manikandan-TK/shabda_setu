"""Tests for the web scraping infrastructure."""

import unittest
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
import tempfile
import json
from pathlib import Path

from src.data.scrapers.wiktionary_scraper import WiktionaryScraper
from src.data.data_collection import DataCollector
from src.core.database import Database

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
        self.db = MagicMock(spec=Database)
        self.collector = DataCollector(self.db, languages=['tamil', 'hindi'])
        
    @patch('src.data.scrapers.wiktionary_scraper.WiktionaryScraper.scrape_words')
    def test_collect_and_store_multiple_languages(self, mock_scrape):
        """Test collecting and storing words from multiple languages."""
        # Mock data
        mock_words = {
            'tamil': [{
                'word': 'அகம்',
                'sanskrit_word': 'अहम्',
                'language': 'tamil',
                'confidence': 0.8,
                'source_url': 'https://ta.wiktionary.org/wiki/அகம்'
            }],
            'hindi': [{
                'word': 'आकाश',
                'sanskrit_word': 'आकाश',
                'language': 'hindi',
                'confidence': 0.8,
                'source_url': 'https://hi.wiktionary.org/wiki/आकाश'
            }]
        }
        
        # Configure mock to return different values for different languages
        mock_scrape.side_effect = lambda: mock_words[mock_scrape._mock_parent.language]
        
        # Create temporary directory for cache
        with tempfile.TemporaryDirectory() as temp_dir:
            self.collector.collect_and_store(cache_dir=temp_dir)
            
            # Check if words were stored in database
            self.assertEqual(self.db.add_word.call_count, 2)
            
            # Verify Tamil word was stored
            self.db.add_word.assert_any_call(
                word='அகம்',
                sanskrit_word='अहम्',
                language='tamil',
                confidence=0.8,
                source_url='https://ta.wiktionary.org/wiki/அகம்'
            )
            
            # Verify Hindi word was stored
            self.db.add_word.assert_any_call(
                word='आकाश',
                sanskrit_word='आकाश',
                language='hindi',
                confidence=0.8,
                source_url='https://hi.wiktionary.org/wiki/आकाश'
            )
            
            # Check if cache files were created
            cache_files = list(Path(temp_dir).glob('*.json'))
            self.assertEqual(len(cache_files), 2)  # One for each language

if __name__ == '__main__':
    unittest.main()

"""Unit tests for web scrapers."""

import unittest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path
from bs4 import BeautifulSoup
import requests

from src.data.scrapers.wiktionary_scraper import WiktionaryScraper
from src.data.scrapers.sanskrit_dict_scraper import SanskritDictScraper
from src.data.scrapers.ddsa_scraper import DDSAScraper
from config.logging_config import setup_logging

class MockResponse:
    """Mock response object for requests."""
    def __init__(self, html_content, status_code=200):
        self.text = html_content
        self.status_code = status_code
    
    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.exceptions.HTTPError(f"HTTP Error: {self.status_code}")

class TestWiktionaryScraper(unittest.TestCase):
    """Test cases for WiktionaryScraper."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.scraper = WiktionaryScraper("tamil")
        
        # Sample HTML content
        self.sample_page_html = """
        <html>
            <div class="etymology">
                <span class="etymology-label">Etymology</span>
                <p>From Sanskrit <i>देव</i> (deva)</p>
            </div>
            <div class="word-entry">
                <h1>தேவன்</h1>
                <p>Meaning: god, divine being</p>
            </div>
        </html>
        """
    
    @patch('requests.Session')
    def test_get_page(self, mock_session):
        """Test page retrieval and parsing."""
        # Setup mock
        mock_session.return_value.get.return_value = MockResponse(self.sample_page_html)
        
        # Test
        soup = self.scraper.get_page("https://ta.wiktionary.org/wiki/தேவன்")
        
        # Verify
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertIn("Etymology", soup.text)
    
    @patch('requests.Session')
    def test_extract_word_info(self, mock_session):
        """Test word information extraction."""
        # Setup
        soup = BeautifulSoup(self.sample_page_html, 'html.parser')
        
        # Test
        word_info = self.scraper._extract_word_info(soup)
        
        # Verify
        self.assertIsInstance(word_info, dict)
        self.assertIn('word', word_info)
        self.assertIn('sanskrit_word', word_info)
        self.assertEqual(word_info.get('language'), 'tamil')
    
    @patch('requests.Session')
    def test_scrape_words(self, mock_session):
        """Test the complete scraping process."""
        # Setup mock responses
        category_html = """
        <html>
            <div class="mw-category">
                <a href="/wiki/தேவன்">தேவன்</a>
            </div>
        </html>
        """
        mock_session.return_value.get.side_effect = [
            MockResponse(category_html),
            MockResponse(self.sample_page_html)
        ]
        
        # Test
        words = self.scraper.scrape_words()
        
        # Verify
        self.assertIsInstance(words, list)
        self.assertTrue(len(words) > 0)
        self.assertIn('word', words[0])
        self.assertIn('sanskrit_word', words[0])

class TestSanskritDictScraper(unittest.TestCase):
    """Test cases for SanskritDictScraper."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.scraper = SanskritDictScraper("hindi")
        
        # Sample HTML content
        self.sample_page_html = """
        <html>
            <div class="entry">
                <h2>देव</h2>
                <div class="definition">
                    <p>देवता (देव)</p>
                    <p>Etymology: Sanskrit देव (deva)</p>
                </div>
            </div>
        </html>
        """
    
    @patch('requests.Session')
    def test_extract_word_info(self, mock_session):
        """Test word information extraction."""
        # Setup
        soup = BeautifulSoup(self.sample_page_html, 'html.parser')
        
        # Test
        word_info = self.scraper._extract_word_info(soup, {'name': 'test_dict'})
        
        # Verify
        self.assertIsInstance(word_info, dict)
        self.assertIn('word', word_info)
        self.assertIn('sanskrit_word', word_info)
        self.assertEqual(word_info.get('language'), 'hindi')

class TestDDSAScraper(unittest.TestCase):
    """Test cases for DDSAScraper."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.scraper = DDSAScraper("bengali")
        
        # Sample HTML content
        self.sample_page_html = """
        <html>
            <div class="entry">
                <h1>দেব</h1>
                <div class="etymology">
                    <p>From Sanskrit देव (deva)</p>
                </div>
                <div class="meaning">god, deity</div>
            </div>
        </html>
        """
    
    @patch('requests.Session')
    def test_extract_word_info(self, mock_session):
        """Test word information extraction."""
        # Setup
        soup = BeautifulSoup(self.sample_page_html, 'html.parser')
        
        # Test
        word_info = self.scraper._extract_word_info(soup, {'name': 'test_dict'})
        
        # Verify
        self.assertIsInstance(word_info, dict)
        self.assertIn('word', word_info)
        self.assertIn('sanskrit_word', word_info)
        self.assertEqual(word_info.get('language'), 'bengali')
    
    def test_unsupported_language(self):
        """Test scraper behavior with unsupported language."""
        with self.assertRaises(ValueError):
            DDSAScraper("unsupported_language")

class TestScraperLogging(unittest.TestCase):
    """Test cases for scraper logging functionality."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.logger = setup_logging("test_scraper")
        self.scraper = WiktionaryScraper("tamil")
    
    @patch('requests.Session')
    def test_scraping_logs(self, mock_session):
        """Test if scraping operations are properly logged."""
        # Setup mock
        mock_session.return_value.get.return_value = MockResponse(
            "<html><div>Test content</div></html>"
        )
        
        # Patch logger
        with patch('src.data.scrapers.wiktionary_scraper.logger') as mock_logger:
            self.scraper.get_page("https://test.url")
            
            # Verify logging calls
            mock_logger.info.assert_called()
            mock_logger.error.assert_not_called()
    
    @patch('requests.Session')
    def test_error_logging(self, mock_session):
        """Test if errors are properly logged."""
        # Setup mock to raise an exception
        mock_session.return_value.get.return_value = MockResponse(
            "", status_code=404
        )
        
        # Patch logger
        with patch('src.data.scrapers.wiktionary_scraper.logger') as mock_logger:
            self.scraper.get_page("https://test.url")
            
            # Verify error logging
            mock_logger.error.assert_called()

if __name__ == '__main__':
    unittest.main()

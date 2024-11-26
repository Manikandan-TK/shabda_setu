"""Wiktionary scraper for Sanskrit loanwords in Indic languages."""

import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin
from .base_scraper import BaseScraper
from config.logging_config import setup_logging



logger = setup_logging("wiktionary")
class WiktionaryScraper(BaseScraper):
    """Scraper for Wiktionary to find Sanskrit loanwords in Indic languages."""
    
    # Language codes and their corresponding Wiktionary domains
    SUPPORTED_LANGUAGES = {
        'tamil': {
            'code': 'ta',
            'script_range': (0x0B80, 0x0BFF),  # Tamil script Unicode range
            'category': 'பகுப்பு:சமஸ்கிருதம்',
            'etymology_headers': ['மொழியாக்கம்', 'வரலாறு']
        },
        'hindi': {
            'code': 'hi',
            'script_range': (0x0900, 0x097F),  # Devanagari script Unicode range
            'category': 'श्रेणी:संस्कृत_से_हिन्दी',
            'etymology_headers': ['व्युत्पत्ति', 'इतिहास']
        },
        'bengali': {
            'code': 'bn',
            'script_range': (0x0980, 0x09FF),  # Bengali script Unicode range
            'category': 'বিষয়শ্রেণী:সংস্কৃত_থেকে_বাংলা',
            'etymology_headers': ['ব্যুৎপত্তি', 'ইতিহাস']
        },
        'telugu': {
            'code': 'te',
            'script_range': (0x0C00, 0x0C7F),  # Telugu script Unicode range
            'category': 'వర్గం:సంస్కృతం_నుండి_తెలుగు',
            'etymology_headers': ['వ్యుత్పత్తి', 'చరిత్ర']
        },
        'malayalam': {
            'code': 'ml',
            'script_range': (0x0D00, 0x0D7F),  # Malayalam script Unicode range
            'category': 'വർഗ്ഗം:സംസ്കൃതത്തിൽ_നിന്ന്',
            'etymology_headers': ['വ്യുൽപ്പത്തി', 'ചരിത്രം']
        },
        'kannada': {
            'code': 'kn',
            'script_range': (0x0C80, 0x0CFF),  # Kannada script Unicode range
            'category': 'ವರ್ಗ:ಸಂಸ್ಕೃತದಿಂದ_ಕನ್ನಡಕ್ಕೆ',
            'etymology_headers': ['ವ್ಯುತ್ಪತ್ತಿ', 'ಇತಿಹಾಸ']
        },
        'gujarati': {
            'code': 'gu',
            'script_range': (0x0A80, 0x0AFF),  # Gujarati script Unicode range
            'category': 'શ્રેણી:સંસ્કૃત_થી_ગુજરાતી',
            'etymology_headers': ['વ્યુત્પત્તિ', 'ઇતિહાસ']
        },
        'punjabi': {
            'code': 'pa',
            'script_range': (0x0A00, 0x0A7F),  # Gurmukhi script Unicode range
            'category': 'ਸ਼੍ਰੇਣੀ:ਸੰਸਕ੍ਰਿਤ_ਤੋਂ_ਪੰਜਾਬੀ',
            'etymology_headers': ['ਵਿਉਤਪਤੀ', 'ਇਤਿਹਾਸ']
        },
        'odia': {
            'code': 'or',
            'script_range': (0x0B00, 0x0B7F),  # Odia script Unicode range
            'category': 'ଶ୍ରେଣୀ:ସଂସ୍କୃତରୁ_ଓଡ଼ିଆ',
            'etymology_headers': ['ବ୍ୟୁତ୍ପତ୍ତି', 'ଇତିହାସ']
        }
    }
    
    def __init__(self, language: str):
        """Initialize the scraper for a specific language.
        
        Args:
            language: Language to scrape (e.g., 'tamil', 'hindi', etc.)
        
        Raises:
            ValueError: If language is not supported
        """
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Language '{language}' not supported. Supported languages: {list(self.SUPPORTED_LANGUAGES.keys())}")
        
        self.language = language
        self.lang_info = self.SUPPORTED_LANGUAGES[language]
        super().__init__(
            base_url=f"https://{self.lang_info['code']}.wiktionary.org",
            delay=1.0  # Respect Wikimedia's rate limits
        )
        self.category_url = f"/wiki/{self.lang_info['category']}"

    def _is_script_match(self, text: str, script_range: Tuple[int, int]) -> bool:
        """Check if text contains characters from the specified script range."""
        start, end = script_range
        return any(start <= ord(c) <= end for c in text)

    def _extract_word_info(self, soup) -> Optional[Dict[str, str]]:
        """Extract word information from a Wiktionary page.
        
        Args:
            soup: BeautifulSoup object of the word page
            
        Returns:
            Dictionary containing word information or None if extraction failed
        """
        try:
            # Get word in target language (title)
            title = soup.find('h1', {'id': 'firstHeading'}).text.strip()
            
            # Find etymology section
            etym_section = None
            for h2 in soup.find_all('h2'):
                if any(header in h2.text for header in self.lang_info['etymology_headers']):
                    etym_section = h2.find_next_sibling()
                    break
            
            if not etym_section:
                return None
                
            # Look for Sanskrit word in etymology
            sanskrit_pattern = r'संस्कृत(?:म्)?|sanskṛtam?|sanskrit'
            etym_text = etym_section.text
            
            if not re.search(sanskrit_pattern, etym_text, re.IGNORECASE):
                return None
                
            # Extract Sanskrit word if present (within देवनागरी script)
            sanskrit_word = None
            
            # First try to find a pattern like "word (transliteration)"
            devanagari_iast_pattern = r'([\u0900-\u097F]+(?:\s*[\u0900-\u097F]+)*)\s*\(([a-zA-Z]+)\)'
            matches = re.finditer(devanagari_iast_pattern, etym_text)
            
            for match in matches:
                devanagari = match.group(1)
                iast = match.group(2).lower()
                # If we find a match with both Devanagari and IAST, use it
                # Skip the word "संस्कृतम्" itself
                if devanagari and iast and devanagari != 'संस्कृतम्':
                    sanskrit_word = devanagari.split()[-1]  # Take the last word if multiple
                    break
            
            # If no match found with IAST, try finding any Devanagari word
            if not sanskrit_word:
                devanagari_pattern = r'[\u0900-\u097F]+(?:\s*[\u0900-\u097F]+)*'
                matches = re.findall(devanagari_pattern, etym_text)
                if matches:
                    # Skip संस्कृतम् and take the next word
                    for word in matches:
                        if word != 'संस्कृतम्':
                            sanskrit_word = word.split()[-1]  # Take the last word if multiple
                            break
            
            if not sanskrit_word:
                return None
                
            # Verify the title contains characters from the target language script
            if not self._is_script_match(title, self.lang_info['script_range']):
                return None
                
            return {
                'word': title,
                'sanskrit_word': sanskrit_word,
                'language': self.language,
                'source_url': self.current_url,
                'confidence': 0.8  # Wiktionary is generally reliable
            }
            
        except Exception as e:
            logger.error(f"Error extracting word info: {e}")
            return None

    def _get_category_pages(self) -> List[str]:
        """Get all pages in the Sanskrit loanwords category."""
        pages = []
        next_url = self.category_url
        
        while next_url:
            soup = self.get_page(urljoin(self.base_url, next_url))
            if not soup:
                break
                
            # Get all word links in the category
            mw_category = soup.find('div', {'class': 'mw-category'})
            if mw_category:
                for link in mw_category.find_all('a'):
                    pages.append(link['href'])
            
            # Find next page link - handle different languages
            next_patterns = {
                'tamil': 'அடுத்த',
                'hindi': 'अगला',
                'bengali': 'পরবর্তী',
                'telugu': 'తరువాత',
                'malayalam': 'അടുത്തത്',
                'kannada': 'ಮುಂದಿನ',
                'gujarati': 'આગળ',
                'punjabi': 'ਅਗਲਾ',
                'odia': 'ପରବର୍ତ୍ତୀ'
            }
            next_pattern = next_patterns.get(self.language, 'next')
            next_link = soup.find('a', text=re.compile(next_pattern, re.IGNORECASE))
            next_url = next_link['href'] if next_link else None
            
        return pages

    def scrape_words(self) -> List[Dict[str, str]]:
        """Scrape Sanskrit loanwords from Wiktionary.
        
        Returns:
            List of dictionaries containing word pairs and metadata
        """
        words = []
        pages = self._get_category_pages()
        
        for page_url in pages:
            self.current_url = urljoin(self.base_url, page_url)
            soup = self.get_page(self.current_url)
            
            if not soup:
                continue
                
            word_info = self._extract_word_info(soup)
            if word_info:
                words.append(word_info)
                logger.info(f"Found Sanskrit loanword: {word_info['word']} <- {word_info['sanskrit_word']} ({self.language})")
        
        return words

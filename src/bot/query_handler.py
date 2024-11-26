from typing import Dict, List, Optional, Tuple
import re
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Query:
    raw_text: str
    words: List[str]
    query_type: str  # 'word_lookup', 'etymology', 'usage', 'translation'
    script_type: str  # Detected script type

class QueryHandler:
    def __init__(self):
        # Define script patterns for all major Indic languages
        self.script_patterns = {
            # North Indian Scripts
            'devanagari': re.compile(r'[\u0900-\u097F]'),  # Hindi, Marathi, Sanskrit
            'gurmukhi': re.compile(r'[\u0A00-\u0A7F]'),    # Punjabi
            'gujarati': re.compile(r'[\u0A80-\u0AFF]'),    # Gujarati
            
            # East Indian Scripts
            'bengali': re.compile(r'[\u0980-\u09FF]'),     # Bengali
            'odia': re.compile(r'[\u0B00-\u0B7F]'),        # Odia/Oriya
            
            # South Indian Scripts
            'tamil': re.compile(r'[\u0B80-\u0BFF]'),       # Tamil
            'telugu': re.compile(r'[\u0C00-\u0C7F]'),      # Telugu
            'kannada': re.compile(r'[\u0C80-\u0CFF]'),     # Kannada
            'malayalam': re.compile(r'[\u0D00-\u0D7F]'),   # Malayalam
        }
        
        # Query patterns for different types of questions
        self.query_patterns = {
            'word_lookup': {
                'en': r'what(?:\s+is|\'s)\s+(.+?)(?:\s+mean(?:ing|s)?)?[\?]?$',
                'hi': r'(.+?)\s+का\s+(?:अर्थ|मतलब)\s+क्या\s+है',
                'bn': r'(.+?)\s+(?:মানে|অর্থ)\s+কি',
                'te': r'(.+?)\s+అర్ధం\s+ఏమిటి',
                'ta': r'(.+?)\s+(?:பொருள்|அர்த்தம்)\s+என்ன',
                'gu': r'(.+?)\s+(?:અર્થ|મતલબ)\s+શું\s+છે',
                'kn': r'(.+?)\s+ಅರ್ಥ\s+ಏನು',
                'ml': r'(.+?)\s+(?:അർത്ഥം|പൊരുൾ)\s+എന്താണ്',
                'pa': r'(.+?)\s+(?:ਅਰਥ|ਮਤਲਬ)\s+ਕੀ\s+ਹੈ',
                'or': r'(.+?)\s+(?:ଅର୍ଥ|ମାନେ)\s+କଣ'
            },
            'etymology': {
                'en': r'etymology\s+of\s+(.+?)[\?]?$',
                'hi': r'(.+?)\s+की\s+उत्पत्ति',
                'bn': r'(.+?)\s+এর\s+উৎপত্তি',
                'te': r'(.+?)\s+పుట్టుపూర్వోత్తరాలు',
                'ta': r'(.+?)\s+சொற்பிறப்பு',
                'gu': r'(.+?)\s+ની\s+વ્યુત્પત્તિ',
                'kn': r'(.+?)\s+ಪದಾಗಮ',
                'ml': r'(.+?)\s+വ്യുൽപ്പത്തി',
                'pa': r'(.+?)\s+ਦੀ\s+ਉਤਪਤੀ',
                'or': r'(.+?)\s+ର\s+ଉତ୍ପତ୍ତି'
            }
        }
    
    def _detect_script(self, text: str) -> str:
        """
        Detect the dominant script in the text.
        Returns the script with the highest character count.
        """
        # Count characters in each script
        script_counts = {
            script: len(pattern.findall(text))
            for script, pattern in self.script_patterns.items()
        }
        
        # If no Indic scripts found, return 'latin'
        if all(count == 0 for count in script_counts.values()):
            return 'latin'
        
        # Return the script with the most characters
        dominant_script = max(script_counts.items(), key=lambda x: x[1])[0]
        logger.info(f"Detected script: {dominant_script} for text: {text[:50]}...")
        return dominant_script
    
    def _extract_words(self, text: str) -> List[str]:
        """
        Extract potential Sanskrit loanwords from text.
        Handles word boundaries for different scripts.
        """
        # Remove mentions and hashtags
        clean_text = re.sub(r'@\w+|#\w+', '', text)
        
        # Split on whitespace and punctuation
        # Note: This is a simplified approach. For production, we should use
        # language-specific tokenizers for better word boundary detection
        words = re.findall(r'\S+', clean_text)
        return [word.strip() for word in words if word.strip()]
    
    def _identify_query_type(self, text: str, script_type: str) -> Tuple[str, Optional[str]]:
        """
        Identify query type and extract target word/phrase.
        Uses script-specific patterns when available.
        """
        text = text.lower().strip()
        
        # Try patterns for detected script
        for query_type, patterns in self.query_patterns.items():
            # Try script-specific pattern first
            if script_type in patterns:
                match = re.search(patterns[script_type], text)
                if match:
                    return query_type, match.group(1).strip()
            
            # Fallback to English pattern
            match = re.search(patterns['en'], text)
            if match:
                return query_type, match.group(1).strip()
        
        # Default to word lookup if no pattern matches
        return 'word_lookup', None
    
    def parse_query(self, text: str) -> Query:
        """
        Parse the query text and identify potential Sanskrit loanwords.
        Handles multiple scripts and query types.
        """
        clean_text = text.strip()
        script_type = self._detect_script(clean_text)
        words = self._extract_words(clean_text)
        query_type, target = self._identify_query_type(clean_text, script_type)
        
        if target and target not in words:
            words.append(target)
        
        return Query(
            raw_text=clean_text,
            words=words,
            query_type=query_type,
            script_type=script_type
        )
    
    def validate_query(self, query: Query) -> bool:
        """Validate if the query can be processed."""
        return len(query.words) > 0

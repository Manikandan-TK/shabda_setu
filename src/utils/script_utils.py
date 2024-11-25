"""Utility functions for script validation and conversion."""

import re
from typing import Dict, List, Set, Tuple
from enum import Enum

class Script(Enum):
    """Enum for different writing scripts."""
    DEVANAGARI = 'devanagari'
    TAMIL = 'tamil'
    BENGALI = 'bengali'
    TELUGU = 'telugu'
    MALAYALAM = 'malayalam'
    KANNADA = 'kannada'
    LATIN = 'latin'
    IAST = 'iast'

class ScriptUtils:
    """Utility class for script validation and conversion."""
    
    # Script Unicode ranges
    SCRIPT_RANGES = {
        Script.DEVANAGARI: [(0x0900, 0x097F)],  # Devanagari
        Script.TAMIL: [(0x0B80, 0x0BFF)],  # Tamil
        Script.BENGALI: [(0x0980, 0x09FF)],  # Bengali
        Script.TELUGU: [(0x0C00, 0x0C7F)],  # Telugu
        Script.MALAYALAM: [(0x0D00, 0x0D7F)],  # Malayalam
        Script.KANNADA: [(0x0C80, 0x0CFF)],  # Kannada
        Script.LATIN: [(0x0000, 0x007F)],  # Basic Latin
        # Additional ranges for extended Latin characters used in IAST
        Script.IAST: [
            (0x0000, 0x007F),  # Basic Latin
            (0x0100, 0x017F),  # Latin Extended-A
            (0x1E00, 0x1EFF)   # Latin Extended Additional
        ]
    }
    
    # Common diacritical marks and special characters
    DIACRITICS = {
        0x0951: 'udatta',
        0x0952: 'anudatta',
        0x0901: 'candrabindu',
        0x0902: 'anusvara',
        0x0903: 'visarga',
        0x093C: 'nukta',
        0x0943: 'vowel_sign_r',
        0x0944: 'vowel_sign_rr',
        0x094D: 'virama'
    }
    
    # IAST to Devanagari mapping
    IAST_TO_DEVANAGARI = {
        'ā': 'आ', 'ī': 'ई', 'ū': 'ऊ', 'ṛ': 'ऋ', 'ṝ': 'ॠ',
        'ḷ': 'ऌ', 'ḹ': 'ॡ', 'ṃ': 'ं', 'ḥ': 'ः',
        'ś': 'श', 'ṣ': 'ष', 'ñ': 'ञ', 'ṅ': 'ङ', 'ṇ': 'ण',
        'ṭ': 'ट', 'ḍ': 'ड', 'ṛh': 'ऋ', 'ṝh': 'ॠ'
    }
    
    @classmethod
    def get_script(cls, text: str) -> Script:
        """Determine the dominant script of a text.
        
        Args:
            text: Input text
            
        Returns:
            Most likely script of the text
        """
        script_counts = {script: 0 for script in Script}
        
        for char in text:
            char_code = ord(char)
            for script, ranges in cls.SCRIPT_RANGES.items():
                if any(start <= char_code <= end for start, end in ranges):
                    script_counts[script] += 1
                    break
        
        # Get script with highest character count, excluding diacritics
        dominant_script = max(script_counts.items(), key=lambda x: x[1])[0]
        return dominant_script
    
    @classmethod
    def validate_script(cls, text: str, expected_script: Script, 
                       allow_numerals: bool = True, 
                       allow_diacritics: bool = True) -> bool:
        """Validate if text is in the expected script.
        
        Args:
            text: Input text
            expected_script: Expected script of the text
            allow_numerals: Whether to allow Arabic numerals (0-9)
            allow_diacritics: Whether to allow diacritical marks
            
        Returns:
            True if text is in expected script, False otherwise
        """
        for char in text:
            char_code = ord(char)
            
            # Skip whitespace
            if char.isspace():
                continue
                
            # Check numerals
            if char.isnumeric():
                if not allow_numerals:
                    return False
                continue
            
            # Check diacritics
            if char_code in cls.DIACRITICS:
                if not allow_diacritics:
                    return False
                continue
            
            # Check if character is in expected script ranges
            ranges = cls.SCRIPT_RANGES[expected_script]
            if not any(start <= char_code <= end for start, end in ranges):
                return False
        
        return True
    
    @classmethod
    def convert_iast_to_devanagari(cls, text: str) -> str:
        """Convert IAST (International Alphabet of Sanskrit Transliteration) to Devanagari.
        
        Args:
            text: Input text in IAST
            
        Returns:
            Text converted to Devanagari
        """
        # First, replace multi-character combinations
        text = text.replace('ṛh', 'ऋ').replace('ṝh', 'ॠ')
        
        # Then replace single characters
        for iast, dev in cls.IAST_TO_DEVANAGARI.items():
            text = text.replace(iast, dev)
        
        return text
    
    @classmethod
    def clean_text(cls, text: str, script: Script) -> str:
        """Clean text by removing invalid characters for a given script.
        
        Args:
            text: Input text
            script: Target script
            
        Returns:
            Cleaned text containing only valid characters for the script
        """
        cleaned = []
        for char in text:
            char_code = ord(char)
            
            # Always keep whitespace
            if char.isspace():
                cleaned.append(char)
                continue
            
            # Keep diacritics
            if char_code in cls.DIACRITICS:
                cleaned.append(char)
                continue
            
            # Keep characters in script range
            ranges = cls.SCRIPT_RANGES[script]
            if any(start <= char_code <= end for start, end in ranges):
                cleaned.append(char)
        
        return ''.join(cleaned)

    @classmethod
    def contains_script(cls, text: str, script: Script) -> bool:
        """Check if text contains any characters from a specific script.
        
        Args:
            text: Input text
            script: Script to check for
            
        Returns:
            True if text contains any characters from the script
        """
        ranges = cls.SCRIPT_RANGES[script]
        return any(
            any(start <= ord(char) <= end for start, end in ranges)
            for char in text
        )

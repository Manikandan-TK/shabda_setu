from typing import Dict, Optional, Tuple
import json
import logging
from pathlib import Path
import sqlite3
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DictionaryEntry:
    word: str
    sanskrit_root: str
    meaning: str
    source: str  # Which dictionary this came from
    confidence: float = 1.0  # Dictionary entries have high confidence by default

class DictionaryHandler:
    def __init__(self, db_path: str = "data/dictionaries/sanskrit_dict.db"):
        """
        Initialize dictionary handler with SQLite database containing merged dictionary data.
        
        The database contains entries from:
        - Monier-Williams Sanskrit Dictionary
        - Apte Sanskrit Dictionary
        - Cologne Digital Sanskrit Dictionary
        - Shabdanjali Sanskrit-Hindi Dictionary
        - IndoWordNet
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dictionary_entries (
                    word TEXT NOT NULL,
                    sanskrit_root TEXT,
                    meaning TEXT,
                    source TEXT,
                    script TEXT,
                    PRIMARY KEY (word, source)
                )
            """)
            
            # Create indices for faster lookup
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_word ON dictionary_entries(word)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_root ON dictionary_entries(sanskrit_root)")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing dictionary database: {e}")
            raise
    
    def lookup_word(self, word: str, script_type: str) -> Optional[DictionaryEntry]:
        """
        Look up a word in the merged dictionary database.
        Returns the most reliable entry if found in multiple dictionaries.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query all matching entries
            cursor.execute("""
                SELECT word, sanskrit_root, meaning, source 
                FROM dictionary_entries 
                WHERE word = ? AND script = ?
            """, (word.lower(), script_type))
            
            entries = cursor.fetchall()
            conn.close()
            
            if not entries:
                return None
            
            # Dictionary source reliability weights
            source_weights = {
                'monier_williams': 1.0,
                'cologne': 0.95,
                'apte': 0.9,
                'shabdanjali': 0.85,
                'indowordnet': 0.8
            }
            
            # Get the entry from the most reliable source
            best_entry = max(entries, key=lambda x: source_weights.get(x[3], 0.5))
            
            return DictionaryEntry(
                word=best_entry[0],
                sanskrit_root=best_entry[1],
                meaning=best_entry[2],
                source=best_entry[3]
            )
            
        except Exception as e:
            logger.error(f"Error looking up word in dictionary: {e}")
            return None
    
    def add_entry(self, entry: DictionaryEntry, script_type: str):
        """Add a new entry to the dictionary database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO dictionary_entries 
                (word, sanskrit_root, meaning, source, script)
                VALUES (?, ?, ?, ?, ?)
            """, (
                entry.word.lower(),
                entry.sanskrit_root,
                entry.meaning,
                entry.source,
                script_type
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error adding dictionary entry: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about the dictionary database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total entries
            cursor.execute("SELECT COUNT(*) FROM dictionary_entries")
            total = cursor.fetchone()[0]
            
            # Get entries by source
            cursor.execute("""
                SELECT source, COUNT(*) 
                FROM dictionary_entries 
                GROUP BY source
            """)
            by_source = dict(cursor.fetchall())
            
            # Get entries by script
            cursor.execute("""
                SELECT script, COUNT(*) 
                FROM dictionary_entries 
                GROUP BY script
            """)
            by_script = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_entries': total,
                'by_source': by_source,
                'by_script': by_script
            }
            
        except Exception as e:
            logger.error(f"Error getting dictionary statistics: {e}")
            return {}

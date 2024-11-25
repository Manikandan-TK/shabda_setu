"""
Core database operations for Shabda Setu.
Provides a clean interface for database interactions with proper error handling.
"""

import sqlite3
from pathlib import Path
import logging
from typing import Dict, List, Optional, Union, Any
import json
from contextlib import contextmanager
import sys

# Add project root to Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass

class Database:
    def __init__(self, db_path: Union[str, Path], is_staging: bool = False):
        """Initialize database connection."""
        self.db_path = Path(db_path)
        self.is_staging = is_staging
        
        if not self.db_path.exists():
            raise DatabaseError(f"Database file not found: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            # Enable foreign key support
            conn.execute('PRAGMA foreign_keys = ON')
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Failed to connect to database: {e}")
        finally:
            if conn:
                conn.close()

    def add_word(self, word: str, language: str, script: str, romanized: str, 
                meaning: Optional[str] = None) -> int:
        """Add a new word to the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if word exists
                cursor.execute('''
                    SELECT id FROM words 
                    WHERE word = ? AND language = ?
                ''', (word, language))
                
                existing = cursor.fetchone()
                if existing:
                    logger.warning(f"Word already exists: {word} in {language}")
                    return existing['id']
                
                # If word doesn't exist, insert it
                cursor.execute('''
                    INSERT INTO words (word, language, script, romanized, meaning)
                    VALUES (?, ?, ?, ?, ?)
                ''', (word, language, script, romanized, meaning))
                conn.commit()
                return cursor.lastrowid
                
        except sqlite3.Error as e:
            logger.error(f"Error adding word: {e}")
            raise DatabaseError(f"Failed to add word: {e}")

    def add_etymology(self, word_id: int, sanskrit_root: str) -> int:
        """Add etymology information for a word."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO etymologies (word_id, sanskrit_root)
                    VALUES (?, ?)
                ''', (word_id, sanskrit_root))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error adding etymology: {e}")
            raise DatabaseError(f"Failed to add etymology: {e}")

    def add_verification(self, word_id: int, llm_name: str, 
                        confidence_score: float, verification_data: Dict) -> int:
        """Add a verification record for a word."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO verifications 
                    (word_id, llm_name, confidence_score, verification_data)
                    VALUES (?, ?, ?, ?)
                ''', (word_id, llm_name, confidence_score, json.dumps(verification_data)))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error adding verification: {e}")
            raise DatabaseError(f"Failed to add verification: {e}")

    def get_word_by_text(self, word: str, language: str) -> Optional[Dict]:
        """Retrieve a word's information by its text and language."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT w.*, e.sanskrit_root, 
                           GROUP_CONCAT(v.llm_name) as verifying_llms,
                           AVG(v.confidence_score) as avg_confidence
                    FROM words w
                    LEFT JOIN etymologies e ON w.id = e.word_id
                    LEFT JOIN verifications v ON w.id = v.word_id
                    WHERE w.word = ? AND w.language = ?
                    GROUP BY w.id
                ''', (word, language))
                result = cursor.fetchone()
                return dict(result) if result else None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving word: {e}")
            raise DatabaseError(f"Failed to retrieve word: {e}")

    def get_high_confidence_words(self, min_confidence: float = 0.8) -> List[Dict]:
        """Retrieve words with high confidence scores for model training."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT w.*, e.sanskrit_root, 
                           AVG(v.confidence_score) as avg_confidence,
                           COUNT(DISTINCT v.llm_name) as verification_count
                    FROM words w
                    JOIN etymologies e ON w.id = e.word_id
                    JOIN verifications v ON w.id = v.word_id
                    GROUP BY w.id
                    HAVING avg_confidence >= ?
                ''', (min_confidence,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error retrieving high confidence words: {e}")
            raise DatabaseError(f"Failed to retrieve high confidence words: {e}")

    def update_confidence_score(self, word_id: int, new_score: float) -> None:
        """Update the confidence score for a word."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE words 
                    SET confidence_score = ?
                    WHERE id = ?
                ''', (new_score, word_id))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error updating confidence score: {e}")
            raise DatabaseError(f"Failed to update confidence score: {e}")

    def promote_to_main(self, word_id: int) -> None:
        """Promote a word from staging to main database."""
        if not self.is_staging:
            raise DatabaseError("Can only promote from staging database")
        
        try:
            # Implementation of staging to main promotion
            # This would involve copying the word and its related data
            # to the main database
            pass
        except sqlite3.Error as e:
            logger.error(f"Error promoting word: {e}")
            raise DatabaseError(f"Failed to promote word: {e}")

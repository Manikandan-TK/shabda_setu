"""
Test suite for database operations.
Tests both main and staging databases with sample Sanskrit loanwords.
"""

import unittest
from pathlib import Path
import sys
import json
import sqlite3

# Add project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from src.core.database import Database, DatabaseError

class TestDatabase(unittest.TestCase):
    def _clean_database(self, db_path: Path) -> None:
        """Clean up the database by dropping and recreating tables."""
        if not db_path.exists():
            return
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Drop existing tables
        cursor.execute("DROP TABLE IF EXISTS verifications")
        cursor.execute("DROP TABLE IF EXISTS etymologies")
        cursor.execute("DROP TABLE IF EXISTS words")
        
        # Recreate tables
        cursor.execute('''
            CREATE TABLE words (
                id INTEGER PRIMARY KEY,
                word TEXT NOT NULL,
                language TEXT NOT NULL,
                script TEXT NOT NULL,
                romanized TEXT NOT NULL,
                meaning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence_score FLOAT DEFAULT 0.0,
                UNIQUE(word, language)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE etymologies (
                id INTEGER PRIMARY KEY,
                word_id INTEGER,
                sanskrit_root TEXT NOT NULL,
                verification_count INTEGER DEFAULT 0,
                confidence_score FLOAT DEFAULT 0.0,
                FOREIGN KEY(word_id) REFERENCES words(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE verifications (
                id INTEGER PRIMARY KEY,
                word_id INTEGER,
                llm_name TEXT NOT NULL,
                confidence_score FLOAT NOT NULL,
                verification_data JSON,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(word_id) REFERENCES words(id)
            )
        ''')
        
        # Recreate indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS words_language_idx ON words(language)')
        cursor.execute('CREATE INDEX IF NOT EXISTS words_confidence_idx ON words(confidence_score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS etymologies_root_idx ON etymologies(sanskrit_root)')
        cursor.execute('CREATE INDEX IF NOT EXISTS verifications_llm_idx ON verifications(llm_name)')
        
        conn.commit()
        conn.close()

    def setUp(self):
        """Set up test databases."""
        self.main_db_path = project_root / 'data' / 'database' / 'main.db'
        self.staging_db_path = project_root / 'data' / 'database' / 'staging.db'
        
        # Clean up existing databases
        self._clean_database(self.main_db_path)
        self._clean_database(self.staging_db_path)
        
        self.main_db = Database(self.main_db_path, is_staging=False)
        self.staging_db = Database(self.staging_db_path, is_staging=True)
        
        # Sample test data (Tamil words with Sanskrit origins)
        self.test_words = [
            {
                'word': 'மனிதன்',
                'language': 'tamil',
                'script': 'tamil',
                'romanized': 'manitan',
                'meaning': 'human',
                'sanskrit_root': 'मनुष्य',
                'verifications': [
                    {
                        'llm_name': 'gpt-4',
                        'confidence': 0.95,
                        'data': {
                            'etymology': 'From Sanskrit मनुष्य (manuṣya)',
                            'usage': 'Common in modern Tamil'
                        }
                    },
                    {
                        'llm_name': 'claude',
                        'confidence': 0.92,
                        'data': {
                            'etymology': 'Derived from Sanskrit मनुष्य (manuṣya)',
                            'certainty': 'high'
                        }
                    }
                ]
            },
            {
                'word': 'ராஜா',
                'language': 'tamil',
                'script': 'tamil',
                'romanized': 'raja',
                'meaning': 'king',
                'sanskrit_root': 'राज',
                'verifications': [
                    {
                        'llm_name': 'gpt-4',
                        'confidence': 0.98,
                        'data': {
                            'etymology': 'From Sanskrit राज (rāja)',
                            'usage': 'Widely used across Indian languages'
                        }
                    }
                ]
            }
        ]

    def tearDown(self):
        """Clean up after tests."""
        self._clean_database(self.main_db_path)
        self._clean_database(self.staging_db_path)

    def test_add_word(self):
        """Test adding a new word."""
        word_data = self.test_words[0]
        word_id = self.main_db.add_word(
            word_data['word'],
            word_data['language'],
            word_data['script'],
            word_data['romanized'],
            word_data['meaning']
        )
        self.assertIsNotNone(word_id)
        
        # Test duplicate word handling
        duplicate_id = self.main_db.add_word(
            word_data['word'],
            word_data['language'],
            word_data['script'],
            word_data['romanized'],
            word_data['meaning']
        )
        self.assertEqual(word_id, duplicate_id)

    def test_add_etymology(self):
        """Test adding etymology information."""
        word_data = self.test_words[0]
        word_id = self.main_db.add_word(
            word_data['word'],
            word_data['language'],
            word_data['script'],
            word_data['romanized'],
            word_data['meaning']
        )
        
        etymology_id = self.main_db.add_etymology(
            word_id,
            word_data['sanskrit_root']
        )
        self.assertIsNotNone(etymology_id)

    def test_add_verification(self):
        """Test adding verification records."""
        word_data = self.test_words[0]
        word_id = self.main_db.add_word(
            word_data['word'],
            word_data['language'],
            word_data['script'],
            word_data['romanized'],
            word_data['meaning']
        )
        
        for verification in word_data['verifications']:
            verification_id = self.main_db.add_verification(
                word_id,
                verification['llm_name'],
                verification['confidence'],
                verification['data']
            )
            self.assertIsNotNone(verification_id)

    def test_get_word(self):
        """Test retrieving word information."""
        # First add a complete word with etymology and verifications
        word_data = self.test_words[0]
        word_id = self.main_db.add_word(
            word_data['word'],
            word_data['language'],
            word_data['script'],
            word_data['romanized'],
            word_data['meaning']
        )
        
        self.main_db.add_etymology(word_id, word_data['sanskrit_root'])
        
        for verification in word_data['verifications']:
            self.main_db.add_verification(
                word_id,
                verification['llm_name'],
                verification['confidence'],
                verification['data']
            )
        
        # Now retrieve and verify
        retrieved = self.main_db.get_word_by_text(
            word_data['word'],
            word_data['language']
        )
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['word'], word_data['word'])
        self.assertEqual(retrieved['language'], word_data['language'])
        self.assertEqual(retrieved['sanskrit_root'], word_data['sanskrit_root'])
        
        # Verify the average confidence score
        confidences = [v['confidence'] for v in word_data['verifications']]
        expected_avg = sum(confidences) / len(confidences)
        self.assertAlmostEqual(float(retrieved['avg_confidence']), expected_avg, places=2)

    def test_get_high_confidence_words(self):
        """Test retrieving high confidence words."""
        # Add both test words with their etymologies and verifications
        for word_data in self.test_words:
            word_id = self.main_db.add_word(
                word_data['word'],
                word_data['language'],
                word_data['script'],
                word_data['romanized'],
                word_data['meaning']
            )
            
            self.main_db.add_etymology(word_id, word_data['sanskrit_root'])
            
            for verification in word_data['verifications']:
                self.main_db.add_verification(
                    word_id,
                    verification['llm_name'],
                    verification['confidence'],
                    verification['data']
                )
        
        # Get high confidence words
        high_confidence = self.main_db.get_high_confidence_words(min_confidence=0.9)
        self.assertTrue(len(high_confidence) > 0)
        
        # All returned words should have confidence >= 0.9
        for word in high_confidence:
            self.assertGreaterEqual(float(word['avg_confidence']), 0.9)

    def test_update_confidence(self):
        """Test updating confidence scores."""
        word_data = self.test_words[0]
        word_id = self.main_db.add_word(
            word_data['word'],
            word_data['language'],
            word_data['script'],
            word_data['romanized'],
            word_data['meaning']
        )
        
        new_confidence = 0.99
        self.main_db.update_confidence_score(word_id, new_confidence)
        
        retrieved = self.main_db.get_word_by_text(
            word_data['word'],
            word_data['language']
        )
        self.assertEqual(float(retrieved['confidence_score']), new_confidence)

if __name__ == '__main__':
    unittest.main()

"""
Database initialization script for Shabda Setu.
Creates both main and staging databases with proper schemas.
"""

import sqlite3
import os
import logging
from pathlib import Path
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

# Database paths
DB_DIR = project_root / 'data' / 'database'
MAIN_DB = DB_DIR / 'main.db'
STAGING_DB = DB_DIR / 'staging.db'

# Schema definitions
SCHEMA = {
    'words': '''
        CREATE TABLE IF NOT EXISTS words (
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
    ''',
    
    'etymologies': '''
        CREATE TABLE IF NOT EXISTS etymologies (
            id INTEGER PRIMARY KEY,
            word_id INTEGER,
            sanskrit_root TEXT NOT NULL,
            verification_count INTEGER DEFAULT 0,
            confidence_score FLOAT DEFAULT 0.0,
            FOREIGN KEY(word_id) REFERENCES words(id)
        )
    ''',
    
    'verifications': '''
        CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY,
            word_id INTEGER,
            llm_name TEXT NOT NULL,
            confidence_score FLOAT NOT NULL,
            verification_data JSON,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(word_id) REFERENCES words(id)
        )
    '''
}

# Indexes for performance optimization
INDEXES = {
    'words_language_idx': 'CREATE INDEX IF NOT EXISTS words_language_idx ON words(language)',
    'words_confidence_idx': 'CREATE INDEX IF NOT EXISTS words_confidence_idx ON words(confidence_score)',
    'etymologies_root_idx': 'CREATE INDEX IF NOT EXISTS etymologies_root_idx ON etymologies(sanskrit_root)',
    'verifications_llm_idx': 'CREATE INDEX IF NOT EXISTS verifications_llm_idx ON verifications(llm_name)'
}

def init_database(db_path: Path) -> None:
    """Initialize a database with the schema."""
    try:
        # Ensure the database directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign key support
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # Create tables
        for table_name, create_table_sql in SCHEMA.items():
            logger.info(f"Creating table: {table_name}")
            cursor.execute(create_table_sql)
        
        # Create indexes
        for index_name, create_index_sql in INDEXES.items():
            logger.info(f"Creating index: {index_name}")
            cursor.execute(create_index_sql)
        
        conn.commit()
        logger.info(f"Successfully initialized database: {db_path}")
        
    except sqlite3.Error as e:
        logger.error(f"Error initializing database {db_path}: {e}")
        raise
    finally:
        if conn:
            conn.close()

def main():
    """Initialize both main and staging databases."""
    try:
        # Initialize main database
        logger.info("Initializing main database...")
        init_database(MAIN_DB)
        
        # Initialize staging database
        logger.info("Initializing staging database...")
        init_database(STAGING_DB)
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize databases: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

"""Script to collect dictionary data for all supported languages."""

import os
import sys
import sqlite3
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from src.core.database import Database
from src.data.data_collection import DataCollector

def init_database(db_path: Path):
    """Initialize the database with required tables."""
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            language TEXT NOT NULL,
            sanskrit_root TEXT,
            confidence REAL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(word, language)
        )
    ''')
    
    conn.commit()
    conn.close()

def main():
    # Initialize database
    db_path = project_root / "data" / "dictionary_data.db"
    init_database(db_path)
    db = Database(str(db_path))
    
    # Create data directory if it doesn't exist
    cache_dir = project_root / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize collector with all languages and scrapers
    collector = DataCollector(db)
    
    # Start collection
    print("Starting dictionary data collection for all languages...")
    collector.collect_and_store(cache_dir=str(cache_dir))
    print("Data collection completed!")

if __name__ == "__main__":
    main()

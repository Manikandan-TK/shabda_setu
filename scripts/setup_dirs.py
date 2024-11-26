"""Create necessary directories for data collection."""

import os
from pathlib import Path

def setup_directories():
    project_root = Path(__file__).parent.parent.absolute()
    
    # Create directories
    directories = [
        project_root / "data" / "cache",
        project_root / "data" / "logs",
        project_root / "data" / "db"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

if __name__ == "__main__":
    setup_directories()

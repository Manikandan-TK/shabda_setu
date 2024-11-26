"""Script to update logging configuration in all scraper files."""

import os
import re

def update_scraper_logging(file_path: str):
    """Update the logging configuration in a scraper file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace old logging imports and setup
    old_patterns = [
        r'import logging\n',
        r'logger = logging\.getLogger\(__name__\)\n',
    ]
    
    new_imports = 'from config.logging_config import setup_logging\n'
    new_logger = f'logger = setup_logging("{os.path.basename(file_path).replace("_scraper.py", "")}")\n'
    
    for pattern in old_patterns:
        content = re.sub(pattern, '', content)
    
    # Add new imports after other imports
    import_section_end = content.rindex('import') + content[content.rindex('import'):].index('\n') + 1
    content = content[:import_section_end] + new_imports + content[import_section_end:]
    
    # Add logger setup after imports but before class definition
    class_start = content.index('class')
    content = content[:class_start] + '\n' + new_logger + content[class_start:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    """Update all scraper files."""
    scrapers_dir = os.path.join('src', 'data', 'scrapers')
    for filename in os.listdir(scrapers_dir):
        if filename.endswith('_scraper.py'):
            file_path = os.path.join(scrapers_dir, filename)
            print(f"Updating {filename}...")
            update_scraper_logging(file_path)
    print("Done updating scraper files!")

if __name__ == '__main__':
    main()

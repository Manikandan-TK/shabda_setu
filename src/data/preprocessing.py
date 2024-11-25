import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Union
import yaml
from sklearn.model_selection import train_test_split
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataPreprocessor:
    def __init__(self, config_path: str):
        """
        Initialize the data preprocessor with configuration.
        
        Args:
            config_path (str): Path to the configuration file
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.supported_languages = self.config['data']['languages']

    def load_raw_data(self, data_dir: str) -> List[Dict]:
        """
        Load raw data from various sources.
        
        Args:
            data_dir (str): Directory containing raw data files
        Returns:
            List[Dict]: List of text samples with annotations
        """
        data = []
        data_path = Path(data_dir)
        
        for lang in self.supported_languages:
            lang_path = data_path / lang
            if not lang_path.exists():
                logger.warning(f"No data found for language: {lang}")
                continue
            
            # Load text files
            for text_file in lang_path.glob("*.txt"):
                with open(text_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                    
                # Load corresponding annotations if they exist
                ann_file = text_file.with_suffix('.json')
                if ann_file.exists():
                    with open(ann_file, 'r', encoding='utf-8') as f:
                        annotations = json.load(f)
                else:
                    annotations = []
                
                data.append({
                    'text': text,
                    'annotations': annotations,
                    'language': lang,
                    'source': text_file.name
                })
        
        return data

    def tokenize_and_label(self, text: str, annotations: List[Dict]) -> Dict:
        """
        Tokenize text and create word-level labels.
        
        Args:
            text (str): Input text
            annotations (List[Dict]): List of Sanskrit loanword annotations
        Returns:
            Dict: Dictionary containing tokens and labels
        """
        # Simple word tokenization (can be improved with language-specific tokenizers)
        words = text.split()
        
        # Create labels (0: not Sanskrit, 1: Sanskrit)
        labels = [0] * len(words)
        
        # Mark Sanskrit loanwords
        for ann in annotations:
            start_idx = ann['start_word']
            end_idx = ann['end_word']
            for i in range(start_idx, end_idx + 1):
                if i < len(labels):
                    labels[i] = 1
        
        return {
            'tokens': words,
            'labels': labels
        }

    def create_dataset(self, raw_data: List[Dict]) -> pd.DataFrame:
        """
        Create a structured dataset from raw data.
        
        Args:
            raw_data (List[Dict]): List of raw data samples
        Returns:
            pd.DataFrame: Processed dataset
        """
        processed_data = []
        
        for sample in raw_data:
            tokenized = self.tokenize_and_label(
                sample['text'],
                sample['annotations']
            )
            
            processed_data.append({
                'text': tokenized['tokens'],
                'labels': tokenized['labels'],
                'language': sample['language'],
                'source': sample['source']
            })
        
        return pd.DataFrame(processed_data)

    def split_dataset(self, df: pd.DataFrame, 
                     train_size: float = 0.8,
                     val_size: float = 0.1) -> Dict[str, pd.DataFrame]:
        """
        Split dataset into train, validation, and test sets.
        
        Args:
            df (pd.DataFrame): Input dataset
            train_size (float): Proportion of training data
            val_size (float): Proportion of validation data
        Returns:
            Dict[str, pd.DataFrame]: Dictionary containing split datasets
        """
        # First split: train + val and test
        train_val, test = train_test_split(
            df,
            train_size=train_size + val_size,
            random_state=self.config['training']['seed']
        )
        
        # Second split: train and val
        relative_val_size = val_size / (train_size + val_size)
        train, val = train_test_split(
            train_val,
            test_size=relative_val_size,
            random_state=self.config['training']['seed']
        )
        
        return {
            'train': train,
            'val': val,
            'test': test
        }

    def save_datasets(self, datasets: Dict[str, pd.DataFrame], output_dir: str):
        """
        Save processed datasets to disk.
        
        Args:
            datasets (Dict[str, pd.DataFrame]): Dictionary of datasets
            output_dir (str): Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for split_name, df in datasets.items():
            output_file = output_path / f"{split_name}.json"
            df.to_json(output_file, orient='records', lines=True)
            logger.info(f"Saved {split_name} dataset to {output_file}")

def main():
    """Main function to run the preprocessing pipeline."""
    config_path = "config/config.yaml"
    preprocessor = DataPreprocessor(config_path)
    
    # Load raw data
    raw_data = preprocessor.load_raw_data("data/raw")
    
    # Create dataset
    df = preprocessor.create_dataset(raw_data)
    
    # Split dataset
    datasets = preprocessor.split_dataset(df)
    
    # Save processed datasets
    preprocessor.save_datasets(datasets, "data/processed")

if __name__ == "__main__":
    main()

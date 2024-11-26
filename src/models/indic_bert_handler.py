from typing import Optional, Dict, List, Tuple
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class IndicBertHandler:
    def __init__(self, model_path: str, tokenizer_path: str, labels_path: str):
        """
        Initialize the IndicBERT handler with paths to the fine-tuned model and tokenizer.
        
        Args:
            model_path: Path to the fine-tuned model
            tokenizer_path: Path to the tokenizer
            labels_path: Path to the labels JSON file containing Sanskrit roots and meanings
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        try:
            # Load the fine-tuned model
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
            self.model.to(self.device)
            self.model.eval()
            
            # Load the tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
            
            # Load Sanskrit roots and meanings
            with open(labels_path, 'r', encoding='utf-8') as f:
                self.labels = json.load(f)
            
            logger.info("Successfully loaded IndicBERT model, tokenizer, and labels")
            
        except Exception as e:
            logger.error(f"Error loading IndicBERT components: {e}")
            raise
    
    def predict(self, word: str, script_type: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Predict if a word is a Sanskrit loanword and return its root and meaning.
        
        Args:
            word: The word to analyze
            script_type: The script type of the word (devanagari, tamil, etc.)
            
        Returns:
            Tuple containing:
            - Sanskrit root (if found, else None)
            - Meaning (if found, else None)
            - Confidence score (0 to 1)
        """
        try:
            # Prepare input
            inputs = self.tokenizer(
                word,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128
            ).to(self.device)
            
            # Get model prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
                confidence, predicted_class = torch.max(probabilities, dim=-1)
                
                # Convert to Python scalars
                confidence = confidence.item()
                predicted_class = predicted_class.item()
            
            # Get Sanskrit root and meaning if prediction is positive
            if predicted_class == 1 and confidence > 0.5:  # Assuming 1 is the positive class
                # Look up the word in our labels
                word_info = self.labels.get(word.lower(), {})
                sanskrit_root = word_info.get('root')
                meaning = word_info.get('meaning')
                return sanskrit_root, meaning, confidence
            
            return None, None, confidence
            
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            return None, None, 0.0
    
    @staticmethod
    def prepare_training_data(words_file: str, output_file: str):
        """
        Prepare training data for fine-tuning IndicBERT.
        This method should be used in the Colab notebook.
        
        Args:
            words_file: Path to JSON file containing words and their Sanskrit origins
            output_file: Path to save the prepared dataset
        """
        try:
            # Load words data
            with open(words_file, 'r', encoding='utf-8') as f:
                words_data = json.load(f)
            
            # Prepare dataset in the format expected by transformers
            dataset = []
            for word, info in words_data.items():
                is_sanskrit = 1 if info.get('is_sanskrit', False) else 0
                example = {
                    'text': word,
                    'label': is_sanskrit,
                    'sanskrit_root': info.get('root', ''),
                    'meaning': info.get('meaning', '')
                }
                dataset.append(example)
            
            # Save prepared dataset
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully prepared training data: {len(dataset)} examples")
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            raise

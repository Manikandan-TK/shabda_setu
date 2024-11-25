import os
import torch
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification
)
from datasets import load_dataset
import numpy as np
from sklearn.metrics import precision_recall_fscore_support
import wandb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SanskritLoanwordDetector:
    def __init__(self, model_name="ai4bharat/indic-bert", num_labels=2):
        """
        Initialize the Sanskrit loanword detector with a pre-trained model.
        
        Args:
            model_name (str): Name of the pre-trained model to use
            num_labels (int): Number of labels (2 for binary classification)
        """
        self.model_name = model_name
        self.num_labels = num_labels
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            model_name,
            num_labels=num_labels
        )
        
        # Move model to appropriate device
        self.model.to(self.device)

    def prepare_dataset(self, dataset_path):
        """
        Prepare the dataset for training.
        
        Args:
            dataset_path (str): Path to the dataset
        Returns:
            datasets.Dataset: Processed dataset
        """
        # Load and preprocess the dataset
        # This is a placeholder - implement actual data loading logic
        dataset = load_dataset("json", data_files=dataset_path)
        
        def tokenize_and_align_labels(examples):
            tokenized_inputs = self.tokenizer(
                examples["text"],
                truncation=True,
                padding=True,
                max_length=512,
                is_split_into_words=True
            )
            
            labels = []
            for i, label in enumerate(examples["labels"]):
                word_ids = tokenized_inputs.word_ids(batch_index=i)
                previous_word_idx = None
                label_ids = []
                
                for word_idx in word_ids:
                    if word_idx is None:
                        label_ids.append(-100)
                    elif word_idx != previous_word_idx:
                        label_ids.append(label[word_idx])
                    else:
                        label_ids.append(-100)
                    previous_word_idx = word_idx
                
                labels.append(label_ids)
            
            tokenized_inputs["labels"] = labels
            return tokenized_inputs
        
        # Process dataset
        processed_dataset = dataset.map(
            tokenize_and_align_labels,
            batched=True,
            remove_columns=dataset["train"].column_names
        )
        
        return processed_dataset

    def compute_metrics(self, pred):
        """
        Compute metrics for evaluation.
        
        Args:
            pred: Prediction outputs from the model
        Returns:
            dict: Dictionary containing computed metrics
        """
        labels = pred.label_ids
        preds = pred.predictions.argmax(-1)
        
        # Flatten the arrays and remove padding (-100)
        true_labels = labels.flatten()
        true_predictions = preds.flatten()
        mask = true_labels != -100
        
        true_labels = true_labels[mask]
        true_predictions = true_predictions[mask]
        
        precision, recall, f1, _ = precision_recall_fscore_support(
            true_labels,
            true_predictions,
            average='binary'
        )
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

    def train(self, train_dataset, eval_dataset, output_dir="./models"):
        """
        Fine-tune the model on the provided dataset.
        
        Args:
            train_dataset: Training dataset
            eval_dataset: Evaluation dataset
            output_dir (str): Directory to save the model
        """
        training_args = TrainingArguments(
            output_dir=output_dir,
            evaluation_strategy="epoch",
            learning_rate=2e-5,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            num_train_epochs=3,
            weight_decay=0.01,
            report_to="wandb",
            logging_dir="./logs",
        )
        
        data_collator = DataCollatorForTokenClassification(self.tokenizer)
        
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
            tokenizer=self.tokenizer,
            compute_metrics=self.compute_metrics
        )
        
        # Start training
        trainer.train()
        
        # Save the model
        trainer.save_model()
        self.tokenizer.save_pretrained(output_dir)

    def predict(self, text):
        """
        Predict Sanskrit loanwords in the given text.
        
        Args:
            text (str): Input text
        Returns:
            list: List of identified Sanskrit loanwords with their probabilities
        """
        # Tokenize input
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True
        ).to(self.device)
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.softmax(outputs.logits, dim=-1)
        
        # Process predictions
        word_predictions = []
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        
        for token, pred in zip(tokens, predictions[0]):
            if token.startswith("##"):
                continue
            if pred[1] > 0.5:  # Threshold for loanword detection
                word_predictions.append({
                    "word": token,
                    "probability": float(pred[1])
                })
        
        return word_predictions

def main():
    # Initialize wandb
    wandb.init(project="sanskrit-loanword-detection")
    
    # Initialize model
    detector = SanskritLoanwordDetector()
    
    # Prepare dataset
    dataset = detector.prepare_dataset("path/to/your/dataset")
    
    # Split dataset
    train_dataset = dataset["train"]
    eval_dataset = dataset["validation"]
    
    # Train model
    detector.train(train_dataset, eval_dataset)
    
    # Test prediction
    test_text = "Your test text here"
    predictions = detector.predict(test_text)
    print("Predictions:", predictions)

if __name__ == "__main__":
    main()

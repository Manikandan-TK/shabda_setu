"""Module for reconciling conflicting word information from different sources."""

from typing import List, Dict, Optional
import logging
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class WordEntry:
    """Represents a word entry from a dictionary source."""
    word: str
    sanskrit_word: str
    language: str
    confidence: float
    source_url: str
    source_name: str
    context: Dict = None
    meanings: List[str] = None
    usage_examples: List[str] = None

class WordReconciliation:
    """Handles reconciliation of conflicting word information from different sources."""
    
    def __init__(self, confidence_threshold: float = 0.7):
        """Initialize the reconciliation system.
        
        Args:
            confidence_threshold: Minimum confidence score to consider an entry reliable
        """
        self.confidence_threshold = confidence_threshold
        
    def _group_entries(self, entries: List[WordEntry]) -> Dict[str, List[WordEntry]]:
        """Group entries by their Sanskrit word and target language word pair.
        
        Args:
            entries: List of word entries from different sources
            
        Returns:
            Dictionary mapping (sanskrit_word, word) pairs to their entries
        """
        grouped = defaultdict(list)
        for entry in entries:
            key = (entry.sanskrit_word, entry.word, entry.language)
            grouped[key].append(entry)
        return grouped
    
    def _calculate_agreement_score(self, entries: List[WordEntry]) -> float:
        """Calculate agreement score between different sources.
        
        Args:
            entries: List of entries for the same word pair
            
        Returns:
            Agreement score between 0 and 1
        """
        if len(entries) <= 1:
            return 1.0
            
        # Weight sources by their confidence
        total_weight = sum(entry.confidence for entry in entries)
        agreement_score = total_weight / (len(entries) * max(entry.confidence for entry in entries))
        
        return agreement_score
    
    def _merge_entries(self, entries: List[WordEntry]) -> WordEntry:
        """Merge multiple entries for the same word pair.
        
        Args:
            entries: List of entries to merge
            
        Returns:
            Merged word entry
        """
        # Sort by confidence
        entries.sort(key=lambda x: x.confidence, reverse=True)
        primary = entries[0]
        
        # Combine meanings and examples if available
        all_meanings = set()
        all_examples = set()
        
        for entry in entries:
            if entry.meanings:
                all_meanings.update(entry.meanings)
            if entry.usage_examples:
                all_examples.update(entry.usage_examples)
        
        # Calculate combined confidence
        agreement = self._calculate_agreement_score(entries)
        combined_confidence = min(1.0, primary.confidence * (1 + 0.1 * agreement * (len(entries) - 1)))
        
        # Create merged entry
        return WordEntry(
            word=primary.word,
            sanskrit_word=primary.sanskrit_word,
            language=primary.language,
            confidence=combined_confidence,
            source_url=primary.source_url,
            source_name=f"{primary.source_name} + {len(entries)-1} more",
            meanings=list(all_meanings) if all_meanings else None,
            usage_examples=list(all_examples) if all_examples else None,
            context={
                'agreement_score': agreement,
                'source_count': len(entries),
                'sources': [e.source_name for e in entries]
            }
        )
    
    def reconcile(self, entries: List[Dict]) -> List[Dict]:
        """Reconcile potentially conflicting word entries.
        
        Args:
            entries: List of word entries from different sources
            
        Returns:
            List of reconciled word entries
        """
        # Convert dictionaries to WordEntry objects
        word_entries = []
        for entry in entries:
            try:
                word_entries.append(WordEntry(
                    word=entry['word'],
                    sanskrit_word=entry['sanskrit_word'],
                    language=entry['language'],
                    confidence=entry['confidence'],
                    source_url=entry['source_url'],
                    source_name=entry['context']['source'],
                    meanings=entry.get('meanings'),
                    usage_examples=entry.get('usage_examples'),
                    context=entry.get('context')
                ))
            except KeyError as e:
                logger.warning(f"Skipping malformed entry, missing field: {e}")
                continue
        
        # Group entries by word pairs
        grouped = self._group_entries(word_entries)
        
        # Reconcile each group
        reconciled = []
        for entries in grouped.values():
            # Filter out low confidence entries
            reliable_entries = [
                e for e in entries 
                if e.confidence >= self.confidence_threshold
            ]
            
            if reliable_entries:
                merged = self._merge_entries(reliable_entries)
                reconciled.append({
                    'word': merged.word,
                    'sanskrit_word': merged.sanskrit_word,
                    'language': merged.language,
                    'confidence': merged.confidence,
                    'source_url': merged.source_url,
                    'meanings': merged.meanings,
                    'usage_examples': merged.usage_examples,
                    'context': merged.context
                })
        
        return reconciled

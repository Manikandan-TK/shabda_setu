from typing import Dict, Optional, List
from .query_handler import QueryHandler, Query
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LoanwordInfo:
    word: str
    sanskrit_root: str
    meaning: str
    confidence: float
    etymology: Optional[str] = None
    usage_examples: Optional[List[str]] = None

class ResponseGenerator:
    def __init__(self):
        """Initialize the response generator with templates, model, and dictionary."""
        # Load model paths from config
        self.model_path = "models/fine_tuned_model"
        self.tokenizer_path = "models/fine_tuned_model"
        self.labels_path = "data/sanskrit_roots.json"
        
        try:
            # Initialize IndicBERT model
            from src.models.indic_bert_handler import IndicBertHandler
            self.model = IndicBertHandler(
                model_path=self.model_path,
                tokenizer_path=self.tokenizer_path,
                labels_path=self.labels_path
            )
            logger.info("Successfully initialized IndicBERT model")
        except Exception as e:
            logger.error(f"Error loading IndicBERT model: {e}")
            self.model = None
            
        try:
            # Initialize dictionary handler
            from src.data.dict_handler import DictionaryHandler
            self.dict_handler = DictionaryHandler()
            logger.info("Successfully initialized dictionary handler")
        except Exception as e:
            logger.error(f"Error loading dictionary handler: {e}")
            self.dict_handler = None
        
        self.query_handler = QueryHandler()
        self.response_templates = {
            # Generic responses (in English)
            'generic': {
                'found': "The word '{word}' comes from Sanskrit '{sanskrit_root}', meaning: {meaning}",
                'not_found': "Sorry, I couldn't find Sanskrit origins for '{word}'.",
                'low_confidence': "I'm not entirely sure, but '{word}' might be derived from Sanskrit '{sanskrit_root}' (confidence: {confidence}%)"
            },
            
            # Hindi (Devanagari)
            'devanagari': {
                'found': "शब्द '{word}' संस्कृत मूल '{sanskrit_root}' से आया है, अर्थ: {meaning}",
                'not_found': "क्षमा करें, '{word}' का संस्कृत मूल नहीं मिल सका।",
                'low_confidence': "मुझे पूरा यकीन नहीं है, लेकिन '{word}' शायद संस्कृत '{sanskrit_root}' से आया है।"
            },
            
            # Bengali
            'bengali': {
                'found': "শব্দ '{word}' সংস্কৃত মূল '{sanskrit_root}' থেকে এসেছে, অর্থ: {meaning}",
                'not_found': "দুঃখিত, '{word}' এর সংস্কৃত মূল খুঁজে পাওয়া যায়নি।",
                'low_confidence': "আমি নিশ্চিত নই, কিন্তু '{word}' সম্ভবত সংস্কৃত '{sanskrit_root}' থেকে এসেছে।"
            },
            
            # Telugu
            'telugu': {
                'found': "పదం '{word}' సంస్కృత మూలం '{sanskrit_root}' నుండి వచ్చింది, అర్థం: {meaning}",
                'not_found': "క్షమించండి, '{word}' యొక్క సంస్కృత మూలాన్ని కనుగొనలేకపోయాను.",
                'low_confidence': "నాకు ఖచ్చితంగా తెలియదు, కానీ '{word}' బహుశా సంస్కృత '{sanskrit_root}' నుండి వచ్చి ఉండవచ్చు."
            },
            
            # Tamil
            'tamil': {
                'found': "சொல் '{word}' சமஸ்கிருத மூலம் '{sanskrit_root}' இலிருந்து வந்துள்ளது, பொருள்: {meaning}",
                'not_found': "மன்னிக்கவும், '{word}' இன் சமஸ்கிருத மூலத்தை கண்டுபிடிக்க முடியவில்லை.",
                'low_confidence': "எனக்கு உறுதியாக தெரியவில்லை, ஆனால் '{word}' சமஸ்கிருத '{sanskrit_root}' இலிருந்து வந்திருக்கலாம்."
            },
            
            # Gujarati
            'gujarati': {
                'found': "શબ્દ '{word}' સંસ્કૃત મૂળ '{sanskrit_root}' માંથી આવ્યો છે, અર્થ: {meaning}",
                'not_found': "માફ કરશો, '{word}' નું સંસ્કૃત મૂળ મળ્યું નથી.",
                'low_confidence': "મને ચોક્કસ ખબર નથી, પણ '{word}' કદાચ સંસ્કૃત '{sanskrit_root}' માંથી આવ્યું હોઈ શકે."
            },
            
            # Kannada
            'kannada': {
                'found': "ಪದ '{word}' ಸಂಸ್ಕೃತ ಮೂಲ '{sanskrit_root}' ನಿಂದ ಬಂದಿದೆ, ಅರ್ಥ: {meaning}",
                'not_found': "ಕ್ಷಮಿಸಿ, '{word}' ನ ಸಂಸ್ಕೃತ ಮೂಲವನ್ನು ಕಂಡುಹಿಡಿಯಲಾಗಲಿಲ್ಲ.",
                'low_confidence': "ನನಗೆ ಖಚಿತವಾಗಿ ಗೊತ್ತಿಲ್ಲ, ಆದರೆ '{word}' ಬಹುಶಃ ಸಂಸ್ಕೃತ '{sanskrit_root}' ನಿಂದ ಬಂದಿರಬಹುದು."
            },
            
            # Odia
            'odia': {
                'found': "ଶବ୍ଦ '{word}' ସଂସ୍କୃତ ମୂଳ '{sanskrit_root}' ରୁ ଆସିଛି, ଅର୍ଥ: {meaning}",
                'not_found': "କ୍ଷମା କରନ୍ତୁ, '{word}' ର ସଂସ୍କୃତ ମୂଳ ମିଳିଲା ନାହିଁ।",
                'low_confidence': "ମୁଁ ନିଶ୍ଚିତ ନୁହେଁ, କିନ୍ତୁ '{word}' ହୁଏତ ସଂସ୍କୃତ '{sanskrit_root}' ରୁ ଆସିଥାଇପାରେ।"
            },
            
            # Malayalam
            'malayalam': {
                'found': "പദം '{word}' സംസ്കൃത മൂലം '{sanskrit_root}' ൽ നിന്ന് വന്നതാണ്, അർത്ഥം: {meaning}",
                'not_found': "ക്ഷമിക്കണം, '{word}' ന്റെ സംസ്കൃത മൂലം കണ്ടെത്താനായില്ല.",
                'low_confidence': "എനിക്ക് ഉറപ്പില്ല, പക്ഷേ '{word}' സംസ്കൃതം '{sanskrit_root}' ൽ നിന്ന് വന്നതാകാം."
            },
            
            # Punjabi (Gurmukhi)
            'gurmukhi': {
                'found': "ਸ਼ਬਦ '{word}' ਸੰਸਕ੍ਰਿਤ ਮੂਲ '{sanskrit_root}' ਤੋਂ ਆਇਆ ਹੈ, ਅਰਥ: {meaning}",
                'not_found': "ਮਾਫ਼ ਕਰਨਾ, '{word}' ਦਾ ਸੰਸਕ੍ਰਿਤ ਮੂਲ ਨਹੀਂ ਮਿਲਿਆ।",
                'low_confidence': "ਮੈਨੂੰ ਪੱਕਾ ਪਤਾ ਨਹੀਂ, ਪਰ '{word}' ਸ਼ਾਇਦ ਸੰਸਕ੍ਰਿਤ '{sanskrit_root}' ਤੋਂ ਆਇਆ ਹੈ।"
            }
        }

    def _get_word_info(self, word: str, script_type: str) -> Optional[LoanwordInfo]:
        """
        Get information about a potential Sanskrit loanword using both dictionary and model.
        Uses a hybrid approach:
        1. First checks dictionary for exact matches
        2. If not found, uses IndicBERT model for prediction
        3. If found in both, combines information with dictionary taking precedence
        """
        try:
            dict_entry = None
            model_prediction = None
            
            # Step 1: Dictionary Lookup
            if self.dict_handler:
                dict_entry = self.dict_handler.lookup_word(word, script_type)
            
            # Step 2: Model Prediction
            if self.model:
                sanskrit_root, meaning, confidence = self.model.predict(word, script_type)
                if sanskrit_root and meaning:
                    model_prediction = LoanwordInfo(
                        word=word,
                        sanskrit_root=sanskrit_root,
                        meaning=meaning,
                        confidence=confidence
                    )
            
            # Step 3: Combine Results
            if dict_entry:
                # Dictionary entries have high confidence
                return LoanwordInfo(
                    word=word,
                    sanskrit_root=dict_entry.sanskrit_root,
                    meaning=dict_entry.meaning,
                    confidence=1.0
                )
            elif model_prediction:
                return model_prediction
            elif not self.model and not self.dict_handler:
                # Fallback if neither system is available
                logger.warning("Both dictionary and model unavailable, using fallback")
                return LoanwordInfo(
                    word=word,
                    sanskrit_root="मूल",
                    meaning="root/origin",
                    confidence=0.85
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting word info: {e}")
            return None

    def _format_script_specific_response(self, template_key: str, script_type: str, **kwargs) -> str:
        """Format response using script-specific template if available."""
        # Use script-specific template if available, fall back to generic
        templates = self.response_templates.get(script_type, self.response_templates['generic'])
        return templates.get(template_key, self.response_templates['generic'][template_key]).format(**kwargs)

    def generate_response(self, tweet_text: str, author_username: str) -> str:
        """Generate a response to a tweet."""
        try:
            query = self.query_handler.parse_query(tweet_text)
            
            if not self.query_handler.validate_query(query):
                return f"@{author_username} {self.response_templates['generic']['not_found']}"
            
            # Process each word in the query
            loanword_results = []
            for word in query.words:
                word_info = self._get_word_info(word, query.script_type)
                if word_info:
                    if word_info.confidence < 0.7:
                        response = self._format_script_specific_response(
                            'low_confidence',
                            query.script_type,
                            word=word,
                            sanskrit_root=word_info.sanskrit_root,
                            confidence=int(word_info.confidence * 100)
                        )
                    else:
                        response = self._format_script_specific_response(
                            'found',
                            query.script_type,
                            word=word,
                            sanskrit_root=word_info.sanskrit_root,
                            meaning=word_info.meaning
                        )
                    loanword_results.append(response)
            
            if not loanword_results:
                return f"@{author_username} " + self._format_script_specific_response(
                    'not_found',
                    query.script_type,
                    word=query.words[0]
                )
            
            # Combine results into a single response
            response = " ".join(loanword_results)
            return f"@{author_username} {response}"
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"@{author_username} {self.response_templates['generic']['error']}"

    def _get_confidence_level(self, confidence: float) -> str:
        """Determine confidence level based on the score."""
        if confidence >= 0.8:
            return 'high_conf'
        elif confidence >= 0.5:
            return 'med_conf'
        return 'low_conf'

    def generate_response(self, word: str, script_type: str, query_type: str = 'word_lookup') -> str:
        """
        Generate a response about the Sanskrit loanword in the appropriate script.
        """
        # Get word information (placeholder for now)
        word_info = self._get_word_info(word, script_type)
        if not word_info:
            return f"Sorry, I couldn't find any information about '{word}'."

        # Get confidence level and appropriate template
        conf_level = self._get_confidence_level(word_info.confidence)
        
        # Default to Latin script if unsupported script is detected
        if script_type not in self.response_templates:
            script_type = 'latin'
            logger.warning(f"Unsupported script type: {script_type}, defaulting to Latin")

        # Get template and format response
        template = self.response_templates[script_type][query_type][conf_level]
        response = template.format(
            word=word,
            root=word_info.sanskrit_root,
            meaning=word_info.meaning
        )

        return response

    def analyze_tweet(self, tweet_text: str, script_type: str) -> Dict[str, List[LoanwordInfo]]:
        """
        Analyze a tweet to identify Sanskrit loanwords.
        Returns a dictionary with high and medium confidence matches.
        """
        # Extract words from tweet
        words = self.query_handler._extract_words(tweet_text)
        
        results = {
            'high_confidence': [],
            'medium_confidence': [],
            'low_confidence': []
        }
        
        for word in words:
            word_info = self._get_word_info(word, script_type)
            if word_info:
                if word_info.confidence >= 0.8:
                    results['high_confidence'].append(word_info)
                elif word_info.confidence >= 0.5:
                    results['medium_confidence'].append(word_info)
                else:
                    results['low_confidence'].append(word_info)
        
        return results

    def generate_tweet_analysis(self, tweet_text: str, script_type: str) -> str:
        """
        Generate a comprehensive response about Sanskrit loanwords in a tweet.
        """
        # Analyze tweet
        results = self.analyze_tweet(tweet_text, script_type)
        
        # Get total count of Sanskrit loanwords
        total_words = len(results['high_confidence']) + len(results['medium_confidence'])
        
        if total_words == 0:
            return self._format_script_specific_response(
                'no_sanskrit',
                script_type,
                text=tweet_text
            )
        
        # Generate response based on script type
        if script_type == 'devanagari':
            response = f"इस ट्वीट में {total_words} संस्कृत शब्द मिले:\n\n"
            
            # Add high confidence words
            if results['high_confidence']:
                response += "निश्चित संस्कृत शब्द:\n"
                for word_info in results['high_confidence']:
                    response += f"• {word_info.word} (मूल: {word_info.sanskrit_root}, अर्थ: {word_info.meaning})\n"
            
            # Add medium confidence words
            if results['medium_confidence']:
                response += "\nसंभावित संस्कृत शब्द:\n"
                for word_info in results['medium_confidence']:
                    response += f"• {word_info.word} (संभावित मूल: {word_info.sanskrit_root})\n"
                    
        elif script_type == 'bengali':
            response = f"এই টুইটে {total_words}টি সংস্কৃত শব্দ পাওয়া গেছে:\n\n"
            
            if results['high_confidence']:
                response += "নিশ্চিত সংস্কৃত শব্দ:\n"
                for word_info in results['high_confidence']:
                    response += f"• {word_info.word} (মূল: {word_info.sanskrit_root}, অর্থ: {word_info.meaning})\n"
            
            if results['medium_confidence']:
                response += "\nসম্ভাব্য সংস্কৃত শব্দ:\n"
                for word_info in results['medium_confidence']:
                    response += f"• {word_info.word} (সম্ভাব্য মূল: {word_info.sanskrit_root})\n"
                    
        # Add more script-specific formats as needed...
        
        else:  # Default to English
            response = f"Found {total_words} Sanskrit loanwords in this tweet:\n\n"
            
            if results['high_confidence']:
                response += "Confirmed Sanskrit words:\n"
                for word_info in results['high_confidence']:
                    response += f"• {word_info.word} (root: {word_info.sanskrit_root}, meaning: {word_info.meaning})\n"
            
            if results['medium_confidence']:
                response += "\nProbable Sanskrit words:\n"
                for word_info in results['medium_confidence']:
                    response += f"• {word_info.word} (probable root: {word_info.sanskrit_root})\n"
        
        return response

    def process_tweet(self, tweet_text: str, author_username: str = None) -> str:
        """
        Process a tweet and generate a response about Sanskrit loanwords.
        Main entry point for tweet analysis.
        """
        try:
            # Detect script type
            script_type = self.query_handler._detect_script(tweet_text)
            
            # Generate analysis
            response = self.generate_tweet_analysis(tweet_text, script_type)
            
            # Add mention if username provided
            if author_username:
                response = f"@{author_username} {response}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")
            return self._format_script_specific_response('error', 'latin')

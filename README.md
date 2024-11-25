# Sanskrit Loanword Detection Bot (Shabda Setu)

A Twitter bot that detects Sanskrit loanwords in Indic language tweets using a hybrid approach:
1. Automated database creation using LLMs and web scraping
2. Fine-tuned IndicBERT model trained on the verified dataset

## Project Philosophy
- 100% Automation: All processes from data collection to model training
- KISS (Keep It Simple, Stupid): Simple, focused components with clear responsibilities
- DRY (Don't Repeat Yourself): Modular design with reusable components
- Defensive Programming: Extensive validation, error handling, and logging

## Project Structure

```
├── data/
│   ├── database/              # SQLite database files
│   │   ├── main.db           # Primary database
│   │   └── staging.db        # Staging database for verification
│   ├── training/             # Training data for model fine-tuning
│   │   ├── raw/             # Processed database exports
│   │   ├── processed/       # Formatted training data
│   │   └── splits/          # Train/val/test splits
│   ├── scripts/             # Database and training scripts
│   │   ├── init_db.py      # Database initialization
│   │   ├── migrations/     # Database migrations
│   │   └── prepare_data.py # Training data preparation
│   └── sources/            # Source data and scripts
│       ├── scrapers/      # Web scraping scripts
│       ├── llm/          # LLM interaction scripts
│       └── cached/       # Cached LLM responses
├── src/
│   ├── core/
│   │   ├── database.py    # Database operations
│   │   ├── verification.py # Multi-LLM verification
│   │   └── confidence.py  # Confidence scoring system
│   ├── model/
│   │   ├── config.py     # Model configuration
│   │   ├── train.py     # Fine-tuning script
│   │   └── predict.py   # Model inference
│   ├── bot/
│   │   ├── twitter_handler.py # Twitter API integration
│   │   └── response_gen.py    # Response generation
│   ├── llm/
│   │   ├── manager.py   # LLM API management
│   │   ├── prompts.py   # LLM prompt templates
│   │   └── parser.py    # LLM response parsing
│   └── utils/
│       ├── validators.py # Input validation
│       ├── sanitizers.py # Data sanitization
│       └── logging.py    # Logging utilities
├── tests/               # Unit and integration tests
├── config/
│   ├── llm_config.yaml # LLM API configurations
│   ├── db_config.yaml  # Database configurations
│   ├── model_config.yaml # Model training settings
│   └── bot_config.yaml # Twitter bot settings
└── requirements.txt    # Project dependencies
```

## Development Phases

### Phase 1: Database Creation
1. **Data Collection**
   - Web scraping from reliable sources
   - Initial LLM generation of candidate words
   - Caching all responses for reproducibility

2. **Verification**
   - Multi-LLM cross-verification
   - Confidence scoring based on:
     * LLM agreement
     * Source reliability
     * Etymology consistency

3. **Quality Assurance**
   - Automated validation
   - Consistency checks
   - Regular audits

### Phase 2: Model Development
1. **Data Preparation**
   - Export high-confidence entries (score > 0.8)
   - Format for sequence labeling task
   - Create train/val/test splits

2. **Model Fine-tuning**
   - Base model: IndicBERT
   - Task: Token classification (BIO tagging)
   - Custom features:
     * Script-aware embeddings
     * Etymology attention layer
     * Confidence score integration

3. **Model Evaluation**
   - Standard metrics (Precision, Recall, F1)
   - Cross-lingual performance
   - Confidence calibration

## Database Schema

```sql
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
);

CREATE TABLE etymologies (
    id INTEGER PRIMARY KEY,
    word_id INTEGER,
    sanskrit_root TEXT NOT NULL,
    verification_count INTEGER DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.0,
    FOREIGN KEY(word_id) REFERENCES words(id)
);

CREATE TABLE verifications (
    id INTEGER PRIMARY KEY,
    word_id INTEGER,
    llm_name TEXT NOT NULL,
    confidence_score FLOAT NOT NULL,
    verification_data JSON,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(word_id) REFERENCES words(id)
);
```

## Training Data Format
```json
{
    "text": "அவர் நல்ல மனிதன்",
    "tokens": ["அவர்", "நல்ல", "மனிதன்"],
    "labels": ["O", "O", "B-SANSKRIT"],
    "metadata": {
        "sanskrit_root": "मनुष्य",
        "confidence": 0.92,
        "etymology": "From Sanskrit मनुष्य (manuṣya)"
    }
}
```

## Usage

1. Initialize and populate database:
```bash
python -m data.scripts.init_db
python -m data.sources.collect_all
```

2. Train model:
```bash
python -m src.model.train --config config/model_config.yaml
```

3. Run bot:
```bash
python -m src.bot.twitter_handler
```

## Inference Pipeline
1. Tweet received → Tokenization
2. IndicBERT prediction → Sanskrit token identification
3. Database lookup → Etymology and confidence retrieval
4. Response generation with explanations

## Error Handling
- Comprehensive logging
- Graceful fallbacks
- Health monitoring
- Automated error reporting

## Future Improvements
1. Active learning from Twitter feedback
2. Multi-task learning for:
   - Script conversion
   - Etymology prediction
3. Cross-lingual transfer learning
4. Confidence score refinement

## License
MIT License - See LICENSE file for details

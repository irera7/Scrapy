"""NLP Processing Service for text data."""
import re
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.data_item import DataItem

logger = structlog.get_logger()


class NLPProcessor:
    """NLP processing for text data."""
    
    # Language detection
    _langdetect_available = False
    _fasttext_model = None
    _nltk_available = False
    _spacy_available = False
    _spacy_model = None
    
    # Persian stopwords
    PERSIAN_STOPWORDS = {
        'و', 'در', 'به', 'از', 'که', 'این', 'را', 'با', 'است', 'برای',
        'آن', 'یک', 'خود', 'تا', 'کرد', 'بر', 'هم', 'نیز', 'گفت', 'می',
        'شد', 'او', 'ها', 'های', 'یا', 'اما', 'باید', 'دو', 'هر', 'بود',
        'شده', 'پس', 'اگر', 'همه', 'صورت', 'یکی', 'طور', 'گرفت', 'دارد',
        'همین', 'بین', 'بی', 'نه', 'دیگر', 'آنها', 'باشد', 'کند', 'داده',
        'بوده', 'کنند', 'شود', 'کنیم', 'کنید', 'شوند', 'بودند', 'داشت',
    }
    
    def __init__(self):
        try:
            from langdetect import detect, detect_langs
            self._langdetect_available = True
        except ImportError:
            logger.warning("langdetect not installed, language detection will be limited")
        
        # Try to load NLTK
        try:
            import nltk
            self._nltk_available = True
            # Try to download required data silently
            try:
                nltk.data.find('taggers/averaged_perceptron_tagger')
            except LookupError:
                try:
                    nltk.download('averaged_perceptron_tagger', quiet=True)
                    nltk.download('punkt', quiet=True)
                    nltk.download('wordnet', quiet=True)
                except:
                    pass
        except ImportError:
            logger.warning("NLTK not installed, POS tagging and lemmatization will be limited")
        
        # Try to load spaCy
        try:
            import spacy
            self._spacy_available = True
        except ImportError:
            logger.warning("spaCy not installed, advanced NLP features will be limited")
    
    async def detect_language(self, text: str) -> Dict[str, Any]:
        """Detect language of text."""
        if not text or len(text) < 20:
            return {"language": "unknown", "confidence": 0.0}
        
        try:
            from langdetect import detect, detect_langs
            
            lang = detect(text)
            langs = detect_langs(text)
            
            return {
                "language": lang,
                "confidence": langs[0].prob if langs else 0.0,
                "alternatives": [
                    {"lang": str(l.lang), "prob": round(l.prob, 3)}
                    for l in langs[:5]
                ]
            }
        except Exception as e:
            logger.warning(f"Language detection error: {e}")
            return {"language": "unknown", "confidence": 0.0}
    
    def clean_text(self, text: str, options: Dict[str, bool] = None) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        options = options or {}
        
        # Normalize unicode
        if options.get("normalize_unicode", True):
            text = unicodedata.normalize('NFKC', text)
        
        # Remove control characters
        if options.get("remove_control_chars", True):
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # Remove HTML entities
        if options.get("decode_html", True):
            import html
            text = html.unescape(text)
        
        # Normalize whitespace
        if options.get("normalize_whitespace", True):
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
        
        # Remove URLs
        if options.get("remove_urls", False):
            text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
        # Remove emails
        if options.get("remove_emails", False):
            text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Remove mentions (@username)
        if options.get("remove_mentions", False):
            text = re.sub(r'@\w+', '', text)
        
        # Remove hashtags (#tag)
        if options.get("remove_hashtags", False):
            text = re.sub(r'#\w+', '', text)
        
        # Remove emojis
        if options.get("remove_emojis", False):
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F1E0-\U0001F1FF"  # flags
                "\U00002702-\U000027B0"
                "\U000024C2-\U0001F251"
                "]+",
                flags=re.UNICODE
            )
            text = emoji_pattern.sub('', text)
        
        # Lowercase
        if options.get("lowercase", False):
            text = text.lower()
        
        return text.strip()
    
    def tokenize(self, text: str, method: str = "word") -> List[str]:
        """Tokenize text into tokens."""
        if not text:
            return []
        
        if method == "word":
            # Simple word tokenization
            return re.findall(r'\b\w+\b', text.lower())
        
        elif method == "sentence":
            # Sentence tokenization
            sentences = re.split(r'[.!?]+', text)
            return [s.strip() for s in sentences if s.strip()]
        
        elif method == "char":
            return list(text)
        
        elif method == "ngram":
            # Character n-grams (bigrams by default)
            return [text[i:i+2] for i in range(len(text)-1)]
        
        return text.split()
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[Tuple[str, int]]:
        """Extract keywords based on frequency."""
        if not text:
            return []
        
        # Tokenize
        words = self.tokenize(text, "word")
        
        # Remove stopwords (basic English stopwords)
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'this', 'that', 'these', 'those', 'it', 'its', 'i', 'you', 'he',
            'she', 'we', 'they', 'them', 'their', 'my', 'your', 'his', 'her',
            'our', 'not', 'no', 'yes', 'if', 'when', 'where', 'what', 'which',
            'who', 'whom', 'how', 'why', 'all', 'each', 'every', 'both', 'few',
            'more', 'most', 'other', 'some', 'such', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there', 'then',
        }
        
        # Filter and count
        word_counts: Dict[str, int] = {}
        for word in words:
            if word not in stopwords and len(word) > 2:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_words[:top_n]
    
    def compute_text_stats(self, text: str) -> Dict[str, Any]:
        """Compute statistics for text."""
        if not text:
            return {
                "char_count": 0,
                "word_count": 0,
                "sentence_count": 0,
                "avg_word_length": 0,
                "avg_sentence_length": 0,
            }
        
        chars = len(text)
        words = self.tokenize(text, "word")
        sentences = self.tokenize(text, "sentence")
        
        word_count = len(words)
        sentence_count = len(sentences)
        
        avg_word_length = sum(len(w) for w in words) / max(word_count, 1)
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Unique word ratio (vocabulary richness)
        unique_ratio = len(set(words)) / max(word_count, 1)
        
        return {
            "char_count": chars,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_word_length": round(avg_word_length, 2),
            "avg_sentence_length": round(avg_sentence_length, 2),
            "unique_word_ratio": round(unique_ratio, 3),
            "unique_words": len(set(words)),
        }
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities (basic pattern matching)."""
        if not text:
            return {}
        
        entities = {
            "emails": [],
            "urls": [],
            "phone_numbers": [],
            "dates": [],
            "money": [],
            "hashtags": [],
            "mentions": [],
        }
        
        # Emails
        emails = re.findall(r'\b[\w.-]+@[\w.-]+\.\w+\b', text)
        entities["emails"] = list(set(emails))
        
        # URLs
        urls = re.findall(r'https?://\S+|www\.\S+', text)
        entities["urls"] = list(set(urls))
        
        # Phone numbers (basic patterns)
        phones = re.findall(r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b', text)
        entities["phone_numbers"] = list(set(phones))
        
        # Dates (various formats)
        dates = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', text)
        entities["dates"] = list(set(dates))
        
        # Money (USD, EUR, etc.)
        money = re.findall(r'[$€£¥]\s*\d+(?:[.,]\d{2})?(?:\s*(?:million|billion|thousand|k|m|b))?', text, re.IGNORECASE)
        entities["money"] = list(set(money))
        
        # Hashtags
        hashtags = re.findall(r'#\w+', text)
        entities["hashtags"] = list(set(hashtags))
        
        # Mentions
        mentions = re.findall(r'@\w+', text)
        entities["mentions"] = list(set(mentions))
        
        return entities
    
    def summarize_simple(self, text: str, max_sentences: int = 3) -> str:
        """Simple extractive summarization based on sentence importance."""
        if not text:
            return ""
        
        sentences = self.tokenize(text, "sentence")
        if len(sentences) <= max_sentences:
            return text
        
        # Score sentences by keyword presence
        keywords = dict(self.extract_keywords(text, top_n=20))
        
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            words = self.tokenize(sentence, "word")
            score = sum(keywords.get(w, 0) for w in words)
            # Boost first sentences
            if i < 3:
                score *= 1.5
            scored_sentences.append((score, i, sentence))
        
        # Sort by score and take top sentences
        scored_sentences.sort(reverse=True)
        top_sentences = scored_sentences[:max_sentences]
        
        # Sort by original order
        top_sentences.sort(key=lambda x: x[1])
        
        return ' '.join(s[2] for s in top_sentences)
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute Jaccard similarity between two texts."""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(self.tokenize(text1, "word"))
        words2 = set(self.tokenize(text2, "word"))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def detect_duplicates(self, texts: List[str], threshold: float = 0.8) -> List[Tuple[int, int, float]]:
        """Detect duplicate or near-duplicate texts."""
        duplicates = []
        
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                similarity = self.compute_similarity(texts[i], texts[j])
                if similarity >= threshold:
                    duplicates.append((i, j, round(similarity, 3)))
        
        return duplicates
    
    def pos_tag(self, text: str, language: str = "en") -> List[Tuple[str, str]]:
        """
        Perform Part-of-Speech tagging.
        
        Args:
            text: Input text
            language: Language code ('en' for English, 'fa' for Persian)
            
        Returns:
            List of (word, POS tag) tuples
            
        POS Tags (Penn Treebank for English):
            - NN: Noun, singular
            - NNS: Noun, plural
            - VB: Verb, base form
            - VBD: Verb, past tense
            - VBG: Verb, gerund
            - JJ: Adjective
            - RB: Adverb
            - etc.
        """
        if not text:
            return []
        
        if self._nltk_available and language == "en":
            try:
                import nltk
                from nltk import word_tokenize, pos_tag
                
                tokens = word_tokenize(text)
                return pos_tag(tokens)
            except Exception as e:
                logger.warning(f"NLTK POS tagging failed: {e}")
        
        if self._spacy_available:
            try:
                import spacy
                
                if self._spacy_model is None:
                    model_name = "en_core_web_sm" if language == "en" else "xx_ent_wiki_sm"
                    try:
                        self._spacy_model = spacy.load(model_name)
                    except OSError:
                        logger.warning(f"spaCy model {model_name} not found")
                        return self._simple_pos_tag(text)
                
                doc = self._spacy_model(text)
                return [(token.text, token.pos_) for token in doc]
            except Exception as e:
                logger.warning(f"spaCy POS tagging failed: {e}")
        
        # Fallback to simple rule-based tagging
        return self._simple_pos_tag(text)
    
    def _simple_pos_tag(self, text: str) -> List[Tuple[str, str]]:
        """Simple rule-based POS tagging as fallback."""
        words = self.tokenize(text, "word")
        
        # Simple heuristic rules
        tagged = []
        for word in words:
            word_lower = word.lower()
            
            if word_lower.endswith(('ing', 'ed', 's')):
                tag = 'VB'  # Verb
            elif word_lower.endswith(('ly',)):
                tag = 'RB'  # Adverb
            elif word_lower.endswith(('tion', 'ness', 'ment', 'er', 'or')):
                tag = 'NN'  # Noun
            elif word_lower.endswith(('ful', 'less', 'ous', 'ive', 'able', 'ible')):
                tag = 'JJ'  # Adjective
            elif word_lower in {'the', 'a', 'an'}:
                tag = 'DT'  # Determiner
            elif word_lower in {'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from'}:
                tag = 'IN'  # Preposition
            elif word_lower in {'and', 'or', 'but', 'nor'}:
                tag = 'CC'  # Conjunction
            else:
                tag = 'NN'  # Default to noun
            
            tagged.append((word, tag))
        
        return tagged
    
    def stem(self, word: str, language: str = "en") -> str:
        """
        Perform stemming on a word.
        Stemming reduces words to their root form (may not be a valid word).
        
        Args:
            word: Input word
            language: Language code
            
        Returns:
            Stemmed word
        """
        if not word:
            return ""
        
        if self._nltk_available and language == "en":
            try:
                from nltk.stem import PorterStemmer, SnowballStemmer
                
                # Use Snowball stemmer for better results
                stemmer = SnowballStemmer("english")
                return stemmer.stem(word)
            except Exception as e:
                logger.warning(f"NLTK stemming failed: {e}")
        
        # Simple fallback stemmer
        return self._simple_stem(word)
    
    def _simple_stem(self, word: str) -> str:
        """Simple suffix-stripping stemmer as fallback."""
        word = word.lower()
        
        # Common English suffixes
        suffixes = [
            'ing', 'ed', 'ly', 'es', 's', 'ment', 'ness', 'tion', 'ation',
            'ful', 'less', 'ous', 'ive', 'able', 'ible', 'er', 'or', 'ist'
        ]
        
        for suffix in sorted(suffixes, key=len, reverse=True):
            if len(word) > len(suffix) + 2 and word.endswith(suffix):
                return word[:-len(suffix)]
        
        return word
    
    def stem_text(self, text: str, language: str = "en") -> str:
        """Stem all words in text."""
        words = self.tokenize(text, "word")
        stemmed = [self.stem(word, language) for word in words]
        return ' '.join(stemmed)
    
    def lemmatize(self, word: str, pos: str = None, language: str = "en") -> str:
        """
        Perform lemmatization on a word.
        Lemmatization reduces words to their base/dictionary form.
        
        Args:
            word: Input word
            pos: Part of speech (optional, for better accuracy)
            language: Language code
            
        Returns:
            Lemmatized word
        """
        if not word:
            return ""
        
        if self._nltk_available and language == "en":
            try:
                from nltk.stem import WordNetLemmatizer
                from nltk.corpus import wordnet
                
                lemmatizer = WordNetLemmatizer()
                
                # Map POS tag to WordNet POS
                if pos:
                    if pos.startswith('J'):
                        wn_pos = wordnet.ADJ
                    elif pos.startswith('V'):
                        wn_pos = wordnet.VERB
                    elif pos.startswith('R'):
                        wn_pos = wordnet.ADV
                    else:
                        wn_pos = wordnet.NOUN
                else:
                    wn_pos = wordnet.NOUN
                
                return lemmatizer.lemmatize(word.lower(), wn_pos)
            except Exception as e:
                logger.warning(f"NLTK lemmatization failed: {e}")
        
        if self._spacy_available:
            try:
                import spacy
                
                if self._spacy_model is None:
                    try:
                        self._spacy_model = spacy.load("en_core_web_sm")
                    except OSError:
                        return word.lower()
                
                doc = self._spacy_model(word)
                if doc:
                    return doc[0].lemma_
            except Exception as e:
                logger.warning(f"spaCy lemmatization failed: {e}")
        
        # Simple fallback
        return self._simple_lemmatize(word)
    
    def _simple_lemmatize(self, word: str) -> str:
        """Simple rule-based lemmatization as fallback."""
        word = word.lower()
        
        # Common irregular forms
        irregulars = {
            'was': 'be', 'were': 'be', 'been': 'be', 'am': 'be', 'is': 'be', 'are': 'be',
            'had': 'have', 'has': 'have',
            'did': 'do', 'does': 'do', 'done': 'do',
            'went': 'go', 'gone': 'go', 'goes': 'go',
            'said': 'say', 'says': 'say',
            'made': 'make', 'makes': 'make',
            'took': 'take', 'taken': 'take', 'takes': 'take',
            'came': 'come', 'comes': 'come',
            'saw': 'see', 'seen': 'see', 'sees': 'see',
            'knew': 'know', 'known': 'know', 'knows': 'know',
            'thought': 'think', 'thinks': 'think',
            'got': 'get', 'gotten': 'get', 'gets': 'get',
            'gave': 'give', 'given': 'give', 'gives': 'give',
            'found': 'find', 'finds': 'find',
            'told': 'tell', 'tells': 'tell',
            'felt': 'feel', 'feels': 'feel',
            'became': 'become', 'becomes': 'become',
            'began': 'begin', 'begun': 'begin', 'begins': 'begin',
            'children': 'child', 'men': 'man', 'women': 'woman',
            'feet': 'foot', 'teeth': 'tooth', 'mice': 'mouse',
            'people': 'person', 'leaves': 'leaf', 'lives': 'life',
        }
        
        if word in irregulars:
            return irregulars[word]
        
        # Simple suffix rules
        if word.endswith('ies') and len(word) > 4:
            return word[:-3] + 'y'
        if word.endswith('es') and len(word) > 3:
            if word[-3] in 'sxzh':
                return word[:-2]
        if word.endswith('s') and len(word) > 2 and word[-2] not in 'su':
            return word[:-1]
        if word.endswith('ed') and len(word) > 3:
            if word[-3] == word[-4]:  # doubled consonant
                return word[:-3]
            return word[:-2]
        if word.endswith('ing') and len(word) > 4:
            if word[-4] == word[-5]:  # doubled consonant
                return word[:-4]
            return word[:-3]
        
        return word
    
    def lemmatize_text(self, text: str, language: str = "en") -> str:
        """Lemmatize all words in text with POS information."""
        if not text:
            return ""
        
        # Get POS tags for better lemmatization
        tagged = self.pos_tag(text, language)
        lemmatized = [self.lemmatize(word, pos, language) for word, pos in tagged]
        return ' '.join(lemmatized)
    
    def get_pos_distribution(self, text: str, language: str = "en") -> Dict[str, int]:
        """Get distribution of POS tags in text."""
        tagged = self.pos_tag(text, language)
        
        distribution: Dict[str, int] = {}
        for _, tag in tagged:
            distribution[tag] = distribution.get(tag, 0) + 1
        
        return distribution
    
    def extract_nouns(self, text: str, language: str = "en") -> List[str]:
        """Extract all nouns from text."""
        tagged = self.pos_tag(text, language)
        nouns = [word for word, tag in tagged if tag.startswith('NN') or tag == 'NOUN']
        return nouns
    
    def extract_verbs(self, text: str, language: str = "en") -> List[str]:
        """Extract all verbs from text."""
        tagged = self.pos_tag(text, language)
        verbs = [word for word, tag in tagged if tag.startswith('VB') or tag == 'VERB']
        return verbs
    
    def extract_adjectives(self, text: str, language: str = "en") -> List[str]:
        """Extract all adjectives from text."""
        tagged = self.pos_tag(text, language)
        adjectives = [word for word, tag in tagged if tag.startswith('JJ') or tag == 'ADJ']
        return adjectives
    
    def remove_stopwords(self, text: str, language: str = "en", custom_stopwords: set = None) -> str:
        """Remove stopwords from text."""
        words = self.tokenize(text, "word")
        
        # Get stopwords for language
        stopwords = set()
        
        if language == "en":
            # English stopwords
            stopwords = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
                'this', 'that', 'these', 'those', 'it', 'its', 'i', 'you', 'he',
                'she', 'we', 'they', 'them', 'their', 'my', 'your', 'his', 'her',
                'our', 'not', 'no', 'yes', 'if', 'when', 'where', 'what', 'which',
                'who', 'whom', 'how', 'why', 'all', 'each', 'every', 'both', 'few',
                'more', 'most', 'other', 'some', 'such', 'only', 'own', 'same', 'so',
                'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there', 'then',
            }
        elif language == "fa":
            stopwords = self.PERSIAN_STOPWORDS
        
        # Add custom stopwords
        if custom_stopwords:
            stopwords = stopwords | custom_stopwords
        
        filtered = [w for w in words if w.lower() not in stopwords]
        return ' '.join(filtered)


# Global instance
nlp_processor = NLPProcessor()


async def process_text_item(item: DataItem, db: AsyncSession, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Process a text data item with NLP."""
    options = options or {}
    result = {}
    
    if not item.content:
        return {"error": "No content to process"}
    
    # Clean text
    if options.get("clean", True):
        item.content = nlp_processor.clean_text(item.content, options.get("clean_options", {}))
        result["cleaned"] = True
    
    # Detect language
    if options.get("detect_language", True):
        lang_info = await nlp_processor.detect_language(item.content)
        metadata = item.item_metadata or {}
        metadata["language"] = lang_info["language"]
        metadata["language_confidence"] = lang_info["confidence"]
        if lang_info.get("alternatives"):
            metadata["language_alternatives"] = lang_info["alternatives"]
        item.item_metadata = metadata
        result["language"] = lang_info
    
    # Compute stats
    if options.get("compute_stats", True):
        stats = nlp_processor.compute_text_stats(item.content)
        metadata = item.item_metadata or {}
        metadata["text_stats"] = stats
        item.item_metadata = metadata
        result["stats"] = stats
    
    # Extract keywords
    if options.get("extract_keywords", False):
        keywords = nlp_processor.extract_keywords(item.content, options.get("keyword_count", 10))
        metadata = item.item_metadata or {}
        metadata["keywords"] = [{"word": w, "count": c} for w, c in keywords]
        item.item_metadata = metadata
        result["keywords"] = keywords
    
    # Extract entities
    if options.get("extract_entities", False):
        entities = nlp_processor.extract_entities(item.content)
        metadata = item.item_metadata or {}
        metadata["entities"] = entities
        item.item_metadata = metadata
        result["entities"] = entities
    
    # Summarize
    if options.get("summarize", False):
        summary = nlp_processor.summarize_simple(
            item.content, 
            options.get("summary_sentences", 3)
        )
        metadata = item.item_metadata or {}
        metadata["summary"] = summary
        item.item_metadata = metadata
        result["summary"] = summary
    
    item.is_processed = True
    await db.commit()
    
    return result


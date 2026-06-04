"""
Sentiment Analysis Engine
==========================

Combines TextBlob and VADER for financial text sentiment analysis.
Also includes keyword-based hawkish/dovish detection for central bank statements.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

import re
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from datetime import datetime

# Sentiment libraries
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print("[WARNING] TextBlob not installed. Run: pip install textblob")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("[WARNING] VADER not installed. Run: pip install vaderSentiment")

from .config import (
    HAWKISH_KEYWORDS, DOVISH_KEYWORDS, NEUTRAL_KEYWORDS,
    FISCAL_BULLISH_KEYWORDS, FISCAL_BEARISH_KEYWORDS,
    BiasDirection
)


@dataclass
class SentimentResult:
    """Container for sentiment analysis results"""
    
    # Overall scores
    composite_score: float      # -1 to 1 (bearish to bullish for currency)
    confidence: float           # 0 to 1 (how confident in the score)
    
    # Component scores
    textblob_polarity: float    # -1 to 1
    textblob_subjectivity: float  # 0 to 1
    vader_compound: float       # -1 to 1
    vader_pos: float            # 0 to 1
    vader_neg: float            # 0 to 1
    vader_neu: float            # 0 to 1
    
    # Keyword analysis
    hawkish_count: int
    dovish_count: int
    keyword_score: float        # -1 to 1 based on keyword balance
    
    # Metadata
    text_length: int
    analysis_time: str
    
    def to_dict(self) -> Dict:
        return {
            'composite_score': self.composite_score,
            'confidence': self.confidence,
            'textblob_polarity': self.textblob_polarity,
            'textblob_subjectivity': self.textblob_subjectivity,
            'vader_compound': self.vader_compound,
            'hawkish_count': self.hawkish_count,
            'dovish_count': self.dovish_count,
            'keyword_score': self.keyword_score,
            'text_length': self.text_length,
            'analysis_time': self.analysis_time,
        }
    
    def get_direction(self) -> BiasDirection:
        """Convert score to direction enum"""
        if self.composite_score > 0.1:
            return BiasDirection.BULLISH
        elif self.composite_score < -0.1:
            return BiasDirection.BEARISH
        return BiasDirection.NEUTRAL


class SentimentEngine:
    """
    Multi-method sentiment analyzer for financial text.
    
    Combines:
    - TextBlob: General NLP sentiment
    - VADER: Social media optimized (good for news headlines)
    - Keyword matching: Domain-specific hawkish/dovish detection
    """
    
    def __init__(self):
        """Initialize sentiment analyzers"""
        
        # VADER analyzer
        if VADER_AVAILABLE:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None
        
        # Precompile keyword patterns for efficiency
        self._compile_keyword_patterns()
    
    def _compile_keyword_patterns(self):
        """Compile regex patterns for keyword matching"""
        
        # Hawkish patterns
        self.hawkish_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in HAWKISH_KEYWORDS
        ]
        
        # Dovish patterns
        self.dovish_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in DOVISH_KEYWORDS
        ]
        
        # Fiscal patterns
        self.fiscal_bullish_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in FISCAL_BULLISH_KEYWORDS
        ]
        
        self.fiscal_bearish_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in FISCAL_BEARISH_KEYWORDS
        ]
    
    def analyze(self, text: str, context: str = 'monetary') -> SentimentResult:
        """
        Analyze text sentiment with combined methods.
        
        Args:
            text: Text to analyze
            context: 'monetary' for central bank, 'fiscal' for government
            
        Returns:
            SentimentResult with all scores
        """
        if not text or not text.strip():
            return self._empty_result()
        
        # Clean text
        cleaned = self._clean_text(text)
        
        # TextBlob analysis
        tb_polarity, tb_subjectivity = self._analyze_textblob(cleaned)
        
        # VADER analysis
        vader_scores = self._analyze_vader(cleaned)
        
        # Keyword analysis
        if context == 'fiscal':
            keyword_score, hawkish, dovish = self._analyze_fiscal_keywords(cleaned)
        else:
            keyword_score, hawkish, dovish = self._analyze_monetary_keywords(cleaned)
        
        # Combine scores
        composite, confidence = self._combine_scores(
            tb_polarity, vader_scores['compound'], keyword_score,
            tb_subjectivity, len(cleaned)
        )
        
        return SentimentResult(
            composite_score=composite,
            confidence=confidence,
            textblob_polarity=tb_polarity,
            textblob_subjectivity=tb_subjectivity,
            vader_compound=vader_scores['compound'],
            vader_pos=vader_scores['pos'],
            vader_neg=vader_scores['neg'],
            vader_neu=vader_scores['neu'],
            hawkish_count=hawkish,
            dovish_count=dovish,
            keyword_score=keyword_score,
            text_length=len(cleaned),
            analysis_time=datetime.now().isoformat()
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation for sentiment
        text = re.sub(r'[^\w\s.,!?;:\'-]', '', text)
        
        return text.strip()
    
    def _analyze_textblob(self, text: str) -> Tuple[float, float]:
        """Analyze with TextBlob"""
        if not TEXTBLOB_AVAILABLE:
            return 0.0, 0.5
        
        try:
            blob = TextBlob(text)
            return blob.sentiment.polarity, blob.sentiment.subjectivity
        except Exception:
            return 0.0, 0.5
    
    def _analyze_vader(self, text: str) -> Dict[str, float]:
        """Analyze with VADER"""
        if self.vader is None:
            return {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0}
        
        try:
            scores = self.vader.polarity_scores(text)
            return scores
        except Exception:
            return {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0}
    
    def _analyze_monetary_keywords(self, text: str) -> Tuple[float, int, int]:
        """
        Count hawkish vs dovish keywords.
        
        Returns:
            (score, hawkish_count, dovish_count)
            score: -1 (all dovish) to 1 (all hawkish)
        """
        hawkish_count = sum(
            1 for pattern in self.hawkish_patterns
            if pattern.search(text)
        )
        
        dovish_count = sum(
            1 for pattern in self.dovish_patterns
            if pattern.search(text)
        )
        
        total = hawkish_count + dovish_count
        if total == 0:
            return 0.0, 0, 0
        
        # Score: hawkish = positive (bullish for currency)
        score = (hawkish_count - dovish_count) / total
        
        return score, hawkish_count, dovish_count
    
    def _analyze_fiscal_keywords(self, text: str) -> Tuple[float, int, int]:
        """
        Count fiscal bullish vs bearish keywords.
        
        Returns:
            (score, bullish_count, bearish_count)
        """
        bullish_count = sum(
            1 for pattern in self.fiscal_bullish_patterns
            if pattern.search(text)
        )
        
        bearish_count = sum(
            1 for pattern in self.fiscal_bearish_patterns
            if pattern.search(text)
        )
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0, 0, 0
        
        score = (bullish_count - bearish_count) / total
        
        return score, bullish_count, bearish_count
    
    def _combine_scores(
        self,
        tb_polarity: float,
        vader_compound: float,
        keyword_score: float,
        subjectivity: float,
        text_length: int
    ) -> Tuple[float, float]:
        """
        Combine all sentiment scores into composite.
        
        Weighting:
        - Keyword matching: 50% (most relevant for financial text)
        - VADER: 30% (good for headlines)
        - TextBlob: 20% (general NLP)
        
        Returns:
            (composite_score, confidence)
        """
        # Weighted average
        composite = (
            keyword_score * 0.50 +
            vader_compound * 0.30 +
            tb_polarity * 0.20
        )
        
        # Confidence based on:
        # - Agreement between methods
        # - Text length (more text = more confident)
        # - Subjectivity (less subjective = more factual = more confident)
        
        # Method agreement (0-1)
        scores = [tb_polarity, vader_compound, keyword_score]
        non_zero = [s for s in scores if abs(s) > 0.05]
        
        if len(non_zero) >= 2:
            # Check if signs agree
            signs = [1 if s > 0 else -1 for s in non_zero]
            agreement = 1.0 if len(set(signs)) == 1 else 0.5
        else:
            agreement = 0.3  # Not enough signal
        
        # Text length factor (more text = more confident, cap at 500 chars)
        length_factor = min(text_length / 500, 1.0)
        
        # Subjectivity factor (less subjective = more confident)
        objectivity_factor = 1.0 - subjectivity * 0.5
        
        # Combined confidence
        confidence = (
            agreement * 0.50 +
            length_factor * 0.25 +
            objectivity_factor * 0.25
        )
        
        return round(composite, 4), round(confidence, 4)
    
    def _empty_result(self) -> SentimentResult:
        """Return empty result for invalid input"""
        return SentimentResult(
            composite_score=0.0,
            confidence=0.0,
            textblob_polarity=0.0,
            textblob_subjectivity=0.5,
            vader_compound=0.0,
            vader_pos=0.0,
            vader_neg=0.0,
            vader_neu=1.0,
            hawkish_count=0,
            dovish_count=0,
            keyword_score=0.0,
            text_length=0,
            analysis_time=datetime.now().isoformat()
        )
    
    def analyze_headline(self, headline: str) -> SentimentResult:
        """
        Optimized analysis for short headlines.
        
        Uses higher keyword weight since headlines are keyword-dense.
        """
        result = self.analyze(headline)
        
        # Boost keyword influence for short text
        if result.text_length < 100:
            # Recalculate with 70% keyword weight
            adjusted = (
                result.keyword_score * 0.70 +
                result.vader_compound * 0.20 +
                result.textblob_polarity * 0.10
            )
            result.composite_score = round(adjusted, 4)
        
        return result
    
    def analyze_batch(self, texts: List[str], context: str = 'monetary') -> List[SentimentResult]:
        """Analyze multiple texts efficiently"""
        return [self.analyze(text, context) for text in texts]
    
    def get_dominant_sentiment(self, results: List[SentimentResult]) -> SentimentResult:
        """
        Aggregate multiple results into dominant sentiment.
        
        Useful for analyzing multiple headlines/statements about same event.
        """
        if not results:
            return self._empty_result()
        
        # Weighted average by confidence
        total_weight = sum(r.confidence for r in results)
        
        if total_weight == 0:
            # Equal weighting
            avg_score = sum(r.composite_score for r in results) / len(results)
            avg_confidence = 0.3
        else:
            avg_score = sum(
                r.composite_score * r.confidence for r in results
            ) / total_weight
            avg_confidence = total_weight / len(results)
        
        # Return aggregated result
        return SentimentResult(
            composite_score=round(avg_score, 4),
            confidence=round(avg_confidence, 4),
            textblob_polarity=sum(r.textblob_polarity for r in results) / len(results),
            textblob_subjectivity=sum(r.textblob_subjectivity for r in results) / len(results),
            vader_compound=sum(r.vader_compound for r in results) / len(results),
            vader_pos=sum(r.vader_pos for r in results) / len(results),
            vader_neg=sum(r.vader_neg for r in results) / len(results),
            vader_neu=sum(r.vader_neu for r in results) / len(results),
            hawkish_count=sum(r.hawkish_count for r in results),
            dovish_count=sum(r.dovish_count for r in results),
            keyword_score=sum(r.keyword_score for r in results) / len(results),
            text_length=sum(r.text_length for r in results),
            analysis_time=datetime.now().isoformat()
        )


# Convenience function
def analyze_sentiment(text: str, context: str = 'monetary') -> SentimentResult:
    """Quick sentiment analysis function"""
    engine = SentimentEngine()
    return engine.analyze(text, context)

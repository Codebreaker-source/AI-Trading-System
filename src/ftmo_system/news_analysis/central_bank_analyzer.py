"""
Central Bank Statement Analyzer
================================

Analyzes central bank statements, speeches, and minutes to extract
hawkish/dovish sentiment and generate trading biases.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

from .config import BiasDirection, BiasStrength, TIMING, CURRENCY_MAPPING
from .sentiment_engine import SentimentEngine, SentimentResult
from .data_sources.central_bank_feeds import CentralBankFeeds, CentralBankStatement


@dataclass
class CentralBankBias:
    """Bias derived from central bank communication"""
    
    bank: str
    currency: str
    direction: BiasDirection
    strength: BiasStrength
    sentiment_score: float      # -1 to 1
    confidence: float           # 0 to 1
    
    # Source info
    statement_title: str
    statement_type: str         # rate_decision, minutes, speech
    analysis_time: datetime
    bias_expiry: datetime
    
    # Raw sentiment data
    hawkish_count: int
    dovish_count: int
    
    def is_active(self) -> bool:
        """Check if bias is still active"""
        return datetime.utcnow() < self.bias_expiry
    
    def hours_remaining(self) -> float:
        """Hours until bias expires"""
        delta = self.bias_expiry - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)
    
    def to_dict(self) -> Dict:
        return {
            'bank': self.bank,
            'currency': self.currency,
            'direction': self.direction.name,
            'strength': self.strength.name,
            'sentiment_score': self.sentiment_score,
            'confidence': self.confidence,
            'statement_title': self.statement_title,
            'statement_type': self.statement_type,
            'analysis_time': self.analysis_time.isoformat(),
            'bias_expiry': self.bias_expiry.isoformat(),
            'hawkish_count': self.hawkish_count,
            'dovish_count': self.dovish_count,
        }


class CentralBankAnalyzer:
    """
    Analyzes central bank communications for trading biases.
    
    Sources:
    - Rate decisions
    - Meeting minutes
    - Policy statements
    - Governor speeches
    
    Uses TextBlob + VADER + keyword matching for sentiment.
    """
    
    # Statement type weights (some are more market-moving)
    STATEMENT_WEIGHTS = {
        'rate_decision': 1.5,
        'press_conference': 1.3,
        'minutes': 1.2,
        'speech': 1.0,
        'report': 0.8,
        'other': 0.5,
    }
    
    def __init__(self):
        """Initialize analyzer"""
        self.feeds = CentralBankFeeds()
        self.sentiment = SentimentEngine()
        
        # Active biases by currency
        self.active_biases: Dict[str, CentralBankBias] = {}
    
    def analyze_recent_statements(
        self,
        hours_back: int = 48
    ) -> Dict[str, CentralBankBias]:
        """
        Analyze recent statements from all central banks.
        
        Args:
            hours_back: How far back to look
            
        Returns:
            Dict mapping currency to bias
        """
        all_statements = self.feeds.get_all_recent(hours_back)
        
        for bank, statements in all_statements.items():
            if statements:
                bias = self._analyze_statements(bank, statements)
                if bias and bias.confidence > 0.3:
                    self.active_biases[bias.currency] = bias
        
        return self.active_biases
    
    def analyze_bank(self, bank: str, hours_back: int = 48) -> Optional[CentralBankBias]:
        """
        Analyze statements from a specific central bank.
        
        Args:
            bank: Bank code (FED, ECB, BOE, BOJ, etc.)
            hours_back: How far back to look
            
        Returns:
            CentralBankBias or None
        """
        statements = self.feeds.get_recent_statements(bank, hours_back)
        
        if not statements:
            return None
        
        bias = self._analyze_statements(bank, statements)
        
        if bias and bias.confidence > 0.3:
            self.active_biases[bias.currency] = bias
            return bias
        
        return None
    
    def get_bias_for_currency(self, currency: str) -> Optional[CentralBankBias]:
        """Get current central bank bias for a currency"""
        currency = currency.upper()
        
        bias = self.active_biases.get(currency)
        
        if bias and bias.is_active():
            return bias
        
        return None
    
    def get_bias_for_pair(self, pair: str) -> Tuple[BiasDirection, float]:
        """
        Get combined central bank bias for a currency pair.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD')
            
        Returns:
            (direction, confidence_adjustment)
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        if len(pair_clean) != 6:
            return BiasDirection.NEUTRAL, 0.0
        
        base_currency = pair_clean[:3]
        quote_currency = pair_clean[3:]
        
        base_bias = self.get_bias_for_currency(base_currency)
        quote_bias = self.get_bias_for_currency(quote_currency)
        
        # Combine biases
        if base_bias and quote_bias:
            # Both have biases - net effect
            base_score = base_bias.sentiment_score * base_bias.confidence
            quote_score = quote_bias.sentiment_score * quote_bias.confidence
            
            # Base bullish = pair up, Quote bullish = pair down
            net_score = base_score - quote_score
            
            if net_score > 0.1:
                direction = BiasDirection.BULLISH
            elif net_score < -0.1:
                direction = BiasDirection.BEARISH
            else:
                direction = BiasDirection.NEUTRAL
            
            conf_adj = abs(net_score) * 0.1  # Max 10% adjustment
            
        elif base_bias:
            direction = base_bias.direction
            conf_adj = base_bias.confidence * 0.05
            
        elif quote_bias:
            # Invert quote bias for pair
            if quote_bias.direction == BiasDirection.BULLISH:
                direction = BiasDirection.BEARISH
            elif quote_bias.direction == BiasDirection.BEARISH:
                direction = BiasDirection.BULLISH
            else:
                direction = BiasDirection.NEUTRAL
            conf_adj = quote_bias.confidence * 0.05
            
        else:
            return BiasDirection.NEUTRAL, 0.0
        
        # Sign the adjustment
        if direction == BiasDirection.BEARISH:
            conf_adj = -conf_adj
        
        return direction, conf_adj
    
    def _analyze_statements(
        self,
        bank: str,
        statements: List[CentralBankStatement]
    ) -> Optional[CentralBankBias]:
        """
        Analyze multiple statements and produce aggregate bias.
        
        Weights by statement type and recency.
        """
        if not statements:
            return None
        
        currency = statements[0].currency
        
        # Analyze each statement
        weighted_scores = []
        total_weight = 0
        total_hawkish = 0
        total_dovish = 0
        
        most_important_statement = None
        highest_weight = 0
        
        for statement in statements:
            # Get type weight
            type_weight = self.STATEMENT_WEIGHTS.get(
                statement.statement_type, 
                self.STATEMENT_WEIGHTS['other']
            )
            
            # Recency weight (more recent = higher weight)
            hours_ago = (datetime.utcnow() - statement.published).total_seconds() / 3600
            recency_weight = max(0.5, 1.0 - hours_ago / 48)
            
            total_weight_for_statement = type_weight * recency_weight
            
            # Analyze sentiment
            text = statement.summary
            
            # Try to get full text for important statements
            if statement.statement_type in ['rate_decision', 'minutes']:
                full_text = self.feeds.fetch_full_statement(statement)
                if full_text:
                    text = full_text
            
            sentiment_result = self.sentiment.analyze(text, context='monetary')
            
            # Accumulate
            weighted_scores.append(
                (sentiment_result.composite_score, total_weight_for_statement)
            )
            total_weight += total_weight_for_statement
            total_hawkish += sentiment_result.hawkish_count
            total_dovish += sentiment_result.dovish_count
            
            # Track most important
            if total_weight_for_statement > highest_weight:
                highest_weight = total_weight_for_statement
                most_important_statement = statement
        
        if total_weight == 0 or most_important_statement is None:
            return None
        
        # Calculate weighted average sentiment
        avg_score = sum(s * w for s, w in weighted_scores) / total_weight
        
        # Determine direction and strength
        if avg_score > 0.3:
            direction = BiasDirection.BULLISH
            if avg_score > 0.6:
                strength = BiasStrength.STRONG
            elif avg_score > 0.4:
                strength = BiasStrength.MEDIUM
            else:
                strength = BiasStrength.WEAK
        elif avg_score < -0.3:
            direction = BiasDirection.BEARISH
            if avg_score < -0.6:
                strength = BiasStrength.STRONG
            elif avg_score < -0.4:
                strength = BiasStrength.MEDIUM
            else:
                strength = BiasStrength.WEAK
        else:
            direction = BiasDirection.NEUTRAL
            strength = BiasStrength.WEAK
        
        # Calculate confidence
        # Higher if: more hawkish/dovish keywords, higher agreement between statements
        keyword_signal = abs(total_hawkish - total_dovish) / max(1, total_hawkish + total_dovish)
        confidence = min(1.0, keyword_signal + abs(avg_score))
        
        # Duration based on statement type
        if most_important_statement.statement_type in ['rate_decision', 'minutes']:
            duration_hours = 8.0  # Longer for official policy
        elif most_important_statement.statement_type == 'speech':
            duration_hours = 6.0
        else:
            duration_hours = 4.0
        
        return CentralBankBias(
            bank=bank,
            currency=currency,
            direction=direction,
            strength=strength,
            sentiment_score=round(avg_score, 3),
            confidence=round(confidence, 3),
            statement_title=most_important_statement.title,
            statement_type=most_important_statement.statement_type,
            analysis_time=datetime.utcnow(),
            bias_expiry=datetime.utcnow() + timedelta(hours=duration_hours),
            hawkish_count=total_hawkish,
            dovish_count=total_dovish
        )
    
    def get_summary(self) -> str:
        """Get human-readable summary of active biases"""
        lines = ["=== Central Bank Sentiment Summary ==="]
        
        active = [b for b in self.active_biases.values() if b.is_active()]
        
        if not active:
            lines.append("No active central bank biases")
        else:
            for bias in active:
                lines.append(
                    f"{bias.bank} ({bias.currency}): {bias.direction.name} "
                    f"[{bias.strength.name}] - {bias.hours_remaining():.1f}h remaining"
                )
                lines.append(f"  Score: {bias.sentiment_score:.2f}, Conf: {bias.confidence:.2f}")
                lines.append(f"  Source: {bias.statement_title[:50]}...")
        
        return "\n".join(lines)
    
    def cleanup_expired(self):
        """Remove expired biases"""
        expired = [
            currency for currency, bias in self.active_biases.items()
            if not bias.is_active()
        ]
        
        for currency in expired:
            del self.active_biases[currency]

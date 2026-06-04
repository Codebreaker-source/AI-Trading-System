"""
Government/Fiscal Policy Analyzer
==================================

Analyzes government fiscal policy, Treasury operations, and political
developments that impact currency markets.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
import re

from .config import (
    BiasDirection, BiasStrength, TIMING,
    FISCAL_BULLISH_KEYWORDS, FISCAL_BEARISH_KEYWORDS
)
from .sentiment_engine import SentimentEngine, SentimentResult


@dataclass
class FiscalBias:
    """Bias derived from fiscal/government analysis"""
    
    currency: str
    direction: BiasDirection
    strength: BiasStrength
    sentiment_score: float
    confidence: float
    
    # Source info
    headline: str
    source: str
    analysis_time: datetime
    bias_expiry: datetime
    
    # Keywords found
    bullish_keywords: int
    bearish_keywords: int
    
    def is_active(self) -> bool:
        return datetime.utcnow() < self.bias_expiry
    
    def hours_remaining(self) -> float:
        delta = self.bias_expiry - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)
    
    def to_dict(self) -> Dict:
        return {
            'currency': self.currency,
            'direction': self.direction.name,
            'strength': self.strength.name,
            'sentiment_score': self.sentiment_score,
            'confidence': self.confidence,
            'headline': self.headline,
            'source': self.source,
            'analysis_time': self.analysis_time.isoformat(),
            'bias_expiry': self.bias_expiry.isoformat(),
        }


@dataclass
class TreasuryAuction:
    """Treasury auction data"""
    
    security_type: str      # 2Y, 5Y, 10Y, 30Y
    auction_date: datetime
    amount: float           # Billion USD
    yield_result: Optional[float]
    bid_to_cover: Optional[float]
    indirect_pct: Optional[float]  # Foreign demand proxy
    
    def is_strong_demand(self) -> bool:
        """Check if auction showed strong demand"""
        if self.bid_to_cover is None:
            return False
        
        # Thresholds vary by security type
        thresholds = {
            '2Y': 2.5,
            '5Y': 2.4,
            '10Y': 2.3,
            '30Y': 2.2,
        }
        
        threshold = thresholds.get(self.security_type, 2.3)
        return self.bid_to_cover >= threshold


class GovernmentAnalyzer:
    """
    Analyzes fiscal policy and government news for trading biases.
    
    Covers:
    - Debt ceiling / government shutdown news
    - Treasury auctions
    - Fiscal stimulus / austerity announcements
    - Credit rating changes
    - Political gridlock / policy uncertainty
    
    Primarily affects USD but methodology extends to other currencies.
    """
    
    # News sources for fiscal policy
    NEWS_SOURCES = {
        'USD': [
            'https://www.reuters.com/markets/us/',
            'https://www.bloomberg.com/markets/economics',
        ],
        'EUR': [
            'https://www.reuters.com/markets/europe/',
        ],
        'GBP': [
            'https://www.reuters.com/world/uk/',
        ],
    }
    
    # High-impact fiscal events
    FISCAL_EVENTS = {
        'debt_ceiling': {'impact': 'high', 'duration_hours': 8},
        'government_shutdown': {'impact': 'high', 'duration_hours': 8},
        'credit_downgrade': {'impact': 'critical', 'duration_hours': 12},
        'stimulus': {'impact': 'medium', 'duration_hours': 6},
        'budget': {'impact': 'medium', 'duration_hours': 6},
        'tax': {'impact': 'medium', 'duration_hours': 6},
    }
    
    def __init__(self):
        """Initialize analyzer"""
        self.sentiment = SentimentEngine()
        
        # Active biases
        self.active_biases: Dict[str, FiscalBias] = {}
        
        # Treasury auction tracking
        self.recent_auctions: List[TreasuryAuction] = []
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    def analyze_fiscal_news(
        self,
        currency: str = 'USD',
        headlines: List[str] = None
    ) -> Optional[FiscalBias]:
        """
        Analyze fiscal/government news for a currency.
        
        Args:
            currency: Currency to analyze (USD, EUR, GBP, etc.)
            headlines: Optional pre-fetched headlines to analyze
            
        Returns:
            FiscalBias or None if no significant signal
        """
        currency = currency.upper()
        
        # Get headlines if not provided
        if headlines is None:
            headlines = self._fetch_fiscal_headlines(currency)
        
        if not headlines:
            return None
        
        # Analyze each headline
        results = []
        bullish_total = 0
        bearish_total = 0
        most_impactful = None
        highest_impact = 0
        
        for headline in headlines:
            sentiment = self.sentiment.analyze(headline, context='fiscal')
            
            # Count fiscal keywords
            bullish = self._count_keywords(headline, FISCAL_BULLISH_KEYWORDS)
            bearish = self._count_keywords(headline, FISCAL_BEARISH_KEYWORDS)
            
            bullish_total += bullish
            bearish_total += bearish
            
            # Check for high-impact events
            impact_score = self._get_event_impact(headline)
            if impact_score > highest_impact:
                highest_impact = impact_score
                most_impactful = headline
            
            results.append(sentiment)
        
        if not results:
            return None
        
        # Aggregate sentiment
        aggregate = self.sentiment.get_dominant_sentiment(results)
        
        # Determine direction
        if bullish_total > bearish_total * 1.5:
            direction = BiasDirection.BULLISH
        elif bearish_total > bullish_total * 1.5:
            direction = BiasDirection.BEARISH
        else:
            direction = BiasDirection.NEUTRAL
        
        # Override with aggregate score if strong
        if aggregate.composite_score > 0.4:
            direction = BiasDirection.BULLISH
        elif aggregate.composite_score < -0.4:
            direction = BiasDirection.BEARISH
        
        # Determine strength
        keyword_imbalance = abs(bullish_total - bearish_total)
        if keyword_imbalance > 5 or abs(aggregate.composite_score) > 0.6:
            strength = BiasStrength.STRONG
        elif keyword_imbalance > 2 or abs(aggregate.composite_score) > 0.4:
            strength = BiasStrength.MEDIUM
        else:
            strength = BiasStrength.WEAK
        
        # Calculate confidence
        confidence = min(1.0, aggregate.confidence + keyword_imbalance * 0.1)
        
        # Only create bias if significant
        if direction == BiasDirection.NEUTRAL and confidence < 0.5:
            return None
        
        # Duration based on event impact
        duration = self._get_duration(most_impactful or headlines[0])
        
        bias = FiscalBias(
            currency=currency,
            direction=direction,
            strength=strength,
            sentiment_score=aggregate.composite_score,
            confidence=round(confidence, 3),
            headline=most_impactful or headlines[0],
            source='fiscal_analysis',
            analysis_time=datetime.utcnow(),
            bias_expiry=datetime.utcnow() + timedelta(hours=duration),
            bullish_keywords=bullish_total,
            bearish_keywords=bearish_total
        )
        
        # Store active bias
        if confidence > 0.3:
            self.active_biases[currency] = bias
        
        return bias
    
    def analyze_treasury_auction(
        self,
        auction: TreasuryAuction
    ) -> Optional[FiscalBias]:
        """
        Analyze Treasury auction results for USD bias.
        
        Strong demand (high bid-to-cover, foreign demand) = USD bullish
        Weak demand = USD bearish
        """
        self.recent_auctions.append(auction)
        
        # Keep only last 10 auctions
        self.recent_auctions = self.recent_auctions[-10:]
        
        # Analyze this auction
        if auction.bid_to_cover is None:
            return None
        
        is_strong = auction.is_strong_demand()
        
        # Check indirect (foreign) demand
        foreign_strong = False
        if auction.indirect_pct is not None:
            # Typical indirect is 60-70%, above 70% is strong
            foreign_strong = auction.indirect_pct > 70
        
        # Determine direction
        if is_strong and foreign_strong:
            direction = BiasDirection.BULLISH
            strength = BiasStrength.MEDIUM
        elif is_strong or foreign_strong:
            direction = BiasDirection.BULLISH
            strength = BiasStrength.WEAK
        elif auction.bid_to_cover < 2.0:
            direction = BiasDirection.BEARISH
            strength = BiasStrength.WEAK
        else:
            return None  # Neutral auction
        
        headline = f"{auction.security_type} Treasury auction: B/C {auction.bid_to_cover:.2f}"
        
        bias = FiscalBias(
            currency='USD',
            direction=direction,
            strength=strength,
            sentiment_score=0.3 if direction == BiasDirection.BULLISH else -0.3,
            confidence=0.5,
            headline=headline,
            source='treasury_auction',
            analysis_time=datetime.utcnow(),
            bias_expiry=datetime.utcnow() + timedelta(hours=4),
            bullish_keywords=1 if is_strong else 0,
            bearish_keywords=0 if is_strong else 1
        )
        
        return bias
    
    def get_bias_for_currency(self, currency: str) -> Optional[FiscalBias]:
        """Get current fiscal bias for a currency"""
        currency = currency.upper()
        bias = self.active_biases.get(currency)
        
        if bias and bias.is_active():
            return bias
        
        return None
    
    def get_bias_for_pair(self, pair: str) -> Tuple[BiasDirection, float]:
        """
        Get fiscal bias impact on a currency pair.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD')
            
        Returns:
            (direction, confidence_adjustment)
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        if len(pair_clean) != 6:
            return BiasDirection.NEUTRAL, 0.0
        
        base = pair_clean[:3]
        quote = pair_clean[3:]
        
        base_bias = self.get_bias_for_currency(base)
        quote_bias = self.get_bias_for_currency(quote)
        
        # Combine biases
        if base_bias and quote_bias:
            net = base_bias.sentiment_score - quote_bias.sentiment_score
            if net > 0.2:
                direction = BiasDirection.BULLISH
            elif net < -0.2:
                direction = BiasDirection.BEARISH
            else:
                direction = BiasDirection.NEUTRAL
            conf_adj = abs(net) * 0.05
        elif base_bias:
            direction = base_bias.direction
            conf_adj = base_bias.confidence * 0.03
        elif quote_bias:
            # Invert for pair
            if quote_bias.direction == BiasDirection.BULLISH:
                direction = BiasDirection.BEARISH
            elif quote_bias.direction == BiasDirection.BEARISH:
                direction = BiasDirection.BULLISH
            else:
                direction = BiasDirection.NEUTRAL
            conf_adj = quote_bias.confidence * 0.03
        else:
            return BiasDirection.NEUTRAL, 0.0
        
        if direction == BiasDirection.BEARISH:
            conf_adj = -conf_adj
        
        return direction, conf_adj
    
    def _fetch_fiscal_headlines(self, currency: str) -> List[str]:
        """Fetch recent fiscal headlines for a currency"""
        # This is a placeholder - in production, would scrape news sources
        # For now, return empty list (headlines would be provided externally)
        return []
    
    def _count_keywords(self, text: str, keywords: set) -> int:
        """Count keyword occurrences in text"""
        text_lower = text.lower()
        count = 0
        for keyword in keywords:
            if keyword.lower() in text_lower:
                count += 1
        return count
    
    def _get_event_impact(self, headline: str) -> float:
        """Get impact score for fiscal event"""
        headline_lower = headline.lower()
        
        for event, info in self.FISCAL_EVENTS.items():
            if event in headline_lower:
                if info['impact'] == 'critical':
                    return 1.0
                elif info['impact'] == 'high':
                    return 0.7
                elif info['impact'] == 'medium':
                    return 0.5
        
        return 0.3  # Default low impact
    
    def _get_duration(self, headline: str) -> float:
        """Get bias duration based on event type"""
        headline_lower = headline.lower()
        
        for event, info in self.FISCAL_EVENTS.items():
            if event in headline_lower:
                return info['duration_hours']
        
        return 4.0  # Default 4 hours
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        lines = ["=== Fiscal Policy Analysis ==="]
        
        active = [b for b in self.active_biases.values() if b.is_active()]
        
        if not active:
            lines.append("No active fiscal biases")
        else:
            for bias in active:
                lines.append(
                    f"{bias.currency}: {bias.direction.name} [{bias.strength.name}]"
                )
                lines.append(f"  {bias.headline[:60]}...")
                lines.append(f"  Expires in {bias.hours_remaining():.1f}h")
        
        if self.recent_auctions:
            lines.append("\n--- Recent Treasury Auctions ---")
            for auction in self.recent_auctions[-3:]:
                lines.append(
                    f"  {auction.security_type}: B/C {auction.bid_to_cover or 'N/A'}"
                )
        
        return "\n".join(lines)
    
    def cleanup_expired(self):
        """Remove expired biases"""
        expired = [
            currency for currency, bias in self.active_biases.items()
            if not bias.is_active()
        ]
        for currency in expired:
            del self.active_biases[currency]

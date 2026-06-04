"""
Central Bank RSS Feeds
=======================

Fetches and parses news/statements from major central banks:
- Federal Reserve (Fed)
- European Central Bank (ECB)
- Bank of England (BOE)
- Bank of Japan (BOJ)
- Reserve Bank of Australia (RBA)
- Bank of Canada (BOC)
- Reserve Bank of New Zealand (RBNZ)
- Swiss National Bank (SNB)

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
import re


@dataclass
class CentralBankStatement:
    """Container for a central bank statement/release"""
    
    bank: str                    # Fed, ECB, BOE, BOJ, etc.
    currency: str                # USD, EUR, GBP, JPY, etc.
    title: str
    summary: str
    full_text: Optional[str]
    url: str
    published: datetime
    statement_type: str          # rate_decision, minutes, speech, report
    
    def to_dict(self) -> Dict:
        return {
            'bank': self.bank,
            'currency': self.currency,
            'title': self.title,
            'summary': self.summary,
            'url': self.url,
            'published': self.published.isoformat(),
            'statement_type': self.statement_type,
        }


class CentralBankFeeds:
    """
    Fetches statements and news from central bank RSS feeds.
    
    Used for sentiment analysis on monetary policy.
    """
    
    # RSS Feed URLs (some banks don't have RSS, use alternative)
    FEEDS = {
        'FED': {
            'currency': 'USD',
            'rss': 'https://www.federalreserve.gov/feeds/press_all.xml',
            'backup_url': 'https://www.federalreserve.gov/newsevents/pressreleases.htm',
        },
        'ECB': {
            'currency': 'EUR',
            'rss': None,  # ECB doesn't have clean RSS
            'backup_url': 'https://www.ecb.europa.eu/press/pr/html/index.en.html',
        },
        'BOE': {
            'currency': 'GBP',
            'rss': None,
            'backup_url': 'https://www.bankofengland.co.uk/news',
        },
        'BOJ': {
            'currency': 'JPY',
            'rss': None,
            'backup_url': 'https://www.boj.or.jp/en/mopo/index.htm',
        },
        'RBA': {
            'currency': 'AUD',
            'rss': None,
            'backup_url': 'https://www.rba.gov.au/media-releases/',
        },
        'BOC': {
            'currency': 'CAD',
            'rss': None,
            'backup_url': 'https://www.bankofcanada.ca/press/',
        },
        'RBNZ': {
            'currency': 'NZD',
            'rss': None,
            'backup_url': 'https://www.rbnz.govt.nz/news',
        },
        'SNB': {
            'currency': 'CHF',
            'rss': None,
            'backup_url': 'https://www.snb.ch/en/mmr/reference/pre_all/source',
        },
    }
    
    # Keywords to identify statement types
    STATEMENT_TYPES = {
        'rate_decision': ['rate decision', 'interest rate', 'policy rate', 'funds rate', 
                         'monetary policy decision', 'policy decision'],
        'minutes': ['minutes', 'meeting minutes', 'fomc minutes', 'mpc minutes'],
        'speech': ['speech', 'remarks', 'testimony', 'address', 'powell', 'lagarde', 
                  'bailey', 'ueda', 'governor'],
        'report': ['report', 'outlook', 'projections', 'forecast', 'financial stability',
                  'monetary policy report'],
        'press_conference': ['press conference', 'q&a', 'presser'],
    }
    
    def __init__(self, cache_minutes: int = 15):
        """Initialize with cache duration"""
        self.cache_minutes = cache_minutes
        self._cache: Dict[str, List[CentralBankStatement]] = {}
        self._cache_times: Dict[str, datetime] = {}
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    def get_recent_statements(
        self,
        bank: str,
        hours_back: int = 48,
        force_refresh: bool = False
    ) -> List[CentralBankStatement]:
        """
        Get recent statements from a central bank.
        
        Args:
            bank: Bank code (FED, ECB, BOE, BOJ, RBA, BOC, RBNZ, SNB)
            hours_back: How far back to look
            force_refresh: Bypass cache
            
        Returns:
            List of CentralBankStatement objects
        """
        bank = bank.upper()
        
        if bank not in self.FEEDS:
            print(f"[CentralBank] Unknown bank: {bank}")
            return []
        
        # Check cache
        if not force_refresh and self._is_cache_valid(bank):
            return self._filter_by_time(self._cache[bank], hours_back)
        
        # Fetch new data
        feed_info = self.FEEDS[bank]
        statements = []
        
        if feed_info.get('rss'):
            statements = self._fetch_rss(bank, feed_info)
        else:
            statements = self._fetch_backup(bank, feed_info)
        
        # Cache results
        self._cache[bank] = statements
        self._cache_times[bank] = datetime.utcnow()
        
        return self._filter_by_time(statements, hours_back)
    
    def get_all_recent(self, hours_back: int = 48) -> Dict[str, List[CentralBankStatement]]:
        """Get recent statements from all banks"""
        results = {}
        
        for bank in self.FEEDS.keys():
            statements = self.get_recent_statements(bank, hours_back)
            if statements:
                results[bank] = statements
        
        return results
    
    def get_statements_for_currency(
        self, 
        currency: str,
        hours_back: int = 48
    ) -> List[CentralBankStatement]:
        """Get statements affecting a specific currency"""
        currency = currency.upper()
        
        # Find bank for this currency
        for bank, info in self.FEEDS.items():
            if info['currency'] == currency:
                return self.get_recent_statements(bank, hours_back)
        
        return []
    
    def _fetch_rss(self, bank: str, feed_info: Dict) -> List[CentralBankStatement]:
        """Fetch and parse RSS feed"""
        statements = []
        
        try:
            feed = feedparser.parse(feed_info['rss'])
            
            for entry in feed.entries[:20]:  # Limit to recent 20
                try:
                    # Parse date
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published = datetime(*entry.updated_parsed[:6])
                    else:
                        published = datetime.utcnow()
                    
                    # Get content
                    title = entry.title if hasattr(entry, 'title') else ''
                    summary = entry.summary if hasattr(entry, 'summary') else ''
                    url = entry.link if hasattr(entry, 'link') else ''
                    
                    # Clean HTML from summary
                    summary = self._clean_html(summary)
                    
                    # Determine statement type
                    statement_type = self._classify_statement(title + ' ' + summary)
                    
                    statements.append(CentralBankStatement(
                        bank=bank,
                        currency=feed_info['currency'],
                        title=title,
                        summary=summary[:500],  # Truncate
                        full_text=None,
                        url=url,
                        published=published,
                        statement_type=statement_type
                    ))
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"[CentralBank] RSS error for {bank}: {e}")
        
        return statements
    
    def _fetch_backup(self, bank: str, feed_info: Dict) -> List[CentralBankStatement]:
        """Fetch from website when RSS not available"""
        statements = []
        
        try:
            response = requests.get(
                feed_info['backup_url'],
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Bank-specific parsing
            if bank == 'FED':
                statements = self._parse_fed_page(soup, feed_info['currency'])
            elif bank == 'ECB':
                statements = self._parse_ecb_page(soup, feed_info['currency'])
            elif bank == 'BOE':
                statements = self._parse_generic_news(soup, bank, feed_info['currency'])
            else:
                statements = self._parse_generic_news(soup, bank, feed_info['currency'])
                
        except Exception as e:
            print(f"[CentralBank] Backup fetch error for {bank}: {e}")
        
        return statements
    
    def _parse_fed_page(self, soup: BeautifulSoup, currency: str) -> List[CentralBankStatement]:
        """Parse Federal Reserve press releases page"""
        statements = []
        
        # Find news items
        news_items = soup.find_all('div', class_='row')
        
        for item in news_items[:15]:
            try:
                # Find date
                date_elem = item.find('time') or item.find(class_='ng-binding')
                if date_elem:
                    date_text = date_elem.get('datetime') or date_elem.text.strip()
                    try:
                        published = datetime.strptime(date_text[:10], '%Y-%m-%d')
                    except:
                        published = datetime.utcnow()
                else:
                    published = datetime.utcnow()
                
                # Find title and link
                link_elem = item.find('a')
                if link_elem:
                    title = link_elem.text.strip()
                    url = 'https://www.federalreserve.gov' + link_elem.get('href', '')
                else:
                    continue
                
                statement_type = self._classify_statement(title)
                
                statements.append(CentralBankStatement(
                    bank='FED',
                    currency=currency,
                    title=title,
                    summary=title,
                    full_text=None,
                    url=url,
                    published=published,
                    statement_type=statement_type
                ))
                
            except Exception:
                continue
        
        return statements
    
    def _parse_ecb_page(self, soup: BeautifulSoup, currency: str) -> List[CentralBankStatement]:
        """Parse ECB press releases page"""
        statements = []
        
        # Find press releases
        items = soup.find_all('dd', class_='ecb-pressItem')
        
        for item in items[:15]:
            try:
                date_elem = item.find('dt')
                link_elem = item.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.text.strip()
                url = 'https://www.ecb.europa.eu' + link_elem.get('href', '')
                
                # Parse date
                if date_elem:
                    date_text = date_elem.text.strip()
                    try:
                        published = datetime.strptime(date_text, '%d %B %Y')
                    except:
                        published = datetime.utcnow()
                else:
                    published = datetime.utcnow()
                
                statement_type = self._classify_statement(title)
                
                statements.append(CentralBankStatement(
                    bank='ECB',
                    currency=currency,
                    title=title,
                    summary=title,
                    full_text=None,
                    url=url,
                    published=published,
                    statement_type=statement_type
                ))
                
            except Exception:
                continue
        
        return statements
    
    def _parse_generic_news(
        self, 
        soup: BeautifulSoup, 
        bank: str, 
        currency: str
    ) -> List[CentralBankStatement]:
        """Generic parser for news pages"""
        statements = []
        
        # Find common news item patterns
        for selector in ['article', '.news-item', '.press-release', 'li']:
            items = soup.select(selector)[:15]
            
            for item in items:
                try:
                    link = item.find('a')
                    if not link:
                        continue
                    
                    title = link.text.strip()
                    if len(title) < 10:
                        continue
                    
                    url = link.get('href', '')
                    
                    statement_type = self._classify_statement(title)
                    
                    statements.append(CentralBankStatement(
                        bank=bank,
                        currency=currency,
                        title=title,
                        summary=title,
                        full_text=None,
                        url=url,
                        published=datetime.utcnow(),  # Date parsing varies
                        statement_type=statement_type
                    ))
                    
                except Exception:
                    continue
            
            if statements:
                break
        
        return statements
    
    def _classify_statement(self, text: str) -> str:
        """Classify statement type based on keywords"""
        text_lower = text.lower()
        
        for stmt_type, keywords in self.STATEMENT_TYPES.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return stmt_type
        
        return 'other'
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text(separator=' ').strip()
    
    def _filter_by_time(
        self, 
        statements: List[CentralBankStatement],
        hours_back: int
    ) -> List[CentralBankStatement]:
        """Filter statements by time"""
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        return [s for s in statements if s.published >= cutoff]
    
    def _is_cache_valid(self, bank: str) -> bool:
        """Check if cache is still valid"""
        if bank not in self._cache_times:
            return False
        
        age = datetime.utcnow() - self._cache_times[bank]
        return age < timedelta(minutes=self.cache_minutes)
    
    def fetch_full_statement(self, statement: CentralBankStatement) -> Optional[str]:
        """
        Fetch full text of a statement for deeper analysis.
        
        Args:
            statement: Statement to fetch full text for
            
        Returns:
            Full text content or None
        """
        if not statement.url:
            return None
        
        try:
            response = requests.get(
                statement.url,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try common content selectors
            for selector in ['article', '.content', '#content', 'main', '.body']:
                content = soup.select_one(selector)
                if content:
                    text = content.get_text(separator=' ')
                    # Clean up whitespace
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text[:5000]  # Limit size
            
            # Fallback to body
            return soup.body.get_text(separator=' ')[:5000] if soup.body else None
            
        except Exception as e:
            print(f"[CentralBank] Error fetching full statement: {e}")
            return None

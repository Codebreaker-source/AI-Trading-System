"""
News Analysis Data Sources
===========================

Data source modules for economic calendar, FRED API, and central bank feeds.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from .forexfactory import ForexFactoryScraper, EconomicEvent
from .fred_api import FREDClient, EconomicDataPoint
from .central_bank_feeds import CentralBankFeeds, CentralBankStatement

__all__ = [
    'ForexFactoryScraper',
    'EconomicEvent',
    'FREDClient',
    'EconomicDataPoint',
    'CentralBankFeeds',
    'CentralBankStatement',
]

"""
Unified Trade Logger
=====================
One master CSV capturing every signal from every source with full context.
One row per (symbol, source, signal) — updated when trade executes and closes.

Columns:
  trade_id | timestamp | symbol | signal_source | source_type | action |
  confidence | confluence_score | dimension_votes | danger_score |
  strategy_votes | close | rsi | atr | momentum | volatility |
  would_execute | actually_executed |
  entry_price | sl | tp | lot |
  exit_time | exit_price | outcome | profit_pips | profit_usd
"""

import os
import uuid
import logging
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

COLUMNS = [
    "trade_id", "timestamp", "symbol", "signal_source", "source_type", "action",
    # ML/gate context
    "confidence", "confluence_score", "dimension_votes", "dimension_count",
    "danger_score", "strategy_votes",
    # Key indicators at signal time
    "close", "rsi", "atr", "momentum", "volatility",
    # Execution flags
    "would_execute", "actually_executed",
    # Order details
    "entry_price", "sl", "tp", "lot",
    # Outcome (filled when trade closes)
    "exit_time", "exit_price", "outcome", "profit_pips", "profit_usd",
    # Outcome detail (filled by trade_outcome_simulator)
    "exit_reason", "mfe_pips", "mae_pips", "trade_duration_minutes", "label_quality",
]


def make_trade_id(symbol: str, source: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    sym = symbol.replace(".sim", "").replace(".", "")[:6]
    src = source[:8]
    return f"{ts}_{sym}_{src}"


class UnifiedTradeLogger:
    """
    Append-only logger for all trade signals and outcomes.
    Thread-safe via file append (each write is atomic at OS level).
    """

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._pending: dict[str, dict] = {}  # trade_id -> row dict

        if not self.log_path.exists():
            pd.DataFrame(columns=COLUMNS).to_csv(self.log_path, index=False)
            logger.info(f"[UNIFIED LOG] Created: {self.log_path}")

    # ------------------------------------------------------------------
    # Log a new signal (call when signal is generated, before execution)
    # ------------------------------------------------------------------

    def log_signal(
        self,
        trade_id: str,
        symbol: str,
        signal_source: str,
        source_type: str,
        action: str,
        # gate context (optional — only present for XGBoost signals)
        confidence: float = 0.0,
        confluence_score: float = 0.0,
        dimension_votes: str = "",
        dimension_count: int = 0,
        danger_score: float = 0.0,
        strategy_votes: str = "",
        # indicator snapshot
        close: float = 0.0,
        rsi: float = 0.0,
        atr: float = 0.0,
        momentum: float = 0.0,
        volatility: float = 0.0,
        # execution status
        would_execute: bool = True,
        actually_executed: bool = False,
    ) -> str:
        """Write signal row. Returns trade_id."""
        row = {
            "trade_id":          trade_id,
            "timestamp":         datetime.now(timezone.utc).isoformat(),
            "symbol":            symbol,
            "signal_source":     signal_source,
            "source_type":       source_type,
            "action":            action,
            "confidence":        round(confidence, 4),
            "confluence_score":  round(confluence_score, 4),
            "dimension_votes":   dimension_votes,
            "dimension_count":   dimension_count,
            "danger_score":      round(danger_score, 2),
            "strategy_votes":    strategy_votes,
            "close":             round(close, 6),
            "rsi":               round(rsi, 2),
            "atr":               round(atr, 6),
            "momentum":          round(momentum, 6),
            "volatility":        round(volatility, 4),
            "would_execute":     would_execute,
            "actually_executed": actually_executed,
            "entry_price": "", "sl": "", "tp": "", "lot": "",
            "exit_time": "", "exit_price": "", "outcome": "",
            "profit_pips": "", "profit_usd": "",
            "exit_reason": "", "mfe_pips": "", "mae_pips": "",
            "trade_duration_minutes": "", "label_quality": "",
        }
        self._pending[trade_id] = row
        self._append_row(row)
        return trade_id

    # ------------------------------------------------------------------
    # Update when EA confirms execution
    # ------------------------------------------------------------------

    def log_execution(
        self,
        trade_id: str,
        entry_price: float,
        sl: float,
        tp: float,
        lot: float,
    ):
        """Mark signal as actually executed and fill order details."""
        self._update_row(trade_id, {
            "actually_executed": True,
            "entry_price":       round(entry_price, 6),
            "sl":                round(sl, 6),
            "tp":                round(tp, 6),
            "lot":               round(lot, 2),
        })

    # ------------------------------------------------------------------
    # Update when trade closes
    # ------------------------------------------------------------------

    def log_outcome(
        self,
        trade_id: str,
        exit_price: float,
        outcome: str,       # 'TP' | 'SL' | 'BE' | 'PARTIAL_TP' | 'MANUAL' | 'OPEN'
        profit_pips: float,
        profit_usd: float,
        exit_reason: str = "",
        mfe_pips: float = 0.0,
        mae_pips: float = 0.0,
        trade_duration_minutes: float = 0.0,
        label_quality: str = "",   # 'tick' | 'm1_approx'
        exit_time: Optional[datetime] = None,
    ):
        """Fill outcome columns when trade closes (or finalizes a label)."""
        self._update_row(trade_id, {
            "exit_time":   (exit_time or datetime.now(timezone.utc)).isoformat(),
            "exit_price":  round(exit_price, 6),
            "outcome":     outcome,
            "profit_pips": round(profit_pips, 1),
            "profit_usd":  round(profit_usd, 2),
            "exit_reason": exit_reason,
            "mfe_pips":    round(mfe_pips, 1),
            "mae_pips":    round(mae_pips, 1),
            "trade_duration_minutes": round(trade_duration_minutes, 1),
            "label_quality": label_quality,
        })

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _append_row(self, row: dict):
        try:
            df = pd.DataFrame([row], columns=COLUMNS)
            df.to_csv(self.log_path, mode="a", header=False, index=False)
        except Exception as e:
            logger.error(f"[UNIFIED LOG] Append failed: {e}")

    def _update_row(self, trade_id: str, updates: dict):
        """Update an existing row in-place by rewriting the file."""
        try:
            df = pd.read_csv(self.log_path, dtype=str)
            mask = df["trade_id"] == trade_id
            if not mask.any():
                logger.warning(f"[UNIFIED LOG] trade_id {trade_id} not found for update")
                return
            for col, val in updates.items():
                df.loc[mask, col] = str(val)
            df.to_csv(self.log_path, index=False)
        except Exception as e:
            logger.error(f"[UNIFIED LOG] Update failed for {trade_id}: {e}")

    def get_summary(self) -> dict:
        """Quick stats for logging."""
        try:
            df = pd.read_csv(self.log_path)
            total    = len(df)
            executed = df["actually_executed"].astype(str).str.lower().eq("true").sum()
            closed   = df["outcome"].notna().sum()
            return {"total_signals": total, "executed": executed, "closed": closed}
        except Exception:
            return {}

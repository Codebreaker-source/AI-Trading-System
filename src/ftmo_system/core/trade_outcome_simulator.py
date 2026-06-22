"""
Tick-Based Outcome Simulator
=============================
Background loop that turns logged signals (data/unified_trades.csv,
actually_executed=True, outcome=='') into fully labeled training rows
by replaying MT5 tick data (fallback: M1 bars) through the same
break-even / partial-TP / regime-trailing logic the live EA uses
(core/exit_logic.py).

Entry/SL/TP are reconstructed the same way live_trading_system.py
computes them at signal time (~live_trading_system.py lines 792-805):
  SL = entry - 1.5*ATR (BUY) / entry + 1.5*ATR (SELL)
  TP = entry + 3.0*ATR (BUY) / entry - 3.0*ATR (SELL)
using the `close` and `atr` columns already captured in unified_trades.csv.

Run via `run_forever()` in a background thread from run_system.py.
"""

import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from core.exit_logic import ExitParams, PositionState, step_position
from core.unified_trade_logger import UnifiedTradeLogger
from core.feature_history_recorder import FeatureHistoryRecorder, SEQUENCE_LENGTH

TICK_TRAJECTORY_LENGTH = 200

logger = logging.getLogger(__name__)

SL_ATR_MULT = 1.5
TP_ATR_MULT = 3.0
MAX_HOLD_HOURS = 48
POLL_SECONDS = 30
MIN_AGE_SECONDS = 60  # don't replay a signal until at least this old


_INDEX_CRYPTO_KEYWORDS = (
    "US500", "US100", "US30", "UK100", "GER", "GER40", "JP225", "AUS200",
    "FRA40", "EU50", "NAS", "SPX", "DJ30",
    "BTC", "ETH", "LTC", "XRP",
    "OIL", "USOIL", "UKOIL", "NGAS",
)


def _pip_value(symbol: str) -> float:
    """
    Approximate 'pip' size in price units, by symbol category.
    Forex majors/minors: 0.0001 (0.01 for JPY pairs).
    Metals (XAU/XAG): 0.01 (1 pip = $0.01).
    Indices/crypto/energy: 1.0 (1 'pip' = 1 point/dollar) — pip-based
    P&L is not meaningful for these, but this avoids wildly inflated
    profit_pips from applying a forex pip size to a $60,000 BTC move.
    """
    s = symbol.upper()
    if any(k in s for k in _INDEX_CRYPTO_KEYWORDS):
        return 1.0
    if "XAU" in s or "XAG" in s:
        return 0.01
    if "JPY" in s:
        return 0.01
    return 0.0001


class TradeOutcomeSimulator:
    def __init__(self, unified_trades_path: str, exit_params: ExitParams = None):
        self.path = Path(unified_trades_path)
        self.unified_logger = UnifiedTradeLogger(str(self.path))
        self.params = exit_params or ExitParams()
        self._stop = False

        data_dir = self.path.parent
        self.feature_history = FeatureHistoryRecorder(str(data_dir / "feature_history"))
        self.sequences_dir = data_dir / "feature_sequences"
        self.sequences_dir.mkdir(parents=True, exist_ok=True)
        self.tick_trajectories_dir = data_dir / "tick_trajectories"
        self.tick_trajectories_dir.mkdir(parents=True, exist_ok=True)

    def stop(self):
        self._stop = True

    def run_forever(self):
        logger.info("[SIM] Trade outcome simulator started")
        while not self._stop:
            try:
                self.process_pending()
            except Exception as e:
                logger.error(f"[SIM] cycle error: {e}")
            time.sleep(POLL_SECONDS)

    # ------------------------------------------------------------------

    def process_pending(self):
        if not self.path.exists():
            return
        try:
            df = pd.read_csv(self.path, dtype=str)
        except Exception as e:
            logger.error(f"[SIM] read failed: {e}")
            return
        if df.empty:
            return

        mask = (
            df["actually_executed"].astype(str).str.lower().eq("true")
            & df["action"].isin(["BUY", "SELL"])
            & df["outcome"].fillna("").eq("")
        )
        pending = df[mask]
        if pending.empty:
            return

        now = datetime.now(timezone.utc)
        for _, row in pending.iterrows():
            try:
                signal_time = pd.to_datetime(row["timestamp"], utc=True).to_pydatetime()
                if (now - signal_time).total_seconds() < MIN_AGE_SECONDS:
                    continue
                self._process_row(row, signal_time, now)
            except Exception as e:
                logger.error(f"[SIM] failed for {row.get('trade_id')}: {e}")

    def _process_row(self, row, signal_time: datetime, now: datetime):
        trade_id = row["trade_id"]
        symbol = row["symbol"]
        action = row["action"]
        close = float(row["close"])
        atr = float(row["atr"])

        if atr <= 0 or close <= 0:
            return

        pip = _pip_value(symbol)
        entry = close
        if action == "BUY":
            sl = entry - atr * SL_ATR_MULT
            tp = entry + atr * TP_ATR_MULT
        else:
            sl = entry + atr * SL_ATR_MULT
            tp = entry - atr * TP_ATR_MULT

        if str(row.get("entry_price", "")).strip() == "":
            self.unified_logger.log_execution(trade_id, entry, sl, tp, lot=0.01)

        path, label_quality = self._get_price_path(symbol, signal_time, now)
        if not path:
            return  # no data yet — try again next poll

        state = PositionState(entry=entry, sl=sl, tp=tp, direction=action, vol=0.01)
        outcome = None
        exit_price = None
        exit_time = None

        for ts, bid, ask in path:
            current = bid if action == "BUY" else ask

            if action == "BUY":
                if current <= state.sl:
                    outcome = "BE" if abs(state.sl - entry) < pip else "SL"
                    exit_price = state.sl
                    exit_time = ts
                    break
                if current >= state.tp:
                    outcome = "PARTIAL_TP" if state.partial_tp_taken else "TP"
                    exit_price = state.tp
                    exit_time = ts
                    break
            else:
                if current >= state.sl:
                    outcome = "BE" if abs(state.sl - entry) < pip else "SL"
                    exit_price = state.sl
                    exit_time = ts
                    break
                if current <= state.tp:
                    outcome = "PARTIAL_TP" if state.partial_tp_taken else "TP"
                    exit_price = state.tp
                    exit_time = ts
                    break

            state = step_position(state, current, bid, ask, atr, pip, self.params)

        if outcome is None:
            if (now - signal_time) > timedelta(hours=MAX_HOLD_HOURS):
                last_ts, last_bid, last_ask = path[-1]
                exit_price = last_bid if action == "BUY" else last_ask
                exit_time = last_ts
                outcome = "MANUAL"
            else:
                return  # still open — re-check next poll

        if action == "BUY":
            profit_pips = (exit_price - entry) / pip
        else:
            profit_pips = (entry - exit_price) / pip
        profit_usd = profit_pips * pip * 100000 * state.vol

        duration_min = (exit_time - signal_time).total_seconds() / 60.0

        self._write_feature_sequence(trade_id, symbol, signal_time)
        self._write_tick_trajectory(trade_id, path, exit_time)

        self.unified_logger.log_outcome(
            trade_id=trade_id,
            exit_price=exit_price,
            outcome=outcome,
            profit_pips=profit_pips,
            profit_usd=profit_usd,
            exit_reason=outcome,
            mfe_pips=state.mfe_pips,
            mae_pips=state.mae_pips,
            trade_duration_minutes=duration_min,
            label_quality=label_quality,
            exit_time=exit_time,
        )
        logger.info(
            f"[SIM] {trade_id} {symbol} {action} -> {outcome} "
            f"({profit_pips:.1f} pips, {label_quality})"
        )

    # ------------------------------------------------------------------

    def _write_feature_sequence(self, trade_id: str, symbol: str, signal_time: datetime):
        seq = self.feature_history.get_sequence(symbol, before=signal_time, length=SEQUENCE_LENGTH)
        if seq is None:
            return
        try:
            np.save(self.sequences_dir / f"{trade_id}.npy", seq)
        except Exception as e:
            logger.error(f"[SIM] feature sequence save failed for {trade_id}: {e}")

    def _write_tick_trajectory(self, trade_id: str, path: list, exit_time: datetime):
        """Sample (timestamp, bid, ask) path up to exit_time down to a fixed length."""
        trimmed = [p for p in path if p[0] <= exit_time]
        if len(trimmed) < 2:
            return
        try:
            arr = np.array([[p[1], p[2]] for p in trimmed], dtype=np.float32)
            if len(arr) > TICK_TRAJECTORY_LENGTH:
                idx = np.linspace(0, len(arr) - 1, TICK_TRAJECTORY_LENGTH).astype(int)
                arr = arr[idx]
            np.save(self.tick_trajectories_dir / f"{trade_id}.npy", arr)
        except Exception as e:
            logger.error(f"[SIM] tick trajectory save failed for {trade_id}: {e}")

    # ------------------------------------------------------------------

    def _get_price_path(self, symbol: str, start: datetime, end: datetime):
        """Return (list of (timestamp, bid, ask), label_quality) or (None, '')."""
        if mt5 is None:
            return None, ""

        ticks = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
        if ticks is not None and len(ticks) > 0:
            path = []
            for t in ticks:
                bid = float(t["bid"])
                ask = float(t["ask"])
                if bid > 0 and ask > 0:
                    path.append((datetime.fromtimestamp(t["time"], tz=timezone.utc), bid, ask))
            if path:
                return path, "tick"

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
        if rates is not None and len(rates) > 0:
            path = []
            for r in rates:
                ts = datetime.fromtimestamp(r["time"], tz=timezone.utc)
                for price in (r["open"], r["high"], r["low"], r["close"]):
                    p = float(price)
                    path.append((ts, p, p))
            if path:
                return path, "m1_approx"

        return None, ""

"""
Profit-aware 3-tier trade labeling for ML training.

Outcome values written by BridgeEA_FTMO_v1 (from DEAL_REASON):
  "TP"    — actual take-profit order hit               → correct direction, full weight
  "TRAIL" — trailing stop closed while in profit       → correct direction, half weight
  "SL"    — stop loss closed at a loss                 → wrong direction,  full weight
  "HOLD"  — no trade taken / filtered out              → HOLD label,       full weight

Label encoding (MUST match all pretrained models):
  0 = SELL
  1 = HOLD
  2 = BUY

Backward compatibility:
  Legacy logs only have "TP" and "SL" (no "TRAIL").  The function handles this
  gracefully — "TP" still maps to full-weight directional, "SL" still maps to
  opposite-direction full-weight.
"""

from __future__ import annotations

LABEL_SELL = 0
LABEL_HOLD = 1
LABEL_BUY  = 2


def label_trade(direction: str, outcome: str) -> tuple[int, float]:
    """
    Convert one execution-log row into a (label, sample_weight) pair.

    Parameters
    ----------
    direction : str   "BUY" or "SELL"
    outcome   : str   "TP", "TRAIL", "SL", or anything else (→ HOLD)

    Returns
    -------
    (label: int, weight: float)
        label  ∈ {LABEL_SELL=0, LABEL_HOLD=1, LABEL_BUY=2}
        weight ∈ {0.5, 1.0}

    Labeling rules
    --------------
    Outcome  Direction  Label   Weight  Rationale
    -------- ---------- ------- ------- -----------------------------------------
    TP       BUY        BUY     1.0     Strong correct signal — reached target
    TP       SELL       SELL    1.0     Strong correct signal — reached target
    TRAIL    BUY        BUY     0.5     Correct direction but didn't reach target
    TRAIL    SELL       SELL    0.5     Correct direction but didn't reach target
    SL       BUY        SELL    1.0     Wrong direction — should have sold
    SL       SELL       BUY     1.0     Wrong direction — should have bought
    other    *          HOLD    1.0     No trade / unknown outcome
    """
    d = str(direction).upper().strip()
    o = str(outcome).upper().strip()

    if o == "TP":
        if d == "BUY":
            return LABEL_BUY,  1.0
        if d == "SELL":
            return LABEL_SELL, 1.0

    elif o == "TRAIL":
        # Correct direction — price moved our way — but trailing stop
        # fired before the full TP target was reached.  Treat as a
        # weaker confirmation of the direction.
        if d == "BUY":
            return LABEL_BUY,  0.5
        if d == "SELL":
            return LABEL_SELL, 0.5

    elif o == "SL":
        # Stopped out at a loss — the direction call was wrong.
        if d == "BUY":
            return LABEL_SELL, 1.0
        if d == "SELL":
            return LABEL_BUY,  1.0

    # HOLD / unrecognised outcome
    return LABEL_HOLD, 1.0


def label_dataframe(df, direction_col: str = "direction",
                    outcome_col: str = "outcome"):
    """
    Apply label_trade() to every row of a DataFrame.

    Returns two Series: (labels, weights) — both aligned with df.index.
    """
    import pandas as pd
    results = df.apply(
        lambda r: label_trade(r[direction_col], r[outcome_col]), axis=1
    )
    labels  = results.map(lambda t: t[0]).astype(int)
    weights = results.map(lambda t: t[1]).astype(float)
    return labels, weights

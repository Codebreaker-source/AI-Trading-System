# VERSION TIMELINE

Maps system versions to dates, code changes, and execution results.

## Timeline Overview

```
2025-09 ─────────────────────────────────────────────────────────
         │ Phase 1: Simple Azure Function
         │ Phase 2: Neural Network Exploration
         │
2025-10 ─┼─ v73: Initial LITE deployment
         │       EA v1.0 → v2.03
         │       Bug: Data loss in accumulator
         │
2025-11 ─┼─ v74-v77: Confluence system development
         │       EA v2.16 → v2.22
         │       8-factor scoring implemented
         │
         ├─ v78-v80: CLEAN27 feature reduction
         │       58 → 27 features
         │       Accuracy: 70.4% avg
         │
2025-12 ─┼─ v82-v84: Optimization phase
         │       Confidence calibration fixes
         │       BE/Trailing research
         │
2026-01 ─┼─ v85: SOLUTION 7 DEPLOYED
         │       Direction-aware cooldown
         │       Entry clustering fix
         │       EA v2.32
         │
         └─ v86: Current (MHP sync)
```

## Detailed Version Map

| Version | Date | EA Version | Key Changes | Model Accuracy |
|---------|------|------------|-------------|----------------|
| v86 | 2026-01-23 | v2.32 | MHP sync | 70.4% |
| v85 | 2026-01-11 | v2.32 | Solution 7: Direction cooldown | 70.4% |
| v84 | 2025-12-06 | v2.32 | BE/Trailing research | 70.4% |
| v83 | 2025-12-03 | v2.32 | Calibration fixes | 70.4% |
| v82 | 2025-12-02 | v2.32 | Documentation update | 70.4% |
| v80 | 2025-11-25 | v2.22 | CLEAN27 features | 70.4% |
| v79 | 2025-11-24 | v2.22 | HOLD imbalance fix | ~68% |
| v78 | 2025-11-18 | v2.22 | Scale-in logic | ~68% |
| v77 | 2025-11-17 | v2.22 | ML-only mode | ~68% |
| v76 | 2025-11-17 | v2.19 | 4-dimension system | ~65% |
| v75 | 2025-11-17 | v2.19 | Lot size fix | ~65% |
| v74 | 2025-11-16 | v2.16 | Confluence scoring | ~65% |
| v73 | 2025-11-16 | v2.16 | Feature optimization | ~63% |
| Earlier | 2025-10 | v1.0-v2.03 | Initial development | ~55-60% |

## EA Version History

| EA Version | Date | Features | Notes |
|------------|------|----------|-------|
| v2.34 | 2026-02 | Latest | Testing |
| v2.32 | 2026-01 | STREAK_SIZE | Current production |
| v2.22 | 2025-11 | Trade execution | Stable |
| v2.19 | 2025-11 | Improved SL/TP | - |
| v2.16 | 2025-11 | Basic execution | First stable |
| v2.03 | 2025-10 | Bug fixes | - |
| v1.0 | 2025-10 | Initial | Data extraction only |

## Model Training History

| Model Set | Date | Features | Samples | Notes |
|-----------|------|----------|---------|-------|
| CLEAN27 | 2025-11-25 | 27 | 598K | Current production |
| 105FEAT | 2025-11-16 | 105 | ~2M | Overfit, too many features |
| B1_CLEAN | 2025-11-20 | 58 | ~1.6M | Balanced labels |
| BALANCED | 2025-11-18 | 58 | ~1.6M | Initial balanced |
| indices | 2025-11 | 58 | ~500K | Index instruments |

## Execution Data by Version

Data files in Azure map to versions:

```
Azure: logs/
├── by_version/
│   ├── v2_16/          # Nov 2025 early testing
│   ├── v2_19/          # Nov 2025 mid
│   ├── v2_22/          # Nov-Dec 2025
│   └── v2_32/          # Jan 2026 (current)
│
└── by_date/
    ├── 2025-10/        # Initial testing
    ├── 2025-11/        # Active development
    ├── 2025-12/        # Optimization
    └── 2026-01/        # Solution 7
```

## Key Decision Points

| Date | Decision | Rationale | Outcome |
|------|----------|-----------|---------|
| 2025-11-25 | 58→27 features | Remove noise | +5% accuracy |
| 2025-11-17 | Disable rule-based | ML outperforms | Cleaner signals |
| 2025-11-17 | 4-dimension system | Multi-factor validation | Fewer bad trades |
| 2026-01-11 | Direction cooldown | Entry clustering | Fixed 44% of losses |

## Links

- Full changelog: `CHANGELOG.md`
- Data manifest: `DATA_MANIFEST.json`
- Handoff archives: `docs/handoffs/archive/`

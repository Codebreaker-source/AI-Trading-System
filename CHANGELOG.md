# CHANGELOG

All notable changes to the AI Trading System.

## [v86] - 2026-01-23
### Changed
- Synced with MHP v81-solution7
- Complete system documentation update

## [v85] - 2026-01-11 (Solution 7)
### Added
- Direction-aware cooldown (60 minutes per symbol+direction)
- Allows opposite direction signals for reversals
### Fixed
- Entry clustering issue (44.4% of losses)
- Trailing stop killing winners (39.3% of losses)
### Changed
- EA params: BE_TriggerRR 1.5→1.0
- Disabled EnableProgressiveTrail

## [v84] - 2025-12-06
### Added
- BE/Trailing research documentation
- Advanced exit management analysis

## [v83] - 2025-12-03
### Fixed
- Model confidence calibration improvements
- Profit calculation bug repairs

## [v82] - 2025-12-02
### Changed
- Comprehensive documentation updates
- 8-12 core project files updated

## [v80] - 2025-11-25
### Added
- CLEAN27 feature set (reduced from 58 to 27)
- Removed noise features (correlations, strength indicators)
### Changed
- Model retraining with Dukascopy clean data
- Average accuracy improved to 70.4%

## [v79] - 2025-11-24
### Fixed
- Training data 80% HOLD label imbalance
- Modified ensemble_predictor to use strongest directional signal

## [v78] - 2025-11-18
### Added
- Scale-in logic requiring breakeven first
- Confluence threshold >= 0.40 for additions

## [v77] - 2025-11-17
### Changed
- ML confidence threshold: 0.35
- Confluence threshold: 0.35
- Rule-based strategies DISABLED (ML only mode)

## [v76] - 2025-11-17
### Added
- 4-dimension signal validation system
- Danger scoring (7 categories, 0-21 points)
- Anti-fragile position building

## [v75] - 2025-11-17
### Fixed
- Lot sizing discrepancy (Python 0.10 vs EA 0.01)

## [v74] - 2025-11-16
### Added
- 8-factor confluence scoring system
- 169 candlestick pattern recognition

## [v73] - 2025-11-16
### Changed
- Migration from 105 features to optimized feature set
- Initial model training improvements

---

## Earlier Versions

## [v72 and earlier] - 2025-10 to 2025-11
### Major Milestones
- Initial LITE system deployment
- Bridge EA development (v1.0 → v2.32)
- Data accumulator with backup system
- Azure integration setup
- LSTM → XGBoost/LightGBM migration

## [Initial] - 2025-09 to 2025-10
### Created
- Phase 1: Simple Azure function
- Phase 2: Neural network exploration
- Phase 4: LITE system architecture
- Bridge EA v1.0 for MT5 data extraction

---

## Version Naming

- **vXX**: Handoff document version
- **Solution X**: Major system architecture changes
- **EA vX.XX**: Expert Advisor versions

## Links

- Full handoff history: `docs/handoffs/archive/`
- Decision rationale: `docs/DECISION_LOG.md`
- Version timeline: `docs/VERSION_TIMELINE.md`

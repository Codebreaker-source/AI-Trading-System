# Credentials & Secrets Map (FTMO_System)

**No actual credential values are stored in this file or anywhere in the
repo/codebase.** This document only notes *where* each credential needs to
go so Claude Chat can plan setup steps without guessing, and so Andy knows
exactly what to fill in and where. Claude Code will never write real
secrets into tracked files without explicit approval.

---

## 1. MT5 / FTMO account credentials

- **File**: `config/ftmo_config.json` → `account` section
- **Keys**: `login` (int, currently `0`), `password` (string, currently `""`),
  `server` (string, currently `"OANDA-Demo-1"`)
- **Consumed by**:
  - `run_system.py` lines 81-101 — `acct.get("login"/"password"/"server")`,
    calls `mt5.login(login, password=password, server=server)`
  - `core/symbol_manager.py` lines 91-93 — same pattern, used for symbol
    discovery connection
- **Status**: currently empty/placeholder (`0`, `""`, OANDA demo server).
  When switching to FTMO, Andy provides real FTMO MT5 login/password/server.
- **Git status**: `config/ftmo_config.json` is in `.gitignore` ("# Credentials")
  — **will not be committed**, but it DOES exist on disk right now with the
  account block present (currently blank values).

## 2. Azure Blob Storage (Colab bridge)

- **Mechanism**: environment variable `AZURE_STORAGE_CONNECTION_STRING`
- **Consumed by**: `core/azure_bridge.py` line 40 —
  `os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")`
- **Status**: not set anywhere in the repo (by design — env var only). If
  unset, `AzureBridge.enabled` is `False` and the whole Colab cloud-ensemble
  path is silently skipped (local XGBoost + strategy runner still work).
- **To configure**: Andy sets this env var on the machine running
  `run_system.py` (and on whatever runs the Colab-side scripts, if they also
  need write access to the same storage account).

## 3. FRED API key (economic data for news_analysis)

- **Mechanism**: environment variable `FRED_API_KEY`, OR passed as
  `fred_api_key` constructor arg
- **Consumed by**:
  - `news_analysis/data_sources/fred_api.py` line 72 —
    `self.api_key = api_key or os.environ.get('FRED_API_KEY')`
  - Passed through `news_analysis/__init__.py` (line 82/95) →
    `news_analysis/bias_manager.py` (line 100/108/114) →
    `news_analysis/data_release_analyzer.py` (line 101/103)
- **Status**: not set. If absent, `fred_api.py` prints a warning and the FRED
  client is `None` — economic-release sentiment features degrade gracefully
  but won't pull live FRED data.
- **Get a free key at**: `https://fred.stlouisfed.org/docs/api/api_key.html`
  (this URL is in the source comments, not a credential itself)

## 4. Google account for Colab (browser-session based, NOT an API key)

- **Mechanism**: `colab/keepalive.py` launches a dedicated Microsoft Edge
  profile (`colab/edge_profile/`) and requires a **one-time manual interactive
  Google login** in that browser window (`--login` flag). After that, the
  session persists in the Edge profile directory.
- **Consumed by**: `colab/keepalive.py`, `colab/find_notebook.py`,
  `colab/save_to_drive.py`, and `scripts/setup_colab_task.py` (which schedules
  `keepalive.py` to run periodically and notes "First run requires a one-time
  manual Google login")
- **Status**: this is interactive/manual, not a config value — Andy logs into
  Google once via the launched browser window. The resulting session
  cookies/profile live in `colab/edge_profile/` (already present, large —
  this is why that directory shows up as browser cache/metrics in the file
  inventory).
- **Note**: `colab/edge_profile/` contains real browser session state
  (cookies, login tokens for whatever Google account was used). Treat this
  directory as sensitive — do not upload it anywhere, and exclude it from any
  repo sync (check it's covered by `.gitignore` if `colab/` is ever tracked —
  currently `.gitignore` does not explicitly list `colab/`, worth flagging).

## 5. Other scheduled-task scripts

- `scripts/setup_*.py` (colab/retrainer/trading/watchdog tasks) configure
  Windows Scheduled Tasks with `<LogonType>InteractiveToken</LogonType>` —
  this runs tasks under the currently logged-in Windows user's session
  (no separate credential stored), required specifically so the Colab
  browser-automation task can access the Edge profile/Google session above.

---

## Summary table

| Credential | Where it lives | Currently set? | How Andy provides it |
|---|---|---|---|
| FTMO MT5 login/password/server | `config/ftmo_config.json` → `account` | No (blank/demo) | Edit JSON directly (gitignored) |
| Azure Storage connection string | env var `AZURE_STORAGE_CONNECTION_STRING` | No | Set OS env var |
| FRED API key | env var `FRED_API_KEY` | No | Set OS env var |
| Google account (Colab) | Edge browser profile `colab/edge_profile/` | Yes (already logged in) | One-time manual login via `keepalive.py --login` |

---

## Action item flagged for `.gitignore`

`colab/edge_profile/` (contains live Google session data) is **not** currently
listed in `.gitignore`. If `FTMO_System` is ever committed/pushed as a whole,
this would leak session cookies. Recommend adding `colab/edge_profile/` to
`.gitignore` — flag this to Andy before doing it (file modification rule).

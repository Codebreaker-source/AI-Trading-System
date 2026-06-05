//+------------------------------------------------------------------+
//|                         BridgeEA_FTMO_v1.mq5                    |
//|                              AI Trading System - FTMO Deploy     |
//|  Based on BridgeEA_LITE_v2_32_STREAK_SIZE                       |
//|                                                                  |
//|  KEY CHANGES FROM v2.32:                                         |
//|  - Dynamic symbol scanning (all Market Watch symbols, not 8)     |
//|  - Writes 27 CLEAN features per symbol (not 58)                  |
//|  - Per-symbol CSV: FTMO_System\data\features\{SYMBOL}_features   |
//|  - Per-symbol signal: data\features\signal_{SYMBOL}.txt          |
//|  - Execution log: data\execution_log\trades.csv                  |
//|  PRESERVED FROM v2.32:                                           |
//|  - Regime-adaptive trailing stops                                |
//|  - Partial TP at 2:1 R:R                                        |
//|  - Progressive trailing                                          |
//|  - Streak-based sizing                                           |
//|  - BE at 25% risk                                               |
//|  - All risk management features                                  |
//+------------------------------------------------------------------+
#property copyright "AI Trading System"
#property link      ""
#property version   "1.00"
#property description "Bridge EA FTMO v1 - Dynamic symbols, 27 CLEAN features"

//--- Input Parameters
input int    TimerSeconds           = 3;       // Timer interval (seconds)
input double FixedLotSize           = 0.01;   // Base lot size (FTMO minimum)
input double MinConfidence          = 0.45;   // Minimum confidence threshold
input double MaxDailyLossPercent    = 3.0;    // System daily loss limit (%)
input double FTMODailyLossPercent   = 5.0;   // FTMO hard daily loss limit (%)
input double FTMOTotalLossPercent   = 10.0;  // FTMO hard total loss limit (%)
input int    MaxTotalPositions      = 10;     // Maximum total open positions
input double MaxPortfolioRiskPercent = 2.0;  // Max portfolio risk (%)
input int    MaxCorrelationExposure = 2;      // Max positions per correlation group
input int    Slippage               = 10;    // Slippage in points
input int    MagicNumber            = 20260601; // Magic number for FTMO trades
input double MaxSpreadPips          = 5.0;   // Maximum spread for entry
input double RiskRewardRatio        = 2.0;   // Risk/Reward ratio
input double SL_ATR_Multiplier      = 1.5;   // Stop loss = ATR * multiplier
input bool   EnableTrading          = true;   // Enable trade execution
input bool   LogVerbose             = true;   // Verbose logging

// Files are written to MT5 Common\Files folder (shared across all terminals)
// Python reads from: C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\Common\Files\

//--- Break-Even & Trailing
input bool   EnableBreakEven        = true;
input bool   EnableTrailing         = true;
input double BE_TriggerRR           = 0.25;
input double BE_BufferPips          = 2.0;
input double Trail_ATR_Multiplier   = 2.0;
input int    TrailCheckSeconds      = 5;

//--- Regime-Adaptive Trailing (from v2.29)
input bool   EnableRegimeTrailing   = true;
input double Trail_ATR_Ranging      = 1.5;
input double Trail_ATR_Trending     = 2.5;
input double Trail_ATR_Volatile     = 3.5;
input double RegimeATR_LowThreshold = 15.0;
input double RegimeATR_HighThreshold= 40.0;

//--- Partial TP (from v2.30)
input bool   EnablePartialTP        = true;
input double PartialTP_TriggerRR    = 2.0;
input double PartialTP_ClosePercent = 50.0;
input double PartialTP_ExtendRR     = 3.0;

//--- Progressive Trailing (from v2.31)
input bool   EnableProgressiveTrail = true;
input double ProgTrail_Tier1_RR     = 1.0;
input double ProgTrail_Tier2_RR     = 1.5;
input double ProgTrail_Tier3_RR     = 2.0;
input double ProgTrail_Mult_Tier1   = 0.9;
input double ProgTrail_Mult_Tier2   = 0.75;
input double ProgTrail_Mult_Tier3   = 0.5;

//--- Streak-Based Sizing (from v2.32)
input bool   EnableStreakSizing      = true;
input int    LossStreak_Tier1_Count  = 2;
input int    LossStreak_Tier2_Count  = 3;
input double LossStreak_Tier1_Mult   = 0.70;
input double LossStreak_Tier2_Mult   = 0.50;
input int    WinStreak_PyramidTrigger= 3;

//--- Technical Indicator Parameters
input int    FastEMA_Period = 12;
input int    SlowEMA_Period = 26;
input int    RSI_Period     = 14;
input int    ATR_Period     = 14;
input int    BB_Period      = 20;
input double BB_Deviation   = 2.0;
input int    Stoch_K        = 14;
input int    Stoch_D        = 3;
input int    Stoch_Slowing  = 3;
input int    SMA20_Period   = 20;
input int    SMA50_Period   = 50;
input ENUM_TIMEFRAMES HTF_Timeframe = PERIOD_H4;

//+------------------------------------------------------------------+
//| Dynamic symbol arrays (populated at OnInit from Market Watch)    |
//+------------------------------------------------------------------+
#define MAX_SYMBOLS 200

string   g_symbols[MAX_SYMBOLS];
int      g_symbol_count = 0;

int      g_fastEMA_h[MAX_SYMBOLS];
int      g_slowEMA_h[MAX_SYMBOLS];
int      g_rsi_h[MAX_SYMBOLS];
int      g_atr_h[MAX_SYMBOLS];
int      g_bb_h[MAX_SYMBOLS];
int      g_stoch_h[MAX_SYMBOLS];
int      g_sma20_h[MAX_SYMBOLS];
int      g_sma50_h[MAX_SYMBOLS];
int      g_htfFastEMA_h[MAX_SYMBOLS];
int      g_htfSlowEMA_h[MAX_SYMBOLS];

//--- Tracking
datetime g_lastTrailCheck  = 0;

//--- Partial TP tracking
ulong    g_partialTPTickets[200];
int      g_partialTPCount       = 0;
int      g_partialTPTakenTotal  = 0;

//--- Streak tracking
int      g_consecutiveWins   = 0;
int      g_consecutiveLosses = 0;
int      g_totalWins         = 0;
int      g_totalLosses       = 0;
int      g_lastKnownHistoryCount = 0;
bool     g_pyramidingEnabled = false;

//--- Daily loss limit
double   g_dayStartBalance      = 0;
double   g_accountStartBalance  = 0;
int      g_currentDay           = -1;
bool     g_dailyLossLimitHit    = false;
bool     g_totalLossLimitHit    = false;

//--- Portfolio risk
double   g_currentPortfolioRisk = 0;

#include <Trade\Trade.mqh>
CTrade g_trade;


//+------------------------------------------------------------------+
//| Strip known FTMO suffixes to get base symbol name                 |
//+------------------------------------------------------------------+
string StripSuffix(string symbol)
{
    string suffixes[] = {".i", "_SB", ".r", "_raw", ".a", ".b", ".c", ".m", ".pro", ".sim"};
    string result = symbol;
    for(int s = 0; s < ArraySize(suffixes); s++)
    {
        int suf_len = StringLen(suffixes[s]);
        int sym_len = StringLen(result);
        if(sym_len > suf_len &&
           StringSubstr(result, sym_len - suf_len) == suffixes[s])
        {
            result = StringSubstr(result, 0, sym_len - suf_len);
            break;
        }
    }
    return result;
}

//+------------------------------------------------------------------+
//| Discover all tradeable symbols from Market Watch                  |
//+------------------------------------------------------------------+
int DiscoverSymbols()
{
    g_symbol_count = 0;
    int total = SymbolsTotal(true);
    Print("[SYMBOLS] Scanning Market Watch: ", total, " symbols found");

    for(int i = 0; i < total && g_symbol_count < MAX_SYMBOLS; i++)
    {
        string sym = SymbolName(i, true);
        if(sym == "") continue;
        if(StringFind(sym, "#") >= 0) continue;

        long trade_mode = SymbolInfoInteger(sym, SYMBOL_TRADE_MODE);
        if(trade_mode == SYMBOL_TRADE_MODE_DISABLED) continue;

        g_symbols[g_symbol_count] = sym;
        g_symbol_count++;
    }

    Print("[SYMBOLS] Tradeable symbols accepted: ", g_symbol_count);
    for(int i = 0; i < g_symbol_count; i++)
        Print("  [", i, "] ", g_symbols[i]);

    return g_symbol_count;
}

//+------------------------------------------------------------------+
//| Initialize indicators for all discovered symbols                  |
//+------------------------------------------------------------------+
void InitAllIndicators()
{
    for(int i = 0; i < g_symbol_count; i++)
    {
        string sym = g_symbols[i];
        g_fastEMA_h[i]    = iMA(sym, 0, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_slowEMA_h[i]    = iMA(sym, 0, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_rsi_h[i]        = iRSI(sym, 0, RSI_Period, PRICE_CLOSE);
        g_atr_h[i]        = iATR(sym, 0, ATR_Period);
        g_bb_h[i]         = iBands(sym, 0, BB_Period, 0, BB_Deviation, PRICE_CLOSE);
        g_stoch_h[i]      = iStochastic(sym, 0, Stoch_K, Stoch_D, Stoch_Slowing, MODE_SMA, STO_LOWHIGH);
        g_sma20_h[i]      = iMA(sym, 0, SMA20_Period, 0, MODE_SMA, PRICE_CLOSE);
        g_sma50_h[i]      = iMA(sym, 0, SMA50_Period, 0, MODE_SMA, PRICE_CLOSE);
        g_htfFastEMA_h[i] = iMA(sym, HTF_Timeframe, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_htfSlowEMA_h[i] = iMA(sym, HTF_Timeframe, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);

        if(g_fastEMA_h[i] == INVALID_HANDLE || g_atr_h[i] == INVALID_HANDLE)
            Print("[WARN] Indicator init issue for ", sym);
    }
}

//+------------------------------------------------------------------+
//| Get ATR value for symbol by index                                 |
//+------------------------------------------------------------------+
double GetATR(int idx)
{
    if(idx < 0 || idx >= g_symbol_count || g_atr_h[idx] == INVALID_HANDLE) return 0.0001;
    double buf[1];
    return (CopyBuffer(g_atr_h[idx], 0, 0, 1, buf) == 1 && buf[0] > 0) ? buf[0] : 0.0001;
}

double GetATRForSymbol(string symbol)
{
    for(int i = 0; i < g_symbol_count; i++)
        if(g_symbols[i] == symbol) return GetATR(i);
    return 0.0001;
}

//+------------------------------------------------------------------+
//| Get pip value for any symbol                                      |
//+------------------------------------------------------------------+
double GetPipValue(string symbol)
{
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    double pip = (digits == 5 || digits == 3) ? point * 10 : point;
    return (pip > 0) ? pip : 0.0001;  // never return 0 — prevents zero divide
}

//+------------------------------------------------------------------+
//| Write 27 CLEAN features for one symbol to its dedicated CSV       |
//+------------------------------------------------------------------+
void WriteFeatureCSV(int idx)
{
    if(g_atr_h[idx] == INVALID_HANDLE) return;
    string sym = g_symbols[idx];

    double buf1[1], buf2[1];
    double fastEMA=0, slowEMA=0, sma20=0, sma50=0;
    double htfFastEMA=0, htfSlowEMA=0;
    double rsi=50, stoch_k=50, stoch_d=50;
    double atr=0.0001, bb_upper=0, bb_middle=0, bb_lower=0;

    if(CopyBuffer(g_fastEMA_h[idx],    0,0,1,buf1)==1) fastEMA=buf1[0];
    if(CopyBuffer(g_slowEMA_h[idx],    0,0,1,buf1)==1) slowEMA=buf1[0];
    if(CopyBuffer(g_sma20_h[idx],      0,0,1,buf1)==1) sma20=buf1[0];
    if(CopyBuffer(g_sma50_h[idx],      0,0,1,buf1)==1) sma50=buf1[0];
    if(CopyBuffer(g_htfFastEMA_h[idx], 0,0,1,buf1)==1) htfFastEMA=buf1[0];
    if(CopyBuffer(g_htfSlowEMA_h[idx], 0,0,1,buf1)==1) htfSlowEMA=buf1[0];
    if(CopyBuffer(g_rsi_h[idx],        0,0,1,buf1)==1) rsi=buf1[0];
    if(CopyBuffer(g_stoch_h[idx],      0,0,1,buf1)==1) stoch_k=buf1[0];
    if(CopyBuffer(g_stoch_h[idx],      1,0,1,buf2)==1) stoch_d=buf2[0];
    if(CopyBuffer(g_atr_h[idx],        0,0,1,buf1)==1) atr=buf1[0];
    if(CopyBuffer(g_bb_h[idx],         0,0,1,buf1)==1) bb_middle=buf1[0];
    if(CopyBuffer(g_bb_h[idx],         1,0,1,buf2)==1) bb_upper=buf2[0];
    if(CopyBuffer(g_bb_h[idx],         2,0,1,buf2)==1) bb_lower=buf2[0];

    MqlRates rates[2];
    if(CopyRates(sym, 0, 0, 2, rates) < 2) return;

    double close  = rates[0].close;
    double high   = rates[0].high;
    double low    = rates[0].low;
    double volume = (double)rates[0].tick_volume;
    double pip    = GetPipValue(sym);

    double volatility   = (atr > 0 && pip > 0) ? atr / pip : 0;
    double momentum     = close - rates[1].close;
    double vol_prev     = (double)rates[1].tick_volume;
    double vol_sma      = (volume + vol_prev) / 2.0;
    double vol_ratio    = (vol_sma > 0) ? volume / vol_sma : 1.0;
    double price_vol    = close * volume;
    double htf_trend_dir   = (htfFastEMA > htfSlowEMA) ? 1.0 : -1.0;
    double htf_trend_align = (htfFastEMA > htfSlowEMA && fastEMA > slowEMA)  ?  1.0 :
                             (htfFastEMA < htfSlowEMA && fastEMA < slowEMA)  ? -1.0 : 0.0;
    double bull_sent = (rsi > 50) ? (rsi - 50.0) / 50.0 : 0.0;
    double bear_sent = (rsi < 50) ? (50.0 - rsi) / 50.0 : 0.0;
    double net_sent  = bull_sent - bear_sent;

    string feat_path = sym + "_features.csv";
    int fh = FileOpen(feat_path, FILE_WRITE | FILE_CSV | FILE_COMMON | FILE_ANSI, ',');
    if(fh == INVALID_HANDLE) return;

    FileWrite(fh,
        "timestamp","symbol",
        "close","high","low","volume",
        "sma_20","sma_50","fast_ema","slow_ema",
        "htf_fast_ema","htf_slow_ema","htf_trend_direction","htf_trend_alignment",
        "rsi","stoch_k","stoch_d","momentum",
        "atr","bb_upper","bb_middle","bb_lower","volatility",
        "volume_sma","volume_ratio","price_volume",
        "bullish_sentiment","bearish_sentiment","net_sentiment");

    FileWrite(fh,
        TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS), sym,
        DoubleToString(close,8),  DoubleToString(high,8),    DoubleToString(low,8),
        DoubleToString(volume,2),
        DoubleToString(sma20,8),  DoubleToString(sma50,8),
        DoubleToString(fastEMA,8),DoubleToString(slowEMA,8),
        DoubleToString(htfFastEMA,8), DoubleToString(htfSlowEMA,8),
        DoubleToString(htf_trend_dir,4), DoubleToString(htf_trend_align,4),
        DoubleToString(rsi,4),    DoubleToString(stoch_k,4), DoubleToString(stoch_d,4),
        DoubleToString(momentum,8),
        DoubleToString(atr,8),    DoubleToString(bb_upper,8),
        DoubleToString(bb_middle,8), DoubleToString(bb_lower,8),
        DoubleToString(volatility,4),
        DoubleToString(vol_sma,2), DoubleToString(vol_ratio,4),
        DoubleToString(price_vol,2),
        DoubleToString(bull_sent,4), DoubleToString(bear_sent,4),
        DoubleToString(net_sent,4));

    FileClose(fh);
}

//+------------------------------------------------------------------+
//| Read signal file for a symbol                                     |
//+------------------------------------------------------------------+
// Read a single source-tagged signal file
// Format: symbol,action,confidence,sl,tp,lot,trade_id,timestamp
string ReadSignalFile(string sig_path, double &out_conf, double &out_sl,
                      double &out_tp, double &out_lot, string &out_trade_id)
{
    out_conf = 0; out_sl = 0; out_tp = 0; out_lot = FixedLotSize; out_trade_id = "";

    int fh = FileOpen(sig_path, FILE_READ | FILE_CSV | FILE_COMMON | FILE_ANSI, ',');
    if(fh == INVALID_HANDLE) return "HOLD";

    string action = "HOLD";
    if(!FileIsEnding(fh))
    {
        FileReadString(fh);               // symbol (discard)
        action       = FileReadString(fh);
        out_conf     = StringToDouble(FileReadString(fh));
        out_sl       = StringToDouble(FileReadString(fh));
        out_tp       = StringToDouble(FileReadString(fh));
        out_lot      = StringToDouble(FileReadString(fh));
        out_trade_id = FileReadString(fh); // trade_id
        if(out_lot < 0.01 || out_lot == 0) out_lot = FixedLotSize;
    }
    FileClose(fh);
    FileDelete(sig_path, FILE_COMMON);
    return action;
}

// Single scan of Common\Files for ALL signal_*_*.txt files — one pass per timer tick
// Fixes: zero divide from FileFindFirst overwriting sym, and 27x per-symbol scan overhead
void ReadAndExecuteAllSignals()
{
    string fname;
    long fh = FileFindFirst("signal_*.txt", fname, FILE_COMMON);
    if(fh == INVALID_HANDLE) return;

    do
    {
        if(StringLen(fname) == 0) continue;

        // Format: signal_{SYM}_{SOURCE}.txt
        // OANDA symbols never contain underscores (EURUSD.sim, XAUUSD.sim etc.)
        // Sources can contain underscores (dema_supertrend, dema_rsi_hf)
        // So split on the FIRST underscore after "signal_"
        // e.g. signal_EURUSD.sim_dema_supertrend.txt
        //      after "signal_" = EURUSD.sim_dema_supertrend.txt
        //      first _ at pos 9 → sym=EURUSD.sim  source=dema_supertrend

        // Strip "signal_" prefix (7 chars)
        string after_prefix = StringSubstr(fname, 7);   // EURUSD.sim_dema_supertrend.txt
        StringReplace(after_prefix, ".txt", "");          // EURUSD.sim_dema_supertrend

        // Find first underscore → boundary between sym and source
        int first_us = StringFind(after_prefix, "_");
        if(first_us < 0) continue;  // no source — skip (old format signal_SYM.txt)

        string sym_part = StringSubstr(after_prefix, 0, first_us);            // EURUSD.sim
        string src_part = StringSubstr(after_prefix, first_us + 1);           // dema_supertrend

        if(StringLen(sym_part) == 0 || StringLen(src_part) == 0) continue;

        if(!FileIsExist(fname, FILE_COMMON)) continue;

        double conf=0, sl=0, tp=0, lot=FixedLotSize;
        string trade_id="";
        string action = ReadSignalFile(fname, conf, sl, tp, lot, trade_id);

        if((action=="BUY" || action=="SELL") && conf >= MinConfidence)
            ExecuteTradeWithId(sym_part, action, conf, sl, tp, lot, trade_id, src_part);
    }
    while(FileFindNext(fh, fname));

    FileFindClose(fh);
}

//+------------------------------------------------------------------+
//| Write open positions for Python                                   |
//+------------------------------------------------------------------+
void WriteOpenPositions()
{
    int fh = FileOpen("open_positions.csv", FILE_WRITE | FILE_CSV | FILE_COMMON | FILE_ANSI, ',');
    if(fh == INVALID_HANDLE) return;

    FileWrite(fh,"ticket","symbol","direction","volume","entry_price","sl","tp","profit","be_status","open_time");

    for(int i = 0; i < PositionsTotal(); i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket==0 || PositionGetInteger(POSITION_MAGIC)!=MagicNumber) continue;

        long   type  = PositionGetInteger(POSITION_TYPE);
        double entry = PositionGetDouble(POSITION_PRICE_OPEN);
        double sl    = PositionGetDouble(POSITION_SL);
        bool   be    = (type==POSITION_TYPE_BUY)  ? (sl>=entry) :
                       (type==POSITION_TYPE_SELL) ? (sl<=entry && sl>0) : false;

        FileWrite(fh,
            IntegerToString((long)ticket),
            PositionGetString(POSITION_SYMBOL),
            (type==POSITION_TYPE_BUY) ? "BUY" : "SELL",
            DoubleToString(PositionGetDouble(POSITION_VOLUME),2),
            DoubleToString(entry,8),
            DoubleToString(sl,8),
            DoubleToString(PositionGetDouble(POSITION_TP),8),
            DoubleToString(PositionGetDouble(POSITION_PROFIT),2),
            be ? "1" : "0",
            TimeToString((datetime)PositionGetInteger(POSITION_TIME),TIME_DATE|TIME_MINUTES|TIME_SECONDS));
    }
    FileClose(fh);
}

//+------------------------------------------------------------------+
//| Log trade execution outcome                                        |
//+------------------------------------------------------------------+
void LogExecution(string sym, string action, string outcome,
                  double entry, double exit_price, double sl, double tp,
                  double volume, double profit, ulong ticket,
                  string trade_id="", string signal_source="")
{
    bool need_header = !FileIsExist("trades.csv", FILE_COMMON);
    int fh = FileOpen("trades.csv", FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI, ',');
    if(fh == INVALID_HANDLE) return;
    FileSeek(fh, 0, SEEK_END);

    if(need_header)
        FileWrite(fh, "timestamp","symbol","direction","outcome",
                      "entry_price","exit_price","sl","tp",
                      "volume","profit","ticket","trade_id","signal_source");

    FileWrite(fh,
        TimeToString(TimeCurrent(),TIME_DATE|TIME_MINUTES|TIME_SECONDS),
        sym, action, outcome,
        DoubleToString(entry,8), DoubleToString(exit_price,8),
        DoubleToString(sl,8), DoubleToString(tp,8),
        DoubleToString(volume,2), DoubleToString(profit,2),
        IntegerToString((long)ticket),
        trade_id, signal_source);
    FileClose(fh);
}

// Execute trade with full attribution (trade_id + source)
void ExecuteTradeWithId(string sym, string action, double confidence,
                        double sl_price, double tp_price, double lot,
                        string trade_id, string source)
{
    if(!EnableTrading) return;
    if(CheckFTMOLimits()) return;

    // Enforce minimum lot size for this symbol
    double min_lot  = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
    double lot_step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
    if(min_lot <= 0) min_lot = 0.01;
    if(lot < min_lot) lot = min_lot;
    if(lot_step > 0) lot = MathFloor(lot / lot_step) * lot_step;

    double spread_pips = (SymbolInfoDouble(sym,SYMBOL_ASK)-SymbolInfoDouble(sym,SYMBOL_BID))/GetPipValue(sym);
    if(spread_pips > MaxSpreadPips) return;

    double atr     = GetATRForSymbol(sym);
    int    digits  = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
    double pt      = SymbolInfoDouble(sym, SYMBOL_POINT);
    // Minimum stop distance required by broker (in price units), add 10% buffer
    double min_stop = (SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) * pt) * 1.1;
    if(min_stop <= 0) min_stop = atr * 0.5;  // fallback: half ATR

    double entry = 0;

    if(action == "BUY")
    {
        entry = SymbolInfoDouble(sym, SYMBOL_ASK);
        // Validate / fix SL: must be BELOW entry by at least min_stop
        if(sl_price <= 0 || sl_price >= entry || (entry - sl_price) < min_stop)
            sl_price = entry - MathMax(atr * SL_ATR_Multiplier, min_stop * 1.5);
        // Validate / fix TP: must be ABOVE entry by at least min_stop
        if(tp_price <= 0 || tp_price <= entry || (tp_price - entry) < min_stop)
            tp_price = entry + MathMax(atr * SL_ATR_Multiplier * RiskRewardRatio, min_stop * 2.0);

        sl_price = NormalizeDouble(sl_price, digits);
        tp_price = NormalizeDouble(tp_price, digits);

        if(g_trade.Buy(lot, sym, entry, sl_price, tp_price, "FTMO_AI_" + source))
        {
            ulong ticket = g_trade.ResultOrder();
            Print("[BUY] ",sym," src=",source," lot=",DoubleToString(lot,2),
                  " entry=",DoubleToString(entry,digits),
                  " SL=",DoubleToString(sl_price,digits),
                  " TP=",DoubleToString(tp_price,digits));
            LogExecution(sym,"BUY","OPEN",entry,0,sl_price,tp_price,lot,0,ticket,trade_id,source);
        }
        else Print("[ERROR] Buy failed (",source,"): ",g_trade.ResultRetcodeDescription());
    }
    else if(action == "SELL")
    {
        entry = SymbolInfoDouble(sym, SYMBOL_BID);
        // Validate / fix SL: must be ABOVE entry by at least min_stop
        if(sl_price <= 0 || sl_price <= entry || (sl_price - entry) < min_stop)
            sl_price = entry + MathMax(atr * SL_ATR_Multiplier, min_stop * 1.5);
        // Validate / fix TP: must be BELOW entry by at least min_stop
        if(tp_price <= 0 || tp_price >= entry || (entry - tp_price) < min_stop)
            tp_price = entry - MathMax(atr * SL_ATR_Multiplier * RiskRewardRatio, min_stop * 2.0);

        sl_price = NormalizeDouble(sl_price, digits);
        tp_price = NormalizeDouble(tp_price, digits);

        if(g_trade.Sell(lot, sym, entry, sl_price, tp_price, "FTMO_AI_" + source))
        {
            ulong ticket = g_trade.ResultOrder();
            Print("[SELL] ",sym," src=",source," lot=",DoubleToString(lot,2),
                  " entry=",DoubleToString(entry,digits),
                  " SL=",DoubleToString(sl_price,digits),
                  " TP=",DoubleToString(tp_price,digits));
            LogExecution(sym,"SELL","OPEN",entry,0,sl_price,tp_price,lot,0,ticket,trade_id,source);
        }
        else Print("[ERROR] Sell failed (",source,"): ",g_trade.ResultRetcodeDescription());
    }
}

//+------------------------------------------------------------------+
//| FTMO drawdown safety check                                        |
//+------------------------------------------------------------------+
bool CheckFTMOLimits()
{
    if(g_totalLossLimitHit || g_dailyLossLimitHit) return true;

    double balance = AccountInfoDouble(ACCOUNT_BALANCE);

    if(g_accountStartBalance > 0)
    {
        double daily_pct = (g_dayStartBalance - balance) / g_accountStartBalance * 100.0;
        if(daily_pct >= MaxDailyLossPercent)
        {
            Print("[HALT] System daily limit hit: ", DoubleToString(daily_pct,2), "%");
            g_dailyLossLimitHit = true; return true;
        }
        if(daily_pct >= FTMODailyLossPercent)
        {
            Print("[HALT] FTMO daily limit hit: ", DoubleToString(daily_pct,2), "%");
            g_dailyLossLimitHit = true; return true;
        }
        double total_pct = (g_accountStartBalance - balance) / g_accountStartBalance * 100.0;
        if(total_pct >= FTMOTotalLossPercent)
        {
            Print("[HALT] FTMO total drawdown limit hit: ", DoubleToString(total_pct,2), "%");
            g_totalLossLimitHit = true; return true;
        }
    }
    return false;
}

//+------------------------------------------------------------------+
void CheckNewDay()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    if(dt.day_of_year != g_currentDay)
    {
        g_dayStartBalance   = AccountInfoDouble(ACCOUNT_BALANCE);
        g_currentDay        = dt.day_of_year;
        g_dailyLossLimitHit = false;
        Print("[NEW DAY] Balance reset: ", DoubleToString(g_dayStartBalance,2));
    }
}

//+------------------------------------------------------------------+
//| Pip dollar value helpers                                          |
//+------------------------------------------------------------------+
double GetPipDollarValue(string symbol)
{
    string b = StripSuffix(symbol);
    if(b=="EURUSD"||b=="GBPUSD"||b=="AUDUSD"||b=="NZDUSD") return 0.10;
    if(b=="USDJPY") return 0.067;
    if(b=="USDCHF"||b=="USDCAD") return 0.075;
    if(b=="EURGBP") return 0.125;
    return 0.10;
}

double CalcPositionRisk(string sym, double entry, double sl, double lot)
{
    double pip = GetPipValue(sym);
    if(pip <= 0) return 0;
    return (MathAbs(entry-sl)/pip) * GetPipDollarValue(sym) * (lot/0.01);
}

double CalcPortfolioRisk()
{
    double risk = 0;
    for(int i=0; i<PositionsTotal(); i++)
    {
        ulong t = PositionGetTicket(i);
        if(t==0||PositionGetInteger(POSITION_MAGIC)!=MagicNumber) continue;
        double sl = PositionGetDouble(POSITION_SL);
        if(sl<=0) continue;
        risk += CalcPositionRisk(PositionGetString(POSITION_SYMBOL),
                                 PositionGetDouble(POSITION_PRICE_OPEN),
                                 sl, PositionGetDouble(POSITION_VOLUME));
    }
    g_currentPortfolioRisk = risk;
    return risk;
}

bool CheckPortfolioRisk(string sym, string action, double lot)
{
    double balance  = AccountInfoDouble(ACCOUNT_BALANCE);
    double max_risk = balance * (MaxPortfolioRiskPercent/100.0);
    double cur_risk = CalcPortfolioRisk();
    double atr      = GetATRForSymbol(sym);
    double entry    = (action=="BUY") ? SymbolInfoDouble(sym,SYMBOL_ASK) : SymbolInfoDouble(sym,SYMBOL_BID);
    double sl       = (action=="BUY") ? entry-atr*SL_ATR_Multiplier : entry+atr*SL_ATR_Multiplier;
    double new_risk = CalcPositionRisk(sym, entry, sl, lot);
    if(cur_risk+new_risk > max_risk)
    {
        if(LogVerbose) Print("[RISK] Limit: cur=",DoubleToString(cur_risk,2)," new=",DoubleToString(new_risk,2));
        return false;
    }
    return true;
}

int GetCorrelationGroup(string symbol)
{
    string b = StripSuffix(symbol);
    if(b=="EURUSD"||b=="GBPUSD"||b=="EURGBP") return 0;
    if(b=="AUDUSD"||b=="NZDUSD") return 1;
    if(b=="USDJPY"||b=="USDCHF"||b=="USDCAD") return 2;
    return 3;
}

bool CheckCorrelationExposure(string sym)
{
    int group=GetCorrelationGroup(sym), count=0;
    for(int i=0; i<PositionsTotal(); i++)
    {
        ulong t=PositionGetTicket(i);
        if(t==0||PositionGetInteger(POSITION_MAGIC)!=MagicNumber) continue;
        if(GetCorrelationGroup(PositionGetString(POSITION_SYMBOL))==group) count++;
    }
    return count < MaxCorrelationExposure;
}

int GetEffectiveMaxPositions()
{
    if(!EnableStreakSizing) return MaxTotalPositions;
    if(g_consecutiveLosses>=LossStreak_Tier2_Count)
        return (int)MathMax(1,MathFloor(MaxTotalPositions*LossStreak_Tier2_Mult));
    if(g_consecutiveLosses>=LossStreak_Tier1_Count)
        return (int)MathMax(1,MathFloor(MaxTotalPositions*LossStreak_Tier1_Mult));
    return MaxTotalPositions;
}

//+------------------------------------------------------------------+
//| Execute trade                                                      |
//+------------------------------------------------------------------+
void ExecuteTrade(string sym, string action, double confidence, double sl_price, double tp_price, double lot)
{
    if(!EnableTrading) { Print("[DISABLED] Skipping trade for ",sym); return; }
    if(CheckFTMOLimits()) { Print("[HALT] FTMO limits — no new trades"); return; }
    if(PositionsTotal() >= GetEffectiveMaxPositions()) return;
    if(!CheckPortfolioRisk(sym,action,lot)) return;
    if(!CheckCorrelationExposure(sym)) return;

    double spread_pips = (SymbolInfoDouble(sym,SYMBOL_ASK)-SymbolInfoDouble(sym,SYMBOL_BID))/GetPipValue(sym);
    if(spread_pips > MaxSpreadPips) { Print("[SPREAD] ",sym," spread=",DoubleToString(spread_pips,1)," > max"); return; }

    double atr   = GetATRForSymbol(sym);
    double entry = 0;

    if(action == "BUY")
    {
        entry = SymbolInfoDouble(sym, SYMBOL_ASK);
        if(sl_price<=0) sl_price = entry - atr*SL_ATR_Multiplier;
        if(tp_price<=0) tp_price = entry + atr*SL_ATR_Multiplier*RiskRewardRatio;
        if(g_trade.Buy(lot,sym,entry,sl_price,tp_price,"FTMO_AI"))
        {
            ulong ticket = g_trade.ResultOrder();
            Print("[BUY] ",sym," lot=",DoubleToString(lot,2)," entry=",DoubleToString(entry,5),
                  " SL=",DoubleToString(sl_price,5)," TP=",DoubleToString(tp_price,5));
            LogExecution(sym,"BUY","OPEN",entry,0,sl_price,tp_price,lot,0,ticket);
        }
        else Print("[ERROR] Buy failed: ",g_trade.ResultRetcodeDescription());
    }
    else if(action == "SELL")
    {
        entry = SymbolInfoDouble(sym, SYMBOL_BID);
        if(sl_price<=0) sl_price = entry + atr*SL_ATR_Multiplier;
        if(tp_price<=0) tp_price = entry - atr*SL_ATR_Multiplier*RiskRewardRatio;
        if(g_trade.Sell(lot,sym,entry,sl_price,tp_price,"FTMO_AI"))
        {
            ulong ticket = g_trade.ResultOrder();
            Print("[SELL] ",sym," lot=",DoubleToString(lot,2)," entry=",DoubleToString(entry,5),
                  " SL=",DoubleToString(sl_price,5)," TP=",DoubleToString(tp_price,5));
            LogExecution(sym,"SELL","OPEN",entry,0,sl_price,tp_price,lot,0,ticket);
        }
        else Print("[ERROR] Sell failed: ",g_trade.ResultRetcodeDescription());
    }
}

//+------------------------------------------------------------------+
//| Position management: BE, trailing, partial TP (from v2.29-2.31)  |
//+------------------------------------------------------------------+
void ManagePositions()
{
    if(!EnableBreakEven && !EnableTrailing) return;
    if((int)(TimeCurrent()-g_lastTrailCheck) < TrailCheckSeconds) return;
    g_lastTrailCheck = TimeCurrent();

    for(int i=PositionsTotal()-1; i>=0; i--)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket==0||PositionGetInteger(POSITION_MAGIC)!=MagicNumber) continue;

        string sym   = PositionGetString(POSITION_SYMBOL);
        long   type  = PositionGetInteger(POSITION_TYPE);
        double entry = PositionGetDouble(POSITION_PRICE_OPEN);
        double sl    = PositionGetDouble(POSITION_SL);
        double tp    = PositionGetDouble(POSITION_TP);
        double vol   = PositionGetDouble(POSITION_VOLUME);

        double atr     = GetATRForSymbol(sym);
        double pip     = GetPipValue(sym);
        double current = (type==POSITION_TYPE_BUY) ? SymbolInfoDouble(sym,SYMBOL_BID)
                                                    : SymbolInfoDouble(sym,SYMBOL_ASK);

        // Regime-adaptive trail multiplier
        double trail_mult = Trail_ATR_Multiplier;
        if(EnableRegimeTrailing && atr>0 && pip>0)
        {
            double atr_pips = atr/pip;
            trail_mult = (atr_pips<RegimeATR_LowThreshold)  ? Trail_ATR_Ranging  :
                         (atr_pips>RegimeATR_HighThreshold) ? Trail_ATR_Volatile : Trail_ATR_Trending;
        }

        if(sl<=0||entry<=0) continue;
        double risk_dist   = MathAbs(entry-sl);
        if(risk_dist<=0) continue;
        double profit_dist = (type==POSITION_TYPE_BUY) ? current-entry : entry-current;
        double rr_now      = profit_dist/risk_dist;

        // Progressive trailing modifier
        double prog_mod = 1.0;
        if(EnableProgressiveTrail)
        {
            if(rr_now>=ProgTrail_Tier3_RR)      prog_mod=ProgTrail_Mult_Tier3;
            else if(rr_now>=ProgTrail_Tier2_RR) prog_mod=ProgTrail_Mult_Tier2;
            else if(rr_now>=ProgTrail_Tier1_RR) prog_mod=ProgTrail_Mult_Tier1;
        }
        double eff_trail = atr*trail_mult*prog_mod;

        // Partial TP
        if(EnablePartialTP && rr_now>=PartialTP_TriggerRR)
        {
            bool already=false;
            for(int p=0;p<g_partialTPCount;p++)
                if(g_partialTPTickets[p]==ticket){already=true;break;}

            if(!already)
            {
                double close_vol = NormalizeDouble(vol*(PartialTP_ClosePercent/100.0),2);
                close_vol = MathMax(close_vol, SymbolInfoDouble(sym,SYMBOL_VOLUME_MIN));
                if(g_trade.PositionClosePartial(ticket,close_vol))
                {
                    if(g_partialTPCount<200) g_partialTPTickets[g_partialTPCount++]=ticket;
                    g_partialTPTakenTotal++;
                    double new_tp = (type==POSITION_TYPE_BUY)
                        ? entry+risk_dist*PartialTP_ExtendRR : entry-risk_dist*PartialTP_ExtendRR;
                    double be_sl  = (type==POSITION_TYPE_BUY)
                        ? entry+BE_BufferPips*pip : entry-BE_BufferPips*pip;
                    g_trade.PositionModify(ticket,be_sl,new_tp);
                    Print("[PARTIAL TP] ",sym," ticket=",IntegerToString((long)ticket));
                }
                continue;
            }
        }

        // Get fresh price just before any modify to avoid race conditions
        double ask_now = SymbolInfoDouble(sym, SYMBOL_ASK);
        double bid_now = SymbolInfoDouble(sym, SYMBOL_BID);

        // Break-even
        if(EnableBreakEven && rr_now>=BE_TriggerRR)
        {
            double be_sl = (type==POSITION_TYPE_BUY)
                ? entry+BE_BufferPips*pip : entry-BE_BufferPips*pip;
            bool needs = (type==POSITION_TYPE_BUY&&sl<be_sl)||(type==POSITION_TYPE_SELL&&sl>be_sl);
            // Validate new SL is still on correct side of current price
            bool valid_be = (type==POSITION_TYPE_BUY  && be_sl < bid_now) ||
                            (type==POSITION_TYPE_SELL && be_sl > ask_now);
            if(needs && valid_be)
            {
                g_trade.PositionModify(ticket,be_sl,tp);
                if(LogVerbose) Print("[BE] ",sym," SL→",DoubleToString(be_sl,5));
            }
        }

        // Trailing stop
        if(EnableTrailing && rr_now>0)
        {
            double new_sl = (type==POSITION_TYPE_BUY) ? current-eff_trail : current+eff_trail;
            bool trail_ok = (type==POSITION_TYPE_BUY  && new_sl>sl+pip) ||
                            (type==POSITION_TYPE_SELL && new_sl<sl-pip && sl>0);
            // Validate new SL is still on correct side of current price before sending
            bool valid_sl = (type==POSITION_TYPE_BUY  && new_sl < bid_now) ||
                            (type==POSITION_TYPE_SELL && new_sl > ask_now);
            if(trail_ok && valid_sl)
            {
                g_trade.PositionModify(ticket,new_sl,tp);
                if(LogVerbose) Print("[TRAIL] ",sym," SL ",DoubleToString(sl,5),"→",DoubleToString(new_sl,5));
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Update streak tracking from closed trades                         |
//+------------------------------------------------------------------+
void UpdateStreakTracking()
{
    int hist = HistoryDealsTotal();
    if(hist<=g_lastKnownHistoryCount) return;

    HistorySelect(0, TimeCurrent());
    for(int i=g_lastKnownHistoryCount; i<hist; i++)
    {
        ulong deal = HistoryDealGetTicket(i);
        if(deal==0||HistoryDealGetInteger(deal,DEAL_MAGIC)!=MagicNumber) continue;
        if(HistoryDealGetInteger(deal,DEAL_ENTRY)!=DEAL_ENTRY_OUT) continue;

        double deal_profit = HistoryDealGetDouble(deal,DEAL_PROFIT);
        string sym         = HistoryDealGetString(deal,DEAL_SYMBOL);
        long   deal_type   = HistoryDealGetInteger(deal,DEAL_TYPE);
        string direction   = (deal_type==DEAL_TYPE_BUY) ? "BUY" : "SELL";
        ulong  pos_id      = (ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);

        // Extract source from deal comment (format: "FTMO_AI_{source}")
        string deal_comment = HistoryDealGetString(deal, DEAL_COMMENT);
        string deal_source  = "";
        if(StringFind(deal_comment, "FTMO_AI_") == 0)
            deal_source = StringSubstr(deal_comment, 8);

        if(deal_profit>0)
        {
            g_consecutiveWins++;  g_consecutiveLosses=0;  g_totalWins++;
            g_pyramidingEnabled = (g_consecutiveWins>=WinStreak_PyramidTrigger);
            LogExecution(sym,direction,"TP",
                0,
                HistoryDealGetDouble(deal,DEAL_PRICE),
                0,0,HistoryDealGetDouble(deal,DEAL_VOLUME),deal_profit,pos_id,
                "",deal_source);
        }
        else
        {
            g_consecutiveLosses++; g_consecutiveWins=0; g_totalLosses++;
            g_pyramidingEnabled=false;
            LogExecution(sym,direction,"SL",
                0,
                HistoryDealGetDouble(deal,DEAL_PRICE),
                0,0,HistoryDealGetDouble(deal,DEAL_VOLUME),deal_profit,pos_id,
                "",deal_source);
        }
    }
    g_lastKnownHistoryCount = hist;
}

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("================================================================");
    Print("  BridgeEA_FTMO_v1 - Dynamic Symbols + 27 CLEAN Features");
    Print("================================================================");
    Print("  Data path:          MT5 Common\\Files (FILE_COMMON)");
    Print("  FTMO daily limit:   ", FTMODailyLossPercent, "%");
    Print("  FTMO total limit:   ", FTMOTotalLossPercent, "%");
    Print("  System daily limit: ", MaxDailyLossPercent, "%");
    Print("  Base lot size:      ", FixedLotSize);

    if(DiscoverSymbols() == 0)
    {
        Print("ERROR: No tradeable symbols in Market Watch");
        return INIT_FAILED;
    }
    InitAllIndicators();

    g_accountStartBalance   = AccountInfoDouble(ACCOUNT_BALANCE);
    g_dayStartBalance       = g_accountStartBalance;
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    g_currentDay            = dt.day_of_year;

    g_lastKnownHistoryCount = HistoryDealsTotal();
    ArrayInitialize(g_partialTPTickets, 0);

    g_trade.SetExpertMagicNumber(MagicNumber);
    g_trade.SetDeviationInPoints(Slippage);
    g_trade.SetTypeFilling(ORDER_FILLING_RETURN);

    EventSetTimer(TimerSeconds);
    Print("SUCCESS: ", g_symbol_count, " symbols | balance: $",
          DoubleToString(g_accountStartBalance,2));
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    EventKillTimer();
    for(int i=0; i<g_symbol_count; i++)
    {
        IndicatorRelease(g_fastEMA_h[i]);   IndicatorRelease(g_slowEMA_h[i]);
        IndicatorRelease(g_rsi_h[i]);       IndicatorRelease(g_atr_h[i]);
        IndicatorRelease(g_bb_h[i]);        IndicatorRelease(g_stoch_h[i]);
        IndicatorRelease(g_sma20_h[i]);     IndicatorRelease(g_sma50_h[i]);
        IndicatorRelease(g_htfFastEMA_h[i]);IndicatorRelease(g_htfSlowEMA_h[i]);
    }
    Print("[DEINIT] W=",g_totalWins," L=",g_totalLosses);
}

//+------------------------------------------------------------------+
//| Timer — runs every TimerSeconds                                    |
//+------------------------------------------------------------------+
void OnTimer()
{
    CheckNewDay();
    UpdateStreakTracking();
    ManagePositions();
    WriteOpenPositions();

    // Write features for all symbols (priority #1 — always runs)
    for(int i=0; i<g_symbol_count; i++)
        WriteFeatureCSV(i);

    // Single-pass signal scan — one FileFindFirst for all sources across all symbols
    if(EnableTrading && !CheckFTMOLimits())
        ReadAndExecuteAllSignals();

    if(LogVerbose)
    {
        double bal = AccountInfoDouble(ACCOUNT_BALANCE);
        double daily_loss = (g_dayStartBalance>0)
            ? (g_dayStartBalance-bal)/g_accountStartBalance*100.0 : 0;
        Print("[STATUS] Syms=",g_symbol_count," Pos=",PositionsTotal(),
              " DailyLoss=",DoubleToString(daily_loss,2),"%",
              " Streak: W",g_consecutiveWins,"/L",g_consecutiveLosses,
              " Pyramid:",g_pyramidingEnabled?"ON":"off");
    }
}

void OnTick() { /* timer-driven only */ }
//+------------------------------------------------------------------+

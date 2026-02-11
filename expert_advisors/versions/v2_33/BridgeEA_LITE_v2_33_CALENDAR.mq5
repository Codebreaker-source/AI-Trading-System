//+------------------------------------------------------------------+
//|                           BridgeEA_LITE_v2_33_CALENDAR.mq5         |
//|                                            AI Trading System      |
//|     CALENDAR INTEGRATION + PYTHON SYNC UPDATE                     |
//+------------------------------------------------------------------+
#property copyright "AI Trading System"
#property link      ""
#property version   "2.33"
#property description "Bridge EA v2.33 - CALENDAR INTEGRATION"
#property description "NEW: Exports MT5 economic calendar for Python"
#property description "SYNC: FixedLotSize=0.01, MinConfidence=0.35"
#property description "KEEP: All v2.32 features (streaks, pyramiding, etc)"

//--- Input Parameters
input int TimerSeconds = 3;              // Timer interval (seconds)

//--- RISK MANAGEMENT PARAMETERS - SYNCED WITH PYTHON v5
input double FixedLotSize = 0.01;        // Fixed lot size (SYNCED with Python)
input double MinConfidence = 0.35;       // Minimum confidence (SYNCED with Python)
input double MaxDailyLossPercent = 3.0;  // Max daily loss before stopping (%)
input int MaxTotalPositions = 10;        // Maximum total open positions (base)
input double MaxPortfolioRiskPercent = 2.0;  // Max portfolio risk (%)
input double TakeProfitEquityPercent = 5.0;  // Close all profitable when equity up this %
input int MaxCorrelationExposure = 2;    // Max positions per correlation group

//--- CALENDAR INTEGRATION PARAMETERS (NEW v2.33)
input bool EnableCalendarExport = true;        // Enable calendar export for Python
input int CalendarLookAheadHours = 24;         // Hours ahead to export events
input int CalendarExportIntervalMin = 5;       // Export interval in minutes

//--- DRAWDOWN SCALING PARAMETERS (FROM v2.28)
input bool EnableDrawdownScaling = true;       // Enable drawdown-based position scaling
input double DrawdownTier1 = 0.75;             // Tier 1 threshold: reduce to 75% max positions
input double DrawdownTier2 = 1.5;              // Tier 2 threshold: reduce to 50% max positions
input double DrawdownTier3 = 2.25;             // Tier 3 threshold: reduce to 25% max positions
input double DrawdownTier4 = 3.0;              // Tier 4 threshold: STOP trading

//--- EQUITY CURVE TRAILING PARAMETERS (FROM v2.27)
input bool EnableEquityCurveTrailing = true;   // Enable equity curve trailing
input double EquityDrawdownThreshold = 3.0;    // Drawdown % to PAUSE new trades (3%)

//--- VOLATILITY REGIME FILTER PARAMETERS (FROM v2.27)
input bool EnableVolatilityFilter = true;      // Enable volatility regime filter
input double MinATRPips = 8.0;                 // Minimum ATR in pips (too quiet = no trade)
input double MaxATRPips = 100.0;               // Maximum ATR in pips (too volatile = no trade)

input int Slippage = 10;                 // Slippage in points
input int MagicNumber = 20251129;        // Magic number for trades
input double MaxSpreadPips = 5.0;        // Maximum spread for entry
input double RiskRewardRatio = 2.0;      // Risk/Reward ratio (2:1 = 2.0)
input double SL_ATR_Multiplier = 2.0;    // Stop loss = ATR * multiplier
input bool EnableTrading = true;         // Enable trade execution
input bool LogVerbose = true;            // Verbose logging

//--- BREAK-EVEN & TRAILING STOP PARAMETERS
input bool EnableBreakEven = true;       // Enable break-even logic
input bool EnableTrailing = true;        // Enable trailing stop
input double BE_TriggerRR = 0.25;        // BE trigger at this R:R (0.25 = 25% of risk)
input double BE_BufferPips = 5.0;        // Buffer above entry for BE (pips)
input double Trail_ATR_Multiplier = 2.0; // Trail distance = ATR * multiplier
input int TrailCheckSeconds = 5;         // How often to check trailing (seconds)

//--- REGIME-ADAPTIVE TRAILING PARAMETERS (FROM v2.29)
input bool EnableRegimeTrailing = true;        // Enable regime-adaptive trailing
input double Trail_ATR_Ranging = 1.5;          // Trailing multiplier for RANGING regime
input double Trail_ATR_Trending = 2.5;         // Trailing multiplier for TRENDING regime
input double Trail_ATR_Volatile = 3.5;         // Trailing multiplier for VOLATILE regime
input double RegimeATR_LowThreshold = 15.0;    // ATR below this = RANGING (pips)
input double RegimeATR_HighThreshold = 40.0;   // ATR above this = VOLATILE (pips)

//--- PARTIAL PROFIT TAKING PARAMETERS (FROM v2.30)
input bool EnablePartialTP = true;             // Enable partial profit taking
input double PartialTP_TriggerRR = 2.0;        // R:R to trigger partial close
input double PartialTP_ClosePercent = 50.0;    // Percent of position to close
input double PartialTP_ExtendRR = 3.0;         // New TP R:R for remaining position

//--- PROGRESSIVE TRAILING PARAMETERS (FROM v2.31)
input bool EnableProgressiveTrail = true;      // Enable progressive trailing
input double ProgTrail_Tier1_RR = 1.0;         // R:R threshold for tier 1
input double ProgTrail_Tier2_RR = 1.5;         // R:R threshold for tier 2
input double ProgTrail_Tier3_RR = 2.0;         // R:R threshold for tier 3
input double ProgTrail_Mult_Tier1 = 0.9;       // Trail multiplier at tier 1
input double ProgTrail_Mult_Tier2 = 0.75;      // Trail multiplier at tier 2
input double ProgTrail_Mult_Tier3 = 0.5;       // Trail multiplier at tier 3

//--- STREAK-BASED SIZING PARAMETERS (FROM v2.32)
input bool EnableStreakSizing = true;          // Enable streak-based position limits
input int LossStreak_Tier1_Count = 2;          // Losses to trigger tier 1 reduction
input int LossStreak_Tier2_Count = 3;          // Losses to trigger tier 2 reduction
input double LossStreak_Tier1_Mult = 0.70;     // Max positions multiplier at tier 1
input double LossStreak_Tier2_Mult = 0.50;     // Max positions multiplier at tier 2

//--- PYRAMIDING PARAMETERS (FROM v2.32)
input bool EnablePyramiding = true;            // Enable pyramiding on win streaks
input int WinStreak_PyramidTrigger = 3;        // Consecutive wins to enable pyramiding
input double Pyramid_MinRR = 1.0;              // Minimum R:R to pyramid
input double Pyramid_PullbackPercent = 50.0;   // Pullback % to trigger pyramid
input int Pyramid_MaxPerSymbol = 2;            // Maximum positions per symbol

//--- Technical Indicator Parameters
input int FastEMA_Period = 12;           // Fast EMA period
input int SlowEMA_Period = 26;           // Slow EMA period
input int RSI_Period = 14;               // RSI period
input int ATR_Period = 14;               // ATR period
input int BB_Period = 20;                // Bollinger Bands period
input double BB_Deviation = 2.0;         // Bollinger Bands deviation
input int Stoch_K = 14;                  // Stochastic %K period
input int Stoch_D = 3;                   // Stochastic %D period
input int Stoch_Slowing = 3;             // Stochastic slowing
input int SMA20_Period = 20;             // SMA 20 period
input int SMA50_Period = 50;             // SMA 50 period
input ENUM_TIMEFRAMES HTF_Timeframe = PERIOD_H4;  // Higher timeframe (H4)

//--- Currency Pairs
string g_pairs[8] = {
    "EURUSD.sim", "GBPUSD.sim", "USDJPY.sim", "USDCHF.sim",
    "AUDUSD.sim", "USDCAD.sim", "NZDUSD.sim", "EURGBP.sim"
};

//--- File paths
string g_featuresFile = "latest_features.csv";
string g_commandsFile = "trade_commands.csv";
string g_tradesLogFile = "trades_execution_log.csv";
string g_positionsFile = "open_positions.csv";
string g_calendarFile = "calendar_events.csv";  // NEW v2.33

//--- Indicator Handles
int g_fastEMA_handles[8];
int g_slowEMA_handles[8];
int g_rsi_handles[8];
int g_atr_handles[8];
int g_bb_handles[8];
int g_stoch_handles[8];
int g_sma20_handles[8];
int g_sma50_handles[8];
int g_htfFastEMA_handles[8];
int g_htfSlowEMA_handles[8];

//--- Trade tracking
datetime g_lastCommandTime = 0;
string g_lastCommandHash = "";
bool g_logHeaderWritten = false;

//--- BE/Trailing tracking
datetime g_lastTrailCheck = 0;
int g_beTriggeredCount = 0;
int g_trailAdjustedCount = 0;

//--- CALENDAR TRACKING (NEW v2.33)
datetime g_lastCalendarExport = 0;
int g_calendarEventsExported = 0;

//--- REGIME TRACKING (FROM v2.29)
string g_lastRegimes[8];
int g_regimeRangingCount = 0;
int g_regimeTrendingCount = 0;
int g_regimeVolatileCount = 0;

//--- PARTIAL TP TRACKING (FROM v2.30)
ulong g_partialTPTickets[50];
int g_partialTPCount = 0;
int g_partialTPTakenTotal = 0;
int g_partialTPExtendedTotal = 0;

//--- STREAK TRACKING (FROM v2.32)
int g_consecutiveWins = 0;
int g_consecutiveLosses = 0;
int g_totalWins = 0;
int g_totalLosses = 0;
int g_lastKnownHistoryCount = 0;
bool g_pyramidingEnabled = false;
int g_pyramidTradesOpened = 0;
int g_streakReducedCount = 0;

//--- DAILY LOSS LIMIT TRACKING
double g_dayStartEquity = 0;
double g_dayStartBalance = 0;
int g_currentDay = -1;
bool g_dailyLossLimitHit = false;
int g_dailyTradesBlocked = 0;

//--- Portfolio Risk Tracking
double g_currentPortfolioRisk = 0;

//--- Equity Curve Trailing Tracking
double g_peakEquity = 0;
double g_currentDrawdownPercent = 0;
bool g_inDrawdownMode = false;

//--- DRAWDOWN SCALING TRACKING
int g_currentMaxPositions = 10;
int g_currentDrawdownTier = 0;
double g_effectiveDrawdownPercent = 0;

#include <Trade\Trade.mqh>
CTrade g_trade;


//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("================================================================");
    Print("  BridgeEA_LITE_v2_33 - CALENDAR INTEGRATION + PYTHON SYNC");
    Print("================================================================");
    Print("  *** PYTHON SYNC SETTINGS ***");
    Print("    - Fixed Lot Size: ", FixedLotSize, " (matches Python)");
    Print("    - Min Confidence: ", MinConfidence, " (matches Python)");
    Print("  RISK LIMITS:");
    Print("    - Max Daily Loss: ", MaxDailyLossPercent, "%");
    Print("    - Base Max Positions: ", MaxTotalPositions);
    Print("    - Max Portfolio Risk: ", MaxPortfolioRiskPercent, "%");
    Print("    - Max Correlation Exposure: ", MaxCorrelationExposure, " per group");
    Print("  CALENDAR EXPORT (NEW v2.33): ", EnableCalendarExport ? "ON" : "OFF");
    if(EnableCalendarExport)
    {
        Print("    - Look-ahead: ", CalendarLookAheadHours, " hours");
        Print("    - Export interval: ", CalendarExportIntervalMin, " minutes");
        Print("    - File: ", g_calendarFile);
    }
    Print("  DRAWDOWN SCALING: ", EnableDrawdownScaling ? "ON" : "OFF");
    Print("  EQUITY CURVE: ", EnableEquityCurveTrailing ? "ON" : "OFF");
    Print("  VOLATILITY FILTER: ", EnableVolatilityFilter ? "ON" : "OFF");
    Print("  BE/TRAIL: ", EnableBreakEven ? "ON" : "OFF", " / ", EnableTrailing ? "ON" : "OFF");
    
    //--- Initialize daily tracking
    InitializeDailyTracking();
    
    //--- Initialize equity curve tracking
    InitializeEquityCurveTracking();
    
    //--- Initialize drawdown scaling
    g_currentMaxPositions = MaxTotalPositions;
    g_currentDrawdownTier = 0;
    g_effectiveDrawdownPercent = 0;
    
    //--- Initialize regime tracking
    for(int i = 0; i < 8; i++)
        g_lastRegimes[i] = "UNKNOWN";
    
    //--- Initialize partial TP tracking
    g_partialTPCount = 0;
    for(int i = 0; i < 50; i++)
        g_partialTPTickets[i] = 0;
    
    //--- Initialize streak tracking
    g_consecutiveWins = 0;
    g_consecutiveLosses = 0;
    g_lastKnownHistoryCount = HistoryDealsTotal();
    g_pyramidingEnabled = false;
    
    //--- Initialize calendar tracking (NEW v2.33)
    g_lastCalendarExport = 0;
    g_calendarEventsExported = 0;
    
    //--- Validate chart timeframe
    if(Period() != PERIOD_M15)
        Print("WARNING: Optimized for M15 charts! Current: ", EnumToString(Period()));
    
    //--- Initialize indicators
    bool init_success = true;
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        string pair = g_pairs[i];
        
        g_fastEMA_handles[i] = iMA(pair, 0, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_slowEMA_handles[i] = iMA(pair, 0, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_rsi_handles[i] = iRSI(pair, 0, RSI_Period, PRICE_CLOSE);
        g_atr_handles[i] = iATR(pair, 0, ATR_Period);
        g_bb_handles[i] = iBands(pair, 0, BB_Period, 0, BB_Deviation, PRICE_CLOSE);
        g_stoch_handles[i] = iStochastic(pair, 0, Stoch_K, Stoch_D, Stoch_Slowing, MODE_SMA, STO_LOWHIGH);
        g_sma20_handles[i] = iMA(pair, 0, SMA20_Period, 0, MODE_SMA, PRICE_CLOSE);
        g_sma50_handles[i] = iMA(pair, 0, SMA50_Period, 0, MODE_SMA, PRICE_CLOSE);
        g_htfFastEMA_handles[i] = iMA(pair, HTF_Timeframe, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_htfSlowEMA_handles[i] = iMA(pair, HTF_Timeframe, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        
        if(g_fastEMA_handles[i] == INVALID_HANDLE || g_atr_handles[i] == INVALID_HANDLE)
        {
            Print("ERROR: Failed to initialize indicators for ", pair);
            init_success = false;
        }
    }
    
    if(!init_success)
        return INIT_FAILED;
    
    //--- Setup trade object
    g_trade.SetExpertMagicNumber(MagicNumber);
    g_trade.SetDeviationInPoints(Slippage);
    g_trade.SetTypeFilling(ORDER_FILLING_FOK);
    
    EventSetTimer(TimerSeconds);
    InitializeTradeLog();
    
    //--- Initial calendar export (NEW v2.33)
    if(EnableCalendarExport)
        ExportCalendarEvents();
    
    Print("SUCCESS: BridgeEA v2.33 initialized");
    Print("   Starting Equity: $", DoubleToString(g_dayStartEquity, 2));
    
    return INIT_SUCCEEDED;
}


//+------------------------------------------------------------------+
//| CALENDAR EXPORT FUNCTION (NEW v2.33)                               |
//| Exports MT5 economic calendar to CSV for Python to read            |
//+------------------------------------------------------------------+
void ExportCalendarEvents()
{
    if(!EnableCalendarExport)
        return;
    
    //--- Check if enough time has passed since last export
    datetime now = TimeCurrent();
    if(now - g_lastCalendarExport < CalendarExportIntervalMin * 60)
        return;
    
    g_lastCalendarExport = now;
    
    //--- Define time range
    datetime time_from = now;
    datetime time_to = now + CalendarLookAheadHours * 3600;
    
    //--- Get calendar events
    MqlCalendarValue values[];
    int count = CalendarValueHistory(values, time_from, time_to);
    
    if(count < 0)
    {
        int error = GetLastError();
        if(error != 0)
            Print("[CALENDAR] Error getting events: ", error);
        return;
    }
    
    //--- Open file for writing
    int handle = FileOpen(g_calendarFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        Print("[CALENDAR] Failed to open file: ", g_calendarFile);
        return;
    }
    
    //--- Write header
    FileWrite(handle, "event_id,event_time,country,currency,event_name,importance,actual,forecast,previous");
    
    int events_written = 0;
    
    for(int i = 0; i < count; i++)
    {
        //--- Get event details
        MqlCalendarEvent event;
        if(!CalendarEventById(values[i].event_id, event))
            continue;
        
        //--- Get country details for currency
        MqlCalendarCountry country;
        if(!CalendarCountryById(event.country_id, country))
            continue;
        
        //--- Filter for relevant currencies (our trading pairs)
        string curr = country.currency;
        if(curr != "USD" && curr != "EUR" && curr != "GBP" && curr != "JPY" &&
           curr != "CHF" && curr != "CAD" && curr != "AUD" && curr != "NZD")
            continue;
        
        //--- Convert importance to string
        string importance_str = "LOW";
        if(event.importance == CALENDAR_IMPORTANCE_MODERATE)
            importance_str = "MEDIUM";
        else if(event.importance == CALENDAR_IMPORTANCE_HIGH)
            importance_str = "HIGH";
        
        //--- Format values (handle LONG_MIN for missing values)
        string actual_str = "";
        string forecast_str = "";
        string previous_str = "";
        
        //--- Get multiplier from event (unit is in event, not values)
        double multiplier = (event.multiplier != 0) ? (double)event.multiplier : 1.0;
        
        if(values[i].actual_value != LONG_MIN)
            actual_str = DoubleToString((double)values[i].actual_value / multiplier, 2);
        if(values[i].forecast_value != LONG_MIN)
            forecast_str = DoubleToString((double)values[i].forecast_value / multiplier, 2);
        if(values[i].prev_value != LONG_MIN)
            previous_str = DoubleToString((double)values[i].prev_value / multiplier, 2);
        
        //--- Format event time
        string time_str = TimeToString(values[i].time, TIME_DATE|TIME_MINUTES);
        
        //--- Clean event name (remove commas)
        string event_name = event.name;
        StringReplace(event_name, ",", " ");
        
        //--- Write row
        FileWrite(handle, 
            values[i].event_id,
            time_str,
            country.name,
            curr,
            event_name,
            importance_str,
            actual_str,
            forecast_str,
            previous_str
        );
        
        events_written++;
    }
    
    FileClose(handle);
    
    g_calendarEventsExported = events_written;
    
    if(LogVerbose && events_written > 0)
        Print("[CALENDAR] Exported ", events_written, " events for next ", CalendarLookAheadHours, " hours");
}

//+------------------------------------------------------------------+
//| Get high-impact events in time range (for trade blocking)          |
//+------------------------------------------------------------------+
bool HasHighImpactEventSoon(string currency, int minutes_ahead)
{
    datetime now = TimeCurrent();
    datetime check_until = now + minutes_ahead * 60;
    
    MqlCalendarValue values[];
    int count = CalendarValueHistory(values, now, check_until);
    
    if(count <= 0)
        return false;
    
    for(int i = 0; i < count; i++)
    {
        MqlCalendarEvent event;
        if(!CalendarEventById(values[i].event_id, event))
            continue;
        
        //--- Only check HIGH importance events
        if(event.importance != CALENDAR_IMPORTANCE_HIGH)
            continue;
        
        //--- Get country for currency
        MqlCalendarCountry country;
        if(!CalendarCountryById(event.country_id, country))
            continue;
        
        //--- Check if currency matches
        if(country.currency == currency)
            return true;
    }
    
    return false;
}


//+------------------------------------------------------------------+
//| Initialize daily tracking variables                                |
//+------------------------------------------------------------------+
void InitializeDailyTracking()
{
    g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
    g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    g_currentDay = dt.day_of_year;
    
    g_dailyLossLimitHit = false;
    g_dailyTradesBlocked = 0;
    
    Print("[DAILY RESET] Day ", g_currentDay, " | Start Equity: $", 
          DoubleToString(g_dayStartEquity, 2));
}

//+------------------------------------------------------------------+
//| Initialize equity curve tracking                                   |
//+------------------------------------------------------------------+
void InitializeEquityCurveTracking()
{
    g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
    g_currentDrawdownPercent = 0;
    g_inDrawdownMode = false;
}

//+------------------------------------------------------------------+
//| Initialize trade execution log                                     |
//+------------------------------------------------------------------+
void InitializeTradeLog()
{
    if(g_logHeaderWritten) return;
    
    int handle = FileOpen(g_tradesLogFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    
    FileWrite(handle, "timestamp,symbol,action,lot_size,confidence,entry_price,sl_price,tp_price,ticket,result,error_code,spread_pips,atr_value,daily_pnl_pct,dd_tier,max_pos,comment");
    FileClose(handle);
    g_logHeaderWritten = true;
}

//+------------------------------------------------------------------+
//| Check if new day and reset tracking                                |
//+------------------------------------------------------------------+
void CheckNewDay()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    int today = dt.day_of_year;
    
    if(today != g_currentDay)
    {
        Print("[NEW DAY] Resetting daily tracking from day ", g_currentDay, " to ", today);
        InitializeDailyTracking();
    }
}

//+------------------------------------------------------------------+
//| Check daily loss limit - returns true if trading allowed           |
//+------------------------------------------------------------------+
bool CheckDailyLossLimit()
{
    CheckNewDay();
    
    if(g_dailyLossLimitHit)
        return false;
    
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double daily_pnl = current_equity - g_dayStartEquity;
    double daily_pnl_percent = (daily_pnl / g_dayStartEquity) * 100.0;
    
    if(daily_pnl_percent <= -MaxDailyLossPercent)
    {
        g_dailyLossLimitHit = true;
        Print("[DAILY LOSS LIMIT HIT] ", DoubleToString(daily_pnl_percent, 2), "% - Trading halted");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Get daily P&L status string                                        |
//+------------------------------------------------------------------+
string GetDailyPnLStatus()
{
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double daily_pnl = current_equity - g_dayStartEquity;
    double daily_pnl_percent = (daily_pnl / g_dayStartEquity) * 100.0;
    return StringFormat("Daily P&L: $%.2f (%.2f%%)", daily_pnl, daily_pnl_percent);
}

//+------------------------------------------------------------------+
//| Get effective drawdown percent                                     |
//+------------------------------------------------------------------+
double GetEffectiveDrawdownPercent()
{
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    
    double total_dd = 0;
    if(g_peakEquity > 0)
        total_dd = ((g_peakEquity - current_equity) / g_peakEquity) * 100.0;
    
    double daily_dd = 0;
    if(g_dayStartEquity > 0)
    {
        double daily_pnl = current_equity - g_dayStartEquity;
        if(daily_pnl < 0)
            daily_dd = MathAbs(daily_pnl / g_dayStartEquity) * 100.0;
    }
    
    return MathMax(total_dd, daily_dd);
}

//+------------------------------------------------------------------+
//| Get drawdown-scaled max positions                                  |
//+------------------------------------------------------------------+
int GetDrawdownScaledMaxPositions()
{
    if(!EnableDrawdownScaling)
        return MaxTotalPositions;
    
    double eff_dd = GetEffectiveDrawdownPercent();
    g_effectiveDrawdownPercent = eff_dd;
    
    int new_tier = 0;
    int scaled_max = MaxTotalPositions;
    
    if(eff_dd >= DrawdownTier4)
        { new_tier = 4; scaled_max = 0; }
    else if(eff_dd >= DrawdownTier3)
        { new_tier = 3; scaled_max = (int)MathMax(1, MathRound(MaxTotalPositions * 0.25)); }
    else if(eff_dd >= DrawdownTier2)
        { new_tier = 2; scaled_max = (int)MathMax(1, MathRound(MaxTotalPositions * 0.50)); }
    else if(eff_dd >= DrawdownTier1)
        { new_tier = 1; scaled_max = (int)MathMax(1, MathRound(MaxTotalPositions * 0.75)); }
    
    if(new_tier != g_currentDrawdownTier)
    {
        Print("[DRAWDOWN TIER] ", g_currentDrawdownTier, " -> ", new_tier, 
              " | DD=", DoubleToString(eff_dd, 2), "% | MaxPos=", scaled_max);
        g_currentDrawdownTier = new_tier;
    }
    
    return scaled_max;
}


//+------------------------------------------------------------------+
//| Update equity curve tracking                                       |
//+------------------------------------------------------------------+
void UpdateEquityCurveTracking()
{
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    
    if(current_equity > g_peakEquity)
    {
        g_peakEquity = current_equity;
        if(g_inDrawdownMode)
        {
            g_inDrawdownMode = false;
            Print("[EQUITY RECOVERED] New Peak: $", DoubleToString(g_peakEquity, 2));
        }
    }
    
    g_currentDrawdownPercent = ((g_peakEquity - current_equity) / g_peakEquity) * 100.0;
    
    if(EnableEquityCurveTrailing && !g_inDrawdownMode && g_currentDrawdownPercent >= EquityDrawdownThreshold)
    {
        g_inDrawdownMode = true;
        Print("[EQUITY DRAWDOWN] ", DoubleToString(g_currentDrawdownPercent, 2), "% - New trades paused");
    }
    
    g_currentMaxPositions = GetDrawdownScaledMaxPositions();
}

//+------------------------------------------------------------------+
//| Check if equity curve allows trading                               |
//+------------------------------------------------------------------+
bool CheckEquityCurveAllowsTrading()
{
    if(!EnableEquityCurveTrailing)
        return true;
    return !g_inDrawdownMode;
}

//+------------------------------------------------------------------+
//| Get equity curve status string                                     |
//+------------------------------------------------------------------+
string GetEquityCurveStatus()
{
    string mode = g_inDrawdownMode ? "PAUSED" : "ACTIVE";
    return StringFormat("EqCurve: %s | Peak=$%.0f | DD=%.2f%% | MaxPos=%d",
                        mode, g_peakEquity, g_effectiveDrawdownPercent, g_currentMaxPositions);
}

//+------------------------------------------------------------------+
//| Update streak tracking                                             |
//+------------------------------------------------------------------+
void UpdateStreakTracking()
{
    int currentHistoryCount = HistoryDealsTotal();
    
    if(currentHistoryCount <= g_lastKnownHistoryCount)
        return;
    
    datetime start_time = TimeCurrent() - 86400;
    HistorySelect(start_time, TimeCurrent());
    
    int historyTotal = HistoryDealsTotal();
    
    for(int i = g_lastKnownHistoryCount; i < historyTotal; i++)
    {
        ulong ticket = HistoryDealGetTicket(i);
        if(ticket == 0) continue;
        
        long deal_magic = HistoryDealGetInteger(ticket, DEAL_MAGIC);
        if(deal_magic != MagicNumber) continue;
        
        ENUM_DEAL_ENTRY deal_entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket, DEAL_ENTRY);
        if(deal_entry != DEAL_ENTRY_OUT) continue;
        
        double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
        double commission = HistoryDealGetDouble(ticket, DEAL_COMMISSION);
        double swap = HistoryDealGetDouble(ticket, DEAL_SWAP);
        double net_profit = profit + commission + swap;
        
        if(net_profit > 0)
        {
            g_consecutiveWins++;
            g_consecutiveLosses = 0;
            g_totalWins++;
            
            if(EnablePyramiding && g_consecutiveWins >= WinStreak_PyramidTrigger && !g_pyramidingEnabled)
            {
                g_pyramidingEnabled = true;
                Print("[STREAK] Pyramiding ENABLED after ", g_consecutiveWins, " wins");
            }
        }
        else if(net_profit < 0)
        {
            g_consecutiveLosses++;
            g_consecutiveWins = 0;
            g_totalLosses++;
            
            if(g_pyramidingEnabled)
            {
                g_pyramidingEnabled = false;
                Print("[STREAK] Pyramiding DISABLED after loss");
            }
        }
    }
    
    g_lastKnownHistoryCount = historyTotal;
}

//+------------------------------------------------------------------+
//| Get streak-adjusted max positions                                  |
//+------------------------------------------------------------------+
int GetStreakAdjustedMaxPositions()
{
    if(!EnableStreakSizing)
        return g_currentMaxPositions;
    
    int base_max = g_currentMaxPositions;
    
    if(g_consecutiveLosses >= LossStreak_Tier2_Count)
        return (int)MathMax(1, base_max * LossStreak_Tier2_Mult);
    else if(g_consecutiveLosses >= LossStreak_Tier1_Count)
        return (int)MathMax(1, base_max * LossStreak_Tier1_Mult);
    
    return base_max;
}

//+------------------------------------------------------------------+
//| Get our position count                                             |
//+------------------------------------------------------------------+
int GetOurPositionCount()
{
    int count = 0;
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        if(PositionGetInteger(POSITION_MAGIC) == MagicNumber)
            count++;
    }
    
    return count;
}

//+------------------------------------------------------------------+
//| Count positions for a symbol                                       |
//+------------------------------------------------------------------+
int CountPositionsForSymbol(string symbol)
{
    int count = 0;
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
        if(PositionGetString(POSITION_SYMBOL) == symbol)
            count++;
    }
    
    return count;
}


//+------------------------------------------------------------------+
//| Get pip value for a symbol                                         |
//+------------------------------------------------------------------+
double GetPipValue(string symbol)
{
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    return (digits == 5 || digits == 3) ? point * 10 : point;
}

//+------------------------------------------------------------------+
//| Get pip dollar value (per 0.01 lot)                                |
//+------------------------------------------------------------------+
double GetPipDollarValue(string symbol)
{
    string base = symbol;
    StringReplace(base, ".sim", "");
    
    if(base == "EURUSD" || base == "GBPUSD" || base == "AUDUSD" || base == "NZDUSD")
        return 0.10;
    else if(base == "USDJPY")
        return 0.067;
    else if(base == "USDCHF" || base == "USDCAD")
        return 0.075;
    else if(base == "EURGBP")
        return 0.125;
    return 0.10;
}

//+------------------------------------------------------------------+
//| Calculate position risk                                            |
//+------------------------------------------------------------------+
double CalculatePositionRisk(string symbol, double entry_price, double stop_loss, double lot_size)
{
    double pip_value = GetPipValue(symbol);
    double pip_dollar = GetPipDollarValue(symbol);
    
    if(pip_value <= 0) return 0;
    
    double sl_pips = MathAbs(entry_price - stop_loss) / pip_value;
    return sl_pips * pip_dollar * (lot_size / 0.01);
}

//+------------------------------------------------------------------+
//| Calculate current portfolio risk                                   |
//+------------------------------------------------------------------+
double CalculateCurrentPortfolioRisk()
{
    double total_risk = 0;
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
        
        string symbol = PositionGetString(POSITION_SYMBOL);
        double entry = PositionGetDouble(POSITION_PRICE_OPEN);
        double sl = PositionGetDouble(POSITION_SL);
        double volume = PositionGetDouble(POSITION_VOLUME);
        
        if(sl <= 0) continue;
        
        total_risk += CalculatePositionRisk(symbol, entry, sl, volume);
    }
    
    g_currentPortfolioRisk = total_risk;
    return total_risk;
}

//+------------------------------------------------------------------+
//| Check portfolio risk limit                                         |
//+------------------------------------------------------------------+
bool CheckPortfolioRiskLimit(string symbol, string action, double lot_size, double &new_risk)
{
    double account_balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double max_risk_dollars = account_balance * (MaxPortfolioRiskPercent / 100.0);
    double current_risk = CalculateCurrentPortfolioRisk();
    
    double atr = GetATRValue(symbol);
    double sl_distance = atr * SL_ATR_Multiplier;
    
    double entry_price = (action == "BUY") ? 
        SymbolInfoDouble(symbol, SYMBOL_ASK) : 
        SymbolInfoDouble(symbol, SYMBOL_BID);
    
    double sl_price = (action == "BUY") ? 
        entry_price - sl_distance : 
        entry_price + sl_distance;
    
    new_risk = CalculatePositionRisk(symbol, entry_price, sl_price, lot_size);
    
    if(current_risk + new_risk > max_risk_dollars)
    {
        Print("[REJECTED] Portfolio risk limit | Current: $", DoubleToString(current_risk, 2),
              " + New: $", DoubleToString(new_risk, 2), " > Max: $", DoubleToString(max_risk_dollars, 2));
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Get correlation group for symbol                                   |
//+------------------------------------------------------------------+
int GetCorrelationGroup(string symbol)
{
    string base = symbol;
    StringReplace(base, ".sim", "");
    
    if(base == "EURUSD" || base == "GBPUSD" || base == "EURGBP")
        return 0;  // European
    if(base == "AUDUSD" || base == "NZDUSD")
        return 1;  // Antipodean
    if(base == "USDJPY" || base == "USDCHF" || base == "USDCAD")
        return 2;  // USD-base
    return 3;
}

//+------------------------------------------------------------------+
//| Count positions in correlation group                               |
//+------------------------------------------------------------------+
int CountPositionsInCorrelationGroup(int target_group)
{
    int count = 0;
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
        
        string symbol = PositionGetString(POSITION_SYMBOL);
        if(GetCorrelationGroup(symbol) == target_group)
            count++;
    }
    
    return count;
}

//+------------------------------------------------------------------+
//| Check correlation exposure                                         |
//+------------------------------------------------------------------+
bool CheckCorrelationExposure(string symbol)
{
    int group = GetCorrelationGroup(symbol);
    int current_count = CountPositionsInCorrelationGroup(group);
    
    if(current_count >= MaxCorrelationExposure)
    {
        Print("[REJECTED] Correlation limit for group ", group, " (", current_count, "/", MaxCorrelationExposure, ")");
        return false;
    }
    
    return true;
}


//+------------------------------------------------------------------+
//| Convert ATR to pips                                                |
//+------------------------------------------------------------------+
double ATRToPips(string symbol, double atr_value)
{
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    double pip_size = (digits == 5 || digits == 3) ? point * 10 : point;
    return (pip_size > 0) ? atr_value / pip_size : 0;
}

//+------------------------------------------------------------------+
//| Check volatility regime                                            |
//+------------------------------------------------------------------+
bool CheckVolatilityRegime(string symbol, double &atr_pips, string &regime)
{
    if(!EnableVolatilityFilter)
    {
        regime = "DISABLED";
        atr_pips = 0;
        return true;
    }
    
    double atr_value = GetATRValue(symbol);
    atr_pips = ATRToPips(symbol, atr_value);
    
    if(atr_pips < MinATRPips)
    {
        regime = "TOO_QUIET";
        return false;
    }
    
    if(atr_pips > MaxATRPips)
    {
        regime = "TOO_VOLATILE";
        return false;
    }
    
    regime = "NORMAL";
    return true;
}

//+------------------------------------------------------------------+
//| Get current market regime                                          |
//+------------------------------------------------------------------+
string GetCurrentRegime(string symbol, double atr_pips)
{
    if(atr_pips <= 0)
        return "TRENDING";
    
    if(atr_pips < RegimeATR_LowThreshold)
        return "RANGING";
    else if(atr_pips > RegimeATR_HighThreshold)
        return "VOLATILE";
    
    return "TRENDING";
}

//+------------------------------------------------------------------+
//| Get regime trail multiplier                                        |
//+------------------------------------------------------------------+
double GetRegimeTrailMultiplier(string symbol, double atr)
{
    if(!EnableRegimeTrailing)
        return Trail_ATR_Multiplier;
    
    double atr_pips = ATRToPips(symbol, atr);
    string regime = GetCurrentRegime(symbol, atr_pips);
    
    if(regime == "RANGING")
        return Trail_ATR_Ranging;
    else if(regime == "VOLATILE")
        return Trail_ATR_Volatile;
    
    return Trail_ATR_Trending;
}

//+------------------------------------------------------------------+
//| Get progressive trail modifier                                     |
//+------------------------------------------------------------------+
double GetProgressiveTrailModifier(double current_rr)
{
    if(!EnableProgressiveTrail)
        return 1.0;
    
    if(current_rr >= ProgTrail_Tier3_RR)
        return ProgTrail_Mult_Tier3;
    else if(current_rr >= ProgTrail_Tier2_RR)
        return ProgTrail_Mult_Tier2;
    else if(current_rr >= ProgTrail_Tier1_RR)
        return ProgTrail_Mult_Tier1;
    
    return 1.0;
}

//+------------------------------------------------------------------+
//| Get combined trail multiplier                                      |
//+------------------------------------------------------------------+
double GetCombinedTrailMultiplier(string symbol, double atr, double current_rr)
{
    double regime_mult = GetRegimeTrailMultiplier(symbol, atr);
    double prog_modifier = GetProgressiveTrailModifier(current_rr);
    return regime_mult * prog_modifier;
}

//+------------------------------------------------------------------+
//| Get ATR value for symbol                                           |
//+------------------------------------------------------------------+
double GetATRValue(string symbol)
{
    int idx = -1;
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        if(g_pairs[i] == symbol) { idx = i; break; }
    }
    
    if(idx < 0) return 0.0001;
    
    double atr[];
    if(CopyBuffer(g_atr_handles[idx], 0, 0, 1, atr) > 0)
        return atr[0];
    
    return 0.0001;
}

//+------------------------------------------------------------------+
//| Get spread in pips                                                 |
//+------------------------------------------------------------------+
double GetSpreadInPips(string symbol)
{
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    
    if(point <= 0) point = 0.00001;
    double pip_factor = (digits == 3 || digits == 5) ? 10.0 : 1.0;
    
    return (ask - bid) / point / pip_factor;
}


//+------------------------------------------------------------------+
//| Timer function - Main loop                                         |
//+------------------------------------------------------------------+
void OnTimer()
{
    CheckNewDay();
    UpdateEquityCurveTracking();
    
    //--- Export calendar events periodically (NEW v2.33)
    if(EnableCalendarExport)
        ExportCalendarEvents();
    
    WriteFeaturesSparse();
    WriteOpenPositions();
    
    if(EnableTrading && CheckDailyLossLimit())
    {
        ProcessTradeCommands();
    }
    else if(EnableTrading && g_dailyLossLimitHit)
    {
        if(FileIsExist(g_commandsFile))
        {
            g_dailyTradesBlocked++;
            if(g_dailyTradesBlocked <= 5)
                Print("[BLOCKED] Trade command ignored - Daily loss limit active");
            FileDelete(g_commandsFile);
        }
    }
    
    UpdateStreakTracking();
    CheckPyramidOpportunities();
    
    if(EnableBreakEven || EnableTrailing || EnablePartialTP)
    {
        datetime now = TimeCurrent();
        if(now - g_lastTrailCheck >= TrailCheckSeconds)
        {
            ManagePartialProfits();
            ManageOpenPositions();
            g_lastTrailCheck = now;
        }
    }
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                            |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    EventKillTimer();
    
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        if(g_fastEMA_handles[i] != INVALID_HANDLE) IndicatorRelease(g_fastEMA_handles[i]);
        if(g_slowEMA_handles[i] != INVALID_HANDLE) IndicatorRelease(g_slowEMA_handles[i]);
        if(g_rsi_handles[i] != INVALID_HANDLE) IndicatorRelease(g_rsi_handles[i]);
        if(g_atr_handles[i] != INVALID_HANDLE) IndicatorRelease(g_atr_handles[i]);
        if(g_bb_handles[i] != INVALID_HANDLE) IndicatorRelease(g_bb_handles[i]);
        if(g_stoch_handles[i] != INVALID_HANDLE) IndicatorRelease(g_stoch_handles[i]);
        if(g_sma20_handles[i] != INVALID_HANDLE) IndicatorRelease(g_sma20_handles[i]);
        if(g_sma50_handles[i] != INVALID_HANDLE) IndicatorRelease(g_sma50_handles[i]);
        if(g_htfFastEMA_handles[i] != INVALID_HANDLE) IndicatorRelease(g_htfFastEMA_handles[i]);
        if(g_htfSlowEMA_handles[i] != INVALID_HANDLE) IndicatorRelease(g_htfSlowEMA_handles[i]);
    }
    
    Print("[SESSION SUMMARY] Wins: ", g_totalWins, " | Losses: ", g_totalLosses,
          " | Calendar Events: ", g_calendarEventsExported);
}

//+------------------------------------------------------------------+
//| Process trade commands from Python                                 |
//+------------------------------------------------------------------+
void ProcessTradeCommands()
{
    if(!FileIsExist(g_commandsFile)) return;
    
    int handle = FileOpen(g_commandsFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    
    // Skip header
    for(int i = 0; i < 7; i++) FileReadString(handle);
    
    int commands_processed = 0;
    int commands_skipped = 0;
    
    while(!FileIsEnding(handle))
    {
        string symbol = FileReadString(handle);
        string action = FileReadString(handle);
        double confidence = StringToDouble(FileReadString(handle));
        double sl_price = StringToDouble(FileReadString(handle));
        double tp_price = StringToDouble(FileReadString(handle));
        double lot_size = StringToDouble(FileReadString(handle));
        string timestamp_str = FileReadString(handle);
        
        if(symbol == "" || action == "") continue;
        
        if(LogVerbose)
            Print("READ: ", symbol, " | ", action, " | Conf:", confidence, 
                  " | SL:", sl_price, " | TP:", tp_price, " | Lot:", lot_size);
        
        bool success = false;
        
        if(action == "BUY" || action == "SELL")
            success = ExecuteTrade(symbol, action, confidence, sl_price, tp_price);
        else if(action == "SCALE_OUT")
            success = ExecuteScaleOut(symbol, confidence, lot_size);
        
        if(success) commands_processed++;
        else commands_skipped++;
    }
    
    FileClose(handle);
    
    if(commands_processed > 0 || commands_skipped > 0)
        Print("Commands: ", commands_processed, " executed, ", commands_skipped, " rejected");
    
    if(commands_processed > 0)
        FileDelete(g_commandsFile);
}


//+------------------------------------------------------------------+
//| Execute a trade                                                    |
//+------------------------------------------------------------------+
bool ExecuteTrade(string symbol, string action, double confidence, double sl_price_in = 0, double tp_price_in = 0)
{
    //--- Check confidence
    if(confidence < MinConfidence)
    {
        Print("[REJECTED] ", symbol, " - Confidence ", confidence, " < ", MinConfidence);
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "LOW_CONFIDENCE");
        return false;
    }
    
    //--- Get streak-adjusted max positions
    int scaled_max = GetStreakAdjustedMaxPositions();
    
    if(scaled_max <= 0)
    {
        Print("[REJECTED] Trading stopped - Drawdown/Streak protection");
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "MAX_POS_ZERO");
        return false;
    }
    
    //--- Check position limit
    int current_positions = GetOurPositionCount();
    if(current_positions >= scaled_max)
    {
        Print("[REJECTED] ", symbol, " - Positions: ", current_positions, "/", scaled_max);
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "MAX_POSITIONS");
        return false;
    }
    
    //--- Check portfolio risk
    double new_risk = 0;
    if(!CheckPortfolioRiskLimit(symbol, action, FixedLotSize, new_risk))
    {
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "PORTFOLIO_RISK");
        return false;
    }
    
    //--- Check correlation
    if(!CheckCorrelationExposure(symbol))
    {
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "CORRELATION");
        return false;
    }
    
    //--- Check equity curve
    if(!CheckEquityCurveAllowsTrading())
    {
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "EQUITY_DD");
        return false;
    }
    
    //--- Check volatility
    double vol_atr_pips = 0;
    string vol_regime = "";
    if(!CheckVolatilityRegime(symbol, vol_atr_pips, vol_regime))
    {
        Print("[REJECTED] ", symbol, " - Volatility: ", vol_regime);
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "VOLATILITY");
        return false;
    }
    
    //--- Validate symbol
    if(!SymbolInfoInteger(symbol, SYMBOL_SELECT))
    {
        if(!SymbolSelect(symbol, true))
        {
            LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "FAILED", 0, "INVALID_SYMBOL");
            return false;
        }
        Sleep(100);
    }
    
    //--- Check spread
    double spread_pips = GetSpreadInPips(symbol);
    if(spread_pips > MaxSpreadPips)
    {
        Print("[REJECTED] ", symbol, " - Spread ", spread_pips, " > ", MaxSpreadPips);
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "SPREAD");
        return false;
    }
    
    //--- Fixed lot size
    double lot_size = FixedLotSize;
    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    
    lot_size = MathMax(lot_size, lot_min);
    lot_size = MathMin(lot_size, lot_max);
    lot_size = NormalizeDouble(MathRound(lot_size / lot_step) * lot_step, 2);
    
    //--- Get entry price
    double entry_price = (action == "BUY") ? 
        SymbolInfoDouble(symbol, SYMBOL_ASK) : 
        SymbolInfoDouble(symbol, SYMBOL_BID);
    
    ENUM_ORDER_TYPE order_type = (action == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    
    //--- SL/TP from Python or ATR fallback
    double sl_price = 0;
    double tp_price = 0;
    
    if(sl_price_in > 0 && tp_price_in > 0)
    {
        sl_price = sl_price_in;
        tp_price = tp_price_in;
    }
    else
    {
        double atr = GetATRValue(symbol);
        double sl_distance = atr * SL_ATR_Multiplier;
        double tp_distance = sl_distance * RiskRewardRatio;
        
        if(action == "BUY")
        {
            sl_price = entry_price - sl_distance;
            tp_price = entry_price + tp_distance;
        }
        else
        {
            sl_price = entry_price + sl_distance;
            tp_price = entry_price - tp_distance;
        }
    }
    
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    sl_price = NormalizeDouble(sl_price, digits);
    tp_price = NormalizeDouble(tp_price, digits);
    
    //--- Send order
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = symbol;
    request.volume = lot_size;
    request.type = order_type;
    request.price = entry_price;
    request.sl = sl_price;
    request.tp = tp_price;
    request.deviation = Slippage;
    request.magic = MagicNumber;
    request.comment = StringFormat("AI_%.0f%%_v2.33", confidence * 100);
    request.type_filling = ORDER_FILLING_FOK;
    
    bool success = OrderSend(request, result);
    
    LogTrade(symbol, action, lot_size, confidence, entry_price, sl_price, tp_price,
             result.order, success ? "SUCCESS" : "FAILED", result.retcode, "");
    
    if(success)
        Print("[SUCCESS] ", symbol, " ", action, " ", lot_size, " @ ", entry_price);
    else
        Print("[FAILED] ", symbol, " | Error: ", result.retcode);
    
    return success;
}


//+------------------------------------------------------------------+
//| Execute scale out                                                  |
//+------------------------------------------------------------------+
bool ExecuteScaleOut(string symbol, double confidence, double requested_lot = 0.05)
{
    if(!PositionSelect(symbol))
    {
        LogTrade(symbol, "SCALE_OUT", 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "NO_POSITION");
        return false;
    }
    
    double pos_volume = PositionGetDouble(POSITION_VOLUME);
    ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    ulong pos_ticket = PositionGetInteger(POSITION_TICKET);
    
    double scale_volume = (requested_lot > 0) ? requested_lot : 0.05;
    if(scale_volume > pos_volume)
        scale_volume = pos_volume;
    
    double min_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    if(scale_volume < min_lot)
    {
        LogTrade(symbol, "SCALE_OUT", 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "VOLUME_TOO_SMALL");
        return false;
    }
    
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = symbol;
    request.volume = scale_volume;
    request.position = pos_ticket;
    request.deviation = Slippage;
    request.magic = MagicNumber;
    request.comment = "SCALE_OUT";
    request.type_filling = ORDER_FILLING_FOK;
    
    if(pos_type == POSITION_TYPE_BUY)
    {
        request.type = ORDER_TYPE_SELL;
        request.price = SymbolInfoDouble(symbol, SYMBOL_BID);
    }
    else
    {
        request.type = ORDER_TYPE_BUY;
        request.price = SymbolInfoDouble(symbol, SYMBOL_ASK);
    }
    
    bool success = OrderSend(request, result);
    
    LogTrade(symbol, "SCALE_OUT", scale_volume, confidence, request.price, 0, 0,
             result.order, success ? "SUCCESS" : "FAILED", result.retcode, "");
    
    if(success)
        Print("[SCALE_OUT] ", symbol, " closed ", scale_volume, " lots");
    
    return success;
}

//+------------------------------------------------------------------+
//| Log trade to file                                                  |
//+------------------------------------------------------------------+
void LogTrade(string symbol, string action, double lot_size, double confidence,
              double entry_price, double sl_price, double tp_price,
              ulong ticket, string result_str, uint error_code, string comment)
{
    int handle = FileOpen(g_tradesLogFile, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    
    FileSeek(handle, 0, SEEK_END);
    
    string timestamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS);
    double spread_pips = GetSpreadInPips(symbol);
    double atr_value = GetATRValue(symbol);
    double daily_pnl_pct = 0;
    if(g_dayStartEquity > 0)
        daily_pnl_pct = ((AccountInfoDouble(ACCOUNT_EQUITY) - g_dayStartEquity) / g_dayStartEquity) * 100;
    
    string log_entry = StringFormat("%s,%s,%s,%.2f,%.2f,%.5f,%.5f,%.5f,%d,%s,%d,%.2f,%.5f,%.2f,%d,%d,%s",
        timestamp, symbol, action, lot_size, confidence, entry_price, sl_price, tp_price,
        ticket, result_str, error_code, spread_pips, atr_value, daily_pnl_pct,
        g_currentDrawdownTier, g_currentMaxPositions, comment);
    
    FileWrite(handle, log_entry);
    FileClose(handle);
}

//+------------------------------------------------------------------+
//| Check partial TP taken                                             |
//+------------------------------------------------------------------+
bool HasTakenPartialTP(ulong ticket)
{
    for(int i = 0; i < g_partialTPCount; i++)
        if(g_partialTPTickets[i] == ticket)
            return true;
    return false;
}

void MarkPartialTPTaken(ulong ticket)
{
    if(HasTakenPartialTP(ticket)) return;
    if(g_partialTPCount < 50)
    {
        g_partialTPTickets[g_partialTPCount] = ticket;
        g_partialTPCount++;
    }
}

//+------------------------------------------------------------------+
//| Manage partial profits                                             |
//+------------------------------------------------------------------+
void ManagePartialProfits()
{
    if(!EnablePartialTP) return;
    
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
        if(HasTakenPartialTP(ticket)) continue;
        
        string symbol = PositionGetString(POSITION_SYMBOL);
        ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
        double entry_price = PositionGetDouble(POSITION_PRICE_OPEN);
        double current_sl = PositionGetDouble(POSITION_SL);
        double current_tp = PositionGetDouble(POSITION_TP);
        double volume = PositionGetDouble(POSITION_VOLUME);
        
        if(volume < 0.02) continue;
        
        double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
        double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
        double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
        int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
        
        double initial_risk = 0;
        double current_profit_distance = 0;
        
        if(pos_type == POSITION_TYPE_BUY)
        {
            initial_risk = entry_price - current_sl;
            current_profit_distance = bid - entry_price;
        }
        else
        {
            initial_risk = current_sl - entry_price;
            current_profit_distance = entry_price - ask;
        }
        
        if(initial_risk <= 0) continue;
        
        double current_rr = current_profit_distance / initial_risk;
        
        if(current_rr >= PartialTP_TriggerRR)
        {
            double close_volume = NormalizeDouble(volume * (PartialTP_ClosePercent / 100.0), 2);
            double min_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
            
            if(close_volume < min_lot) close_volume = min_lot;
            if(close_volume > volume - min_lot) close_volume = volume - min_lot;
            if(close_volume < min_lot) continue;
            
            bool closed = g_trade.PositionClosePartial(ticket, close_volume);
            
            if(closed)
            {
                double pip_factor = (digits == 3 || digits == 5) ? 10.0 : 1.0;
                double pip_value = point * pip_factor;
                double be_buffer = 2.0 * pip_value;
                
                double new_sl = (pos_type == POSITION_TYPE_BUY) ? 
                    entry_price + be_buffer : entry_price - be_buffer;
                new_sl = NormalizeDouble(new_sl, digits);
                
                double new_tp = 0;
                double extended_distance = initial_risk * PartialTP_ExtendRR;
                new_tp = (pos_type == POSITION_TYPE_BUY) ?
                    entry_price + extended_distance : entry_price - extended_distance;
                new_tp = NormalizeDouble(new_tp, digits);
                
                g_trade.PositionModify(ticket, new_sl, new_tp);
                MarkPartialTPTaken(ticket);
                g_partialTPTakenTotal++;
                
                Print("[PARTIAL TP] ", symbol, " @ ", DoubleToString(current_rr, 1), ":1 R:R");
            }
        }
    }
}


//+------------------------------------------------------------------+
//| Manage open positions (BE & Trailing)                              |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
        
        string symbol = PositionGetString(POSITION_SYMBOL);
        ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
        double entry_price = PositionGetDouble(POSITION_PRICE_OPEN);
        double current_sl = PositionGetDouble(POSITION_SL);
        double current_tp = PositionGetDouble(POSITION_TP);
        
        double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
        double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
        double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
        int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
        
        double pip_factor = (digits == 3 || digits == 5) ? 10.0 : 1.0;
        double pip_value = point * pip_factor;
        
        double initial_risk = 0;
        double current_profit_distance = 0;
        double current_price = 0;
        
        if(pos_type == POSITION_TYPE_BUY)
        {
            current_price = bid;
            initial_risk = entry_price - current_sl;
            current_profit_distance = current_price - entry_price;
        }
        else
        {
            current_price = ask;
            initial_risk = current_sl - entry_price;
            current_profit_distance = entry_price - current_price;
        }
        
        if(initial_risk <= 0) continue;
        
        double current_rr = current_profit_distance / initial_risk;
        
        double atr = GetATRValue(symbol);
        double trail_multiplier = GetCombinedTrailMultiplier(symbol, atr, current_rr);
        double trail_distance = atr * trail_multiplier;
        
        double be_buffer = BE_BufferPips * pip_value;
        double be_level = (pos_type == POSITION_TYPE_BUY) ? 
            entry_price + be_buffer : entry_price - be_buffer;
        be_level = NormalizeDouble(be_level, digits);
        
        bool at_breakeven = (pos_type == POSITION_TYPE_BUY) ? 
            (current_sl >= entry_price) : (current_sl <= entry_price && current_sl > 0);
        
        //--- Break-even logic
        if(EnableBreakEven && !at_breakeven && current_rr >= BE_TriggerRR)
        {
            if(ModifyPositionSL(ticket, symbol, be_level, current_tp))
            {
                g_beTriggeredCount++;
                Print("[BE] ", symbol, " @ ", DoubleToString(current_rr, 2), ":1 R:R");
            }
            continue;
        }
        
        //--- Trailing stop logic
        if(EnableTrailing && at_breakeven)
        {
            double new_sl = 0;
            bool should_trail = false;
            
            if(pos_type == POSITION_TYPE_BUY)
            {
                new_sl = NormalizeDouble(current_price - trail_distance, digits);
                if(new_sl > current_sl + (5 * point))
                    should_trail = true;
            }
            else
            {
                new_sl = NormalizeDouble(current_price + trail_distance, digits);
                if(new_sl < current_sl - (5 * point) || current_sl == 0)
                    should_trail = true;
            }
            
            if(should_trail)
            {
                if(ModifyPositionSL(ticket, symbol, new_sl, current_tp))
                    g_trailAdjustedCount++;
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Modify position stop loss                                          |
//+------------------------------------------------------------------+
bool ModifyPositionSL(ulong ticket, string symbol, double new_sl, double current_tp)
{
    long stop_level = SymbolInfoInteger(symbol, SYMBOL_TRADE_STOPS_LEVEL);
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    double min_distance = stop_level * point;
    double current_price = SymbolInfoDouble(symbol, SYMBOL_BID);
    
    if(MathAbs(new_sl - current_price) < min_distance)
        return false;
    
    return g_trade.PositionModify(ticket, new_sl, current_tp);
}

//+------------------------------------------------------------------+
//| Check pyramid opportunities                                        |
//+------------------------------------------------------------------+
void CheckPyramidOpportunities()
{
    if(!EnablePyramiding || !g_pyramidingEnabled)
        return;
    
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
        
        string symbol = PositionGetString(POSITION_SYMBOL);
        ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
        double entry_price = PositionGetDouble(POSITION_PRICE_OPEN);
        double current_sl = PositionGetDouble(POSITION_SL);
        
        int symbol_positions = CountPositionsForSymbol(symbol);
        if(symbol_positions >= Pyramid_MaxPerSymbol)
            continue;
        
        double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
        double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
        int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
        
        double initial_risk = 0;
        double current_profit_distance = 0;
        double current_price = 0;
        
        if(pos_type == POSITION_TYPE_BUY)
        {
            current_price = bid;
            initial_risk = entry_price - current_sl;
            current_profit_distance = current_price - entry_price;
        }
        else
        {
            current_price = ask;
            initial_risk = current_sl - entry_price;
            current_profit_distance = entry_price - current_price;
        }
        
        if(initial_risk <= 0) continue;
        
        double current_rr = current_profit_distance / initial_risk;
        
        if(current_rr < Pyramid_MinRR)
            continue;
        
        // Check total positions limit
        int streak_max = GetStreakAdjustedMaxPositions();
        if(PositionsTotal() >= streak_max)
            continue;
        
        // Simple pyramid logic: if position is profitable enough, add at pullback
        double pullback_trigger = entry_price + (current_profit_distance * (1 - Pyramid_PullbackPercent / 100.0));
        
        bool should_pyramid = false;
        if(pos_type == POSITION_TYPE_BUY && current_price <= pullback_trigger && current_price > entry_price)
            should_pyramid = true;
        else if(pos_type == POSITION_TYPE_SELL && current_price >= pullback_trigger && current_price < entry_price)
            should_pyramid = true;
        
        if(should_pyramid)
        {
            double lot_size = FixedLotSize;
            double tp_distance = initial_risk * RiskRewardRatio;
            double new_tp = (pos_type == POSITION_TYPE_BUY) ? 
                current_price + tp_distance : current_price - tp_distance;
            new_tp = NormalizeDouble(new_tp, digits);
            
            bool success = false;
            if(pos_type == POSITION_TYPE_BUY)
                success = g_trade.Buy(lot_size, symbol, 0, current_sl, new_tp, "PYRAMID");
            else
                success = g_trade.Sell(lot_size, symbol, 0, current_sl, new_tp, "PYRAMID");
            
            if(success)
            {
                g_pyramidTradesOpened++;
                Print("[PYRAMID] ", symbol, " @ ", DoubleToString(current_rr, 1), ":1 R:R");
            }
        }
    }
}


//+------------------------------------------------------------------+
//| Write open positions to CSV                                        |
//+------------------------------------------------------------------+
void WriteOpenPositions()
{
    int handle = FileOpen(g_positionsFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    
    FileWrite(handle, "symbol", "ticket", "direction", "volume", "entry_price", 
              "sl", "tp", "profit", "magic", "open_time", "be_status", "trail_active");
    
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
        
        string symbol = PositionGetString(POSITION_SYMBOL);
        ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
        double volume = PositionGetDouble(POSITION_VOLUME);
        double entry = PositionGetDouble(POSITION_PRICE_OPEN);
        double sl = PositionGetDouble(POSITION_SL);
        double tp = PositionGetDouble(POSITION_TP);
        double profit = PositionGetDouble(POSITION_PROFIT);
        datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
        
        string direction = (type == POSITION_TYPE_BUY) ? "BUY" : "SELL";
        
        bool at_be = (type == POSITION_TYPE_BUY) ? (sl >= entry) : (sl <= entry && sl > 0);
        string be_status = at_be ? "YES" : "NO";
        string trail_active = (at_be && EnableTrailing) ? "YES" : "NO";
        
        FileWrite(handle, symbol, ticket, direction, volume, entry, sl, tp, 
                  profit, MagicNumber, TimeToString(open_time, TIME_DATE|TIME_MINUTES),
                  be_status, trail_active);
    }
    
    FileClose(handle);
}

//+------------------------------------------------------------------+
//| Feature calculation helpers                                        |
//+------------------------------------------------------------------+
double CalculateVolumeSMA(string symbol, int period)
{
    double sum = 0;
    for(int i = 0; i < period; i++)
        sum += (double)iVolume(symbol, PERIOD_CURRENT, i);
    return sum / period;
}

double CalculateVolatility(string symbol, int period)
{
    double sum = 0;
    for(int i = 0; i < period; i++)
        sum += iHigh(symbol, PERIOD_CURRENT, i) - iLow(symbol, PERIOD_CURRENT, i);
    return sum / period;
}

double CalculateATRAverage(string symbol, int period)
{
    double sum = 0;
    for(int i = 0; i < period; i++)
    {
        double high = iHigh(symbol, PERIOD_CURRENT, i);
        double low = iLow(symbol, PERIOD_CURRENT, i);
        double close_prev = iClose(symbol, PERIOD_CURRENT, i+1);
        double tr = MathMax(high - low, MathMax(MathAbs(high - close_prev), MathAbs(low - close_prev)));
        sum += tr;
    }
    return sum / period;
}

double CalculateReturnsStd(string symbol, int period)
{
    double returns[];
    ArrayResize(returns, period);
    
    for(int i = 0; i < period; i++)
    {
        double close_cur = iClose(symbol, PERIOD_CURRENT, i);
        double close_prev = iClose(symbol, PERIOD_CURRENT, i+1);
        returns[i] = (close_prev > 0) ? (close_cur - close_prev) / close_prev : 0;
    }
    
    double mean = 0;
    for(int i = 0; i < period; i++) mean += returns[i];
    mean /= period;
    
    double variance = 0;
    for(int i = 0; i < period; i++)
        variance += MathPow(returns[i] - mean, 2);
    
    return MathSqrt(variance / period);
}

double CalculateSharpeApprox(string symbol, int period)
{
    double returns[];
    ArrayResize(returns, period);
    
    for(int i = 0; i < period; i++)
    {
        double close_cur = iClose(symbol, PERIOD_CURRENT, i);
        double close_prev = iClose(symbol, PERIOD_CURRENT, i+1);
        returns[i] = (close_prev > 0) ? (close_cur - close_prev) / close_prev : 0;
    }
    
    double mean = 0;
    for(int i = 0; i < period; i++) mean += returns[i];
    mean /= period;
    
    double std = CalculateReturnsStd(symbol, period);
    return (std > 0) ? mean / std : 0;
}

double CalculateMaxDrawdown(string symbol, int period)
{
    double max_price = iClose(symbol, PERIOD_CURRENT, 0);
    double max_dd = 0;
    
    for(int i = 0; i < period; i++)
    {
        double close = iClose(symbol, PERIOD_CURRENT, i);
        if(close > max_price) max_price = close;
        double dd = (max_price > 0) ? (close - max_price) / max_price : 0;
        if(dd < max_dd) max_dd = dd;
    }
    return max_dd;
}

double CalculateCorrelation(string symbol1, string symbol2, int period)
{
    double closes1[], closes2[];
    ArrayResize(closes1, period);
    ArrayResize(closes2, period);
    
    for(int i = 0; i < period; i++)
    {
        closes1[i] = iClose(symbol1, PERIOD_CURRENT, i);
        closes2[i] = iClose(symbol2, PERIOD_CURRENT, i);
    }
    
    double mean1 = 0, mean2 = 0;
    for(int i = 0; i < period; i++) { mean1 += closes1[i]; mean2 += closes2[i]; }
    mean1 /= period; mean2 /= period;
    
    double cov = 0, var1 = 0, var2 = 0;
    for(int i = 0; i < period; i++)
    {
        double diff1 = closes1[i] - mean1;
        double diff2 = closes2[i] - mean2;
        cov += diff1 * diff2;
        var1 += diff1 * diff1;
        var2 += diff2 * diff2;
    }
    
    double denom = MathSqrt(var1 * var2);
    return (denom > 0) ? cov / denom : 0;
}

void CalculateCurrencyStrengths(double &close_prices[], double &strengths[])
{
    for(int i = 0; i < 8; i++)
        strengths[i] = 50.0 + (MathRand() % 1000) / 20.0;
}


//+------------------------------------------------------------------+
//| Write features in SPARSE format - 58 features                      |
//+------------------------------------------------------------------+
void WriteFeaturesSparse()
{
    int handle = FileOpen(g_featuresFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    
    string header = "timestamp,symbol,close,high,low,volume,sma_20,sma_50,fast_ema,slow_ema,rsi,atr,";
    header += "bb_upper,bb_middle,bb_lower,stoch_k,stoch_d,volume_sma,volume_ratio,price_volume,";
    header += "volatility,momentum,trend_confirm,momentum_confirm,volatility_confirm,";
    header += "returns_std,sharpe_approx,max_drawdown,";
    header += "htf_fast_ema,htf_slow_ema,htf_trend_direction,htf_trend_alignment,";
    header += "bullish_sentiment,bearish_sentiment,net_sentiment,";
    header += "corr_eurusd.sim,corr_gbpusd.sim,corr_usdjpy.sim,corr_usdchf.sim,";
    header += "corr_audusd.sim,corr_usdcad.sim,corr_nzdusd.sim,corr_eurgbp.sim,avg_correlation,";
    header += "usd_strength,eur_strength,gbp_strength,jpy_strength,chf_strength,cad_strength,aud_strength,nzd_strength,";
    header += "htf_confirm,price_action_confirm,correlation_confirm,ema_confirm,rsi_confirm,volume_confirm,bb_confirm,stoch_confirm";
    
    FileWrite(handle, header);
    
    string timestamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS);
    
    double close_prices[8];
    for(int i = 0; i < 8; i++)
        close_prices[i] = iClose(g_pairs[i], PERIOD_CURRENT, 0);
    
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        string pair = g_pairs[i];
        
        double close = iClose(pair, PERIOD_CURRENT, 0);
        double high = iHigh(pair, PERIOD_CURRENT, 0);
        double low = iLow(pair, PERIOD_CURRENT, 0);
        long volume = iVolume(pair, PERIOD_CURRENT, 0);
        
        if(close == 0 || high == 0 || low == 0) continue;
        
        double fastEMA[], slowEMA[], rsi[], atr[];
        double bb_upper[], bb_middle[], bb_lower[];
        double stoch_k[], stoch_d[], sma20[], sma50[];
        double htfFastEMA[], htfSlowEMA[];
        
        if(CopyBuffer(g_fastEMA_handles[i], 0, 0, 1, fastEMA) <= 0) continue;
        if(CopyBuffer(g_slowEMA_handles[i], 0, 0, 1, slowEMA) <= 0) continue;
        if(CopyBuffer(g_rsi_handles[i], 0, 0, 1, rsi) <= 0) continue;
        if(CopyBuffer(g_atr_handles[i], 0, 0, 1, atr) <= 0) continue;
        if(CopyBuffer(g_bb_handles[i], 1, 0, 1, bb_upper) <= 0) continue;
        if(CopyBuffer(g_bb_handles[i], 0, 0, 1, bb_middle) <= 0) continue;
        if(CopyBuffer(g_bb_handles[i], 2, 0, 1, bb_lower) <= 0) continue;
        if(CopyBuffer(g_stoch_handles[i], 0, 0, 1, stoch_k) <= 0) continue;
        if(CopyBuffer(g_stoch_handles[i], 1, 0, 1, stoch_d) <= 0) continue;
        if(CopyBuffer(g_sma20_handles[i], 0, 0, 1, sma20) <= 0) continue;
        if(CopyBuffer(g_sma50_handles[i], 0, 0, 1, sma50) <= 0) continue;
        if(CopyBuffer(g_htfFastEMA_handles[i], 0, 0, 1, htfFastEMA) <= 0) continue;
        if(CopyBuffer(g_htfSlowEMA_handles[i], 0, 0, 1, htfSlowEMA) <= 0) continue;
        
        double volume_sma = CalculateVolumeSMA(pair, 20);
        double volume_ratio = (volume_sma > 0) ? (double)volume / volume_sma : 1.0;
        double price_volume = close * volume;
        
        double close_20 = iClose(pair, PERIOD_CURRENT, 20);
        double momentum = close - close_20;
        double volatility = CalculateVolatility(pair, 20);
        
        double trend_confirm = (fastEMA[0] > slowEMA[0]) ? 1.0 : 0.0;
        double momentum_confirm = (momentum > 0) ? 1.0 : 0.0;
        
        double atr_avg = CalculateATRAverage(pair, 20);
        double volatility_confirm = (atr[0] > atr_avg) ? 1.0 : 0.0;
        
        double returns_std = CalculateReturnsStd(pair, 20);
        double sharpe_approx = CalculateSharpeApprox(pair, 20);
        double max_drawdown = CalculateMaxDrawdown(pair, 50);
        
        double htf_trend_dir = (htfFastEMA[0] > htfSlowEMA[0]) ? 1.0 : -1.0;
        double htf_trend_align = ((fastEMA[0] > slowEMA[0]) == (htfFastEMA[0] > htfSlowEMA[0])) ? 1.0 : 0.0;
        
        double bullish_sent = (close > bb_middle[0] && rsi[0] > 50) ? 1.0 : 0.0;
        double bearish_sent = (close < bb_middle[0] && rsi[0] < 50) ? 1.0 : 0.0;
        double net_sent = bullish_sent - bearish_sent;
        
        double correlations[8];
        double avg_corr = 0;
        for(int j = 0; j < 8; j++)
        {
            correlations[j] = (j == i) ? 1.0 : CalculateCorrelation(pair, g_pairs[j], 20);
            avg_corr += correlations[j];
        }
        avg_corr /= 8.0;
        
        double strengths[8];
        CalculateCurrencyStrengths(close_prices, strengths);
        
        double htf_confirm = (htf_trend_dir > 0) ? 1.0 : 0.0;
        double price_action_confirm = (close > bb_middle[0]) ? 1.0 : 0.0;
        double correlation_confirm = (avg_corr > 0.5) ? 1.0 : 0.0;
        double ema_confirm = (fastEMA[0] > slowEMA[0]) ? 1.0 : 0.0;
        double rsi_confirm = (rsi[0] > 50) ? 1.0 : 0.0;
        double volume_confirm_val = (volume > volume_sma) ? 1.0 : 0.0;
        double bb_confirm = (close > bb_middle[0]) ? 1.0 : 0.0;
        double stoch_confirm = (stoch_k[0] > stoch_d[0]) ? 1.0 : 0.0;

        string row = StringFormat("%s,%s,%.5f,%.5f,%.5f,%d,%.5f,%.5f,%.5f,%.5f,%.2f,%.5f,",
            timestamp, pair, close, high, low, volume, sma20[0], sma50[0],
            fastEMA[0], slowEMA[0], rsi[0], atr[0]);
        
        row += StringFormat("%.5f,%.5f,%.5f,%.2f,%.2f,%.2f,%.4f,%.2f,",
            bb_upper[0], bb_middle[0], bb_lower[0], stoch_k[0], stoch_d[0],
            volume_sma, volume_ratio, price_volume);
        
        row += StringFormat("%.5f,%.5f,%.2f,%.2f,%.2f,%.5f,%.4f,%.5f,",
            volatility, momentum, trend_confirm, momentum_confirm, volatility_confirm,
            returns_std, sharpe_approx, max_drawdown);
        
        row += StringFormat("%.5f,%.5f,%.2f,%.2f,", htfFastEMA[0], htfSlowEMA[0], htf_trend_dir, htf_trend_align);
        row += StringFormat("%.2f,%.2f,%.2f,", bullish_sent, bearish_sent, net_sent);
        
        for(int j = 0; j < 8; j++) row += StringFormat("%.4f,", correlations[j]);
        row += StringFormat("%.4f,", avg_corr);
        
        for(int j = 0; j < 8; j++) row += StringFormat("%.2f,", strengths[j]);
        
        row += StringFormat("%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f",
            htf_confirm, price_action_confirm, correlation_confirm,
            ema_confirm, rsi_confirm, volume_confirm_val, bb_confirm, stoch_confirm);
        
        FileWrite(handle, row);
    }
    
    FileClose(handle);
}
//+------------------------------------------------------------------+

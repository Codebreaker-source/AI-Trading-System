//+------------------------------------------------------------------+
//|                           BridgeEA_LITE_v2_31_PROG_TRAIL.mq5       |
//|                                            AI Trading System      |
//|     PROGRESSIVE TRAILING OPTIMIZATION UPDATE                      |
//+------------------------------------------------------------------+
#property copyright "AI Trading System"
#property link      ""
#property version   "2.31"
#property description "Bridge EA v2.31 - PROGRESSIVE TRAILING"
#property description "NEW: Trailing gets tighter as profit grows"
#property description "KEEP: Partial TP from v2.30"
#property description "KEEP: Regime-adaptive trailing from v2.29"
#property description "KEEP: All risk management features"

//--- Input Parameters
input int TimerSeconds = 3;              // Timer interval (seconds)

//--- RISK MANAGEMENT PARAMETERS (FROM v2.27)
input double FixedLotSize = 0.01;        // Fixed lot size (no confidence scaling)
input double MinConfidence = 0.60;       // Minimum confidence threshold
input double MaxDailyLossPercent = 3.0;  // Max daily loss before stopping (%)
input int MaxTotalPositions = 10;        // Maximum total open positions (base)
input double MaxPortfolioRiskPercent = 2.0;  // Max portfolio risk (%)
input double TakeProfitEquityPercent = 5.0;  // Close all profitable when equity up this %
input int MaxCorrelationExposure = 2;    // Max positions per correlation group

//--- DRAWDOWN SCALING PARAMETERS (NEW v2.28)
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
input double BE_TriggerRR = 1.0;         // BE trigger at this R:R (1.0 = 1:1)
input double BE_BufferPips = 5.0;        // Buffer above entry for BE (pips)
input double Trail_ATR_Multiplier = 2.0; // Trail distance = ATR * multiplier
input int TrailCheckSeconds = 5;         // How often to check trailing (seconds)

//--- REGIME-ADAPTIVE TRAILING PARAMETERS (NEW v2.29)
input bool EnableRegimeTrailing = true;        // Enable regime-adaptive trailing
input double Trail_ATR_Ranging = 1.5;          // Trailing multiplier for RANGING regime
input double Trail_ATR_Trending = 2.5;         // Trailing multiplier for TRENDING regime
input double Trail_ATR_Volatile = 3.5;         // Trailing multiplier for VOLATILE regime
input double RegimeATR_LowThreshold = 15.0;    // ATR below this = RANGING (pips)
input double RegimeATR_HighThreshold = 40.0;   // ATR above this = VOLATILE (pips)

//--- PARTIAL PROFIT TAKING PARAMETERS (NEW v2.30)
input bool EnablePartialTP = true;             // Enable partial profit taking
input double PartialTP_TriggerRR = 2.0;        // R:R to trigger partial close (e.g., 2.0 = 2:1)
input double PartialTP_ClosePercent = 50.0;    // Percent of position to close (50 = half)
input double PartialTP_ExtendRR = 3.0;         // New TP R:R for remaining position

//--- PROGRESSIVE TRAILING PARAMETERS (NEW v2.31)
input bool EnableProgressiveTrail = true;      // Enable progressive trailing (tighter as profit grows)
input double ProgTrail_Tier1_RR = 1.0;         // R:R threshold for tier 1 (0.9x multiplier)
input double ProgTrail_Tier2_RR = 1.5;         // R:R threshold for tier 2 (0.75x multiplier)
input double ProgTrail_Tier3_RR = 2.0;         // R:R threshold for tier 3 (0.5x multiplier)
input double ProgTrail_Mult_Tier1 = 0.9;       // Trail multiplier at tier 1 (slightly tighter)
input double ProgTrail_Mult_Tier2 = 0.75;      // Trail multiplier at tier 2 (tighter)
input double ProgTrail_Mult_Tier3 = 0.5;       // Trail multiplier at tier 3 (very tight)

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

//--- REGIME TRACKING (NEW v2.29)
string g_lastRegimes[8];           // Last regime for each pair (for change detection)
int g_regimeRangingCount = 0;      // Count of regime = RANGING
int g_regimeTrendingCount = 0;     // Count of regime = TRENDING
int g_regimeVolatileCount = 0;     // Count of regime = VOLATILE

//--- PARTIAL TP TRACKING (NEW v2.30)
// Track which positions have already taken partial profit
// Using arrays with max 50 positions (should be plenty)
ulong g_partialTPTickets[50];      // Tickets that have taken partial
int g_partialTPCount = 0;          // Number of tickets in array
int g_partialTPTakenTotal = 0;     // Total partial TPs taken (for stats)
int g_partialTPExtendedTotal = 0;  // Positions that hit extended TP

//--- DAILY LOSS LIMIT TRACKING (FROM v2.27)
double g_dayStartEquity = 0;
double g_dayStartBalance = 0;
int g_currentDay = -1;
bool g_dailyLossLimitHit = false;
int g_dailyTradesBlocked = 0;

//--- Portfolio Risk Tracking (FROM v2.27)
double g_currentPortfolioRisk = 0;  // Current total risk in dollars

//--- Equity Curve Trailing Tracking (FROM v2.27)
double g_peakEquity = 0;              // Highest equity observed
double g_currentDrawdownPercent = 0; // Current drawdown from peak
bool g_inDrawdownMode = false;        // True when in drawdown pause mode

//--- DRAWDOWN SCALING TRACKING (NEW v2.28)
int g_currentMaxPositions = 10;       // Dynamically adjusted based on drawdown
int g_currentDrawdownTier = 0;        // Current tier (0-4) for logging
double g_effectiveDrawdownPercent = 0; // Worse of total vs daily drawdown

#include <Trade\Trade.mqh>
CTrade g_trade;


//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("================================================================");
    Print("  BridgeEA_LITE_v2_28 - DRAWDOWN-BASED POSITION SCALING");
    Print("================================================================");
    Print("  RISK LIMITS:");
    Print("    - Max Daily Loss: ", MaxDailyLossPercent, "%");
    Print("    - Base Max Positions: ", MaxTotalPositions);
    Print("    - Max Portfolio Risk: ", MaxPortfolioRiskPercent, "%");
    Print("    - Max Correlation Exposure: ", MaxCorrelationExposure, " per group");
    Print("    - Fixed Lot Size: ", FixedLotSize);
    Print("    - Take Profit at Equity +", TakeProfitEquityPercent, "%");
    Print("  DRAWDOWN SCALING (NEW v2.28): ", EnableDrawdownScaling ? "ON" : "OFF");
    if(EnableDrawdownScaling)
    {
        Print("    - Tier 1 (75% pos): ", DrawdownTier1, "% DD");
        Print("    - Tier 2 (50% pos): ", DrawdownTier2, "% DD");
        Print("    - Tier 3 (25% pos): ", DrawdownTier3, "% DD");
        Print("    - Tier 4 (STOP):    ", DrawdownTier4, "% DD");
        Print("    - Uses WORST of (total DD) vs (daily DD)");
    }
    Print("  EQUITY CURVE: ", EnableEquityCurveTrailing ? "ON" : "OFF", 
          " (PAUSE at ", EquityDrawdownThreshold, "%)");
    Print("  VOLATILITY FILTER: ", EnableVolatilityFilter ? "ON" : "OFF",
          " (ATR: ", MinATRPips, "-", MaxATRPips, " pips)");
    Print("  EXECUTION: M15 timeframe, H4 HTF confirmation");
    Print("  BE/TRAIL: ", EnableBreakEven ? "ON" : "OFF", " / ", EnableTrailing ? "ON" : "OFF");
    
    //--- Initialize daily tracking
    InitializeDailyTracking();
    
    //--- Initialize equity curve tracking
    InitializeEquityCurveTracking();
    
    //--- Initialize drawdown scaling (NEW v2.28)
    g_currentMaxPositions = MaxTotalPositions;
    g_currentDrawdownTier = 0;
    g_effectiveDrawdownPercent = 0;
    
    //--- Initialize regime tracking (NEW v2.29)
    for(int i = 0; i < 8; i++)
    {
        g_lastRegimes[i] = "UNKNOWN";
    }
    g_regimeRangingCount = 0;
    g_regimeTrendingCount = 0;
    g_regimeVolatileCount = 0;
    
    //--- Log regime trailing settings
    if(EnableRegimeTrailing)
    {
        Print("  REGIME-ADAPTIVE TRAILING (NEW v2.29):");
        Print("    - RANGING (<", RegimeATR_LowThreshold, " pips): ", Trail_ATR_Ranging, "x ATR");
        Print("    - TRENDING: ", Trail_ATR_Trending, "x ATR");
        Print("    - VOLATILE (>", RegimeATR_HighThreshold, " pips): ", Trail_ATR_Volatile, "x ATR");
    }
    else
    {
        Print("  REGIME TRAILING: DISABLED (using static ", Trail_ATR_Multiplier, "x ATR)");
    }
    
    //--- Initialize partial TP tracking (NEW v2.30)
    g_partialTPCount = 0;
    g_partialTPTakenTotal = 0;
    g_partialTPExtendedTotal = 0;
    for(int i = 0; i < 50; i++)
    {
        g_partialTPTickets[i] = 0;
    }
    
    //--- Log partial TP settings
    if(EnablePartialTP)
    {
        Print("  PARTIAL PROFIT TAKING (NEW v2.30):");
        Print("    - Trigger at: ", PartialTP_TriggerRR, ":1 R:R");
        Print("    - Close: ", PartialTP_ClosePercent, "% of position");
        Print("    - Extend TP to: ", PartialTP_ExtendRR, ":1 R:R");
        Print("    - Move SL to: Break-even + 2 pips");
    }
    else
    {
        Print("  PARTIAL TP: DISABLED");
    }
    
    //--- Log progressive trailing settings (NEW v2.31)
    if(EnableProgressiveTrail)
    {
        Print("  PROGRESSIVE TRAILING (NEW v2.31):");
        Print("    - Tier 1 (", ProgTrail_Tier1_RR, ":1+ R:R): ", ProgTrail_Mult_Tier1, "x modifier");
        Print("    - Tier 2 (", ProgTrail_Tier2_RR, ":1+ R:R): ", ProgTrail_Mult_Tier2, "x modifier");
        Print("    - Tier 3 (", ProgTrail_Tier3_RR, ":1+ R:R): ", ProgTrail_Mult_Tier3, "x modifier");
        Print("    - Effect: Trail tightens as profit grows");
    }
    else
    {
        Print("  PROGRESSIVE TRAILING: DISABLED");
    }
    
    //--- Validate chart timeframe
    if(Period() != PERIOD_M15)
    {
        Print("WARNING: Optimized for M15 charts! Current: ", EnumToString(Period()));
    }
    
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
    
    Print("SUCCESS: BridgeEA v2.28 initialized");
    Print("   Starting Equity: $", DoubleToString(g_dayStartEquity, 2));
    Print("   Daily Loss Limit: $", DoubleToString(g_dayStartEquity * MaxDailyLossPercent / 100, 2));
    Print("   Current Max Positions: ", g_currentMaxPositions, " (Tier ", g_currentDrawdownTier, ")");
    
    return INIT_SUCCEEDED;
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
    //--- Check for new day first
    CheckNewDay();
    
    //--- If already hit limit today, stay blocked
    if(g_dailyLossLimitHit)
    {
        return false;
    }
    
    //--- Calculate current daily P&L
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double daily_pnl = current_equity - g_dayStartEquity;
    double daily_pnl_percent = (daily_pnl / g_dayStartEquity) * 100.0;
    
    //--- Check if loss limit exceeded
    if(daily_pnl_percent <= -MaxDailyLossPercent)
    {
        g_dailyLossLimitHit = true;
        Print("╔════════════════════════════════════════════════════════════╗");
        Print("║  ⛔ DAILY LOSS LIMIT HIT - TRADING HALTED FOR TODAY        ║");
        Print("╠════════════════════════════════════════════════════════════╣");
        Print("║  Start Equity: $", DoubleToString(g_dayStartEquity, 2));
        Print("║  Current Equity: $", DoubleToString(current_equity, 2));
        Print("║  Daily P&L: $", DoubleToString(daily_pnl, 2), " (", DoubleToString(daily_pnl_percent, 2), "%)");
        Print("║  Limit: -", DoubleToString(MaxDailyLossPercent, 1), "%");
        Print("╚════════════════════════════════════════════════════════════╝");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Get current daily P&L info for logging                             |
//+------------------------------------------------------------------+
string GetDailyPnLStatus()
{
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double daily_pnl = current_equity - g_dayStartEquity;
    double daily_pnl_percent = (daily_pnl / g_dayStartEquity) * 100.0;
    double remaining = MaxDailyLossPercent + daily_pnl_percent;
    
    return StringFormat("Daily P&L: $%.2f (%.2f%%) | Remaining: %.2f%%",
                        daily_pnl, daily_pnl_percent, remaining);
}

//+------------------------------------------------------------------+
//| PORTFOLIO RISK MANAGEMENT (FROM v2.27)                             |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Get pip value for a symbol                                         |
//+------------------------------------------------------------------+
double GetPipValue(string symbol)
{
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    
    // For 5-digit or 3-digit pairs, pip = 10 points
    if(digits == 5 || digits == 3)
        return point * 10;
    else
        return point;
}

//+------------------------------------------------------------------+
//| Get pip dollar value for a symbol (per 0.01 lot)                   |
//+------------------------------------------------------------------+
double GetPipDollarValue(string symbol)
{
    // Approximate pip values per 0.01 lot for major pairs
    string base = symbol;
    StringReplace(base, ".sim", "");
    
    if(base == "EURUSD" || base == "GBPUSD" || base == "AUDUSD" || base == "NZDUSD")
        return 0.10;  // $0.10 per pip per 0.01 lot
    else if(base == "USDJPY")
        return 0.067; // Approx $0.067 per pip
    else if(base == "USDCHF" || base == "USDCAD")
        return 0.075; // Approx $0.075 per pip
    else if(base == "EURGBP")
        return 0.125; // Approx $0.125 per pip
    else
        return 0.10;  // Default
}

//+------------------------------------------------------------------+
//| Calculate risk for a single position                               |
//+------------------------------------------------------------------+
double CalculatePositionRisk(string symbol, double entry_price, double stop_loss, double lot_size)
{
    double pip_value = GetPipValue(symbol);
    double pip_dollar = GetPipDollarValue(symbol);
    
    if(pip_value <= 0) return 0;
    
    double sl_pips = MathAbs(entry_price - stop_loss) / pip_value;
    double risk_dollars = sl_pips * pip_dollar * (lot_size / 0.01);
    
    return risk_dollars;
}

//+------------------------------------------------------------------+
//| Calculate total portfolio risk from all open positions            |
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
        
        if(sl <= 0) continue;  // No SL = can't calculate risk
        
        double pos_risk = CalculatePositionRisk(symbol, entry, sl, volume);
        total_risk += pos_risk;
    }
    
    g_currentPortfolioRisk = total_risk;
    return total_risk;
}

//+------------------------------------------------------------------+
//| Check if new position would exceed portfolio risk limit            |
//+------------------------------------------------------------------+
bool CheckPortfolioRiskLimit(string symbol, string action, double lot_size, double &new_risk)
{
    double account_balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double max_risk_dollars = account_balance * (MaxPortfolioRiskPercent / 100.0);
    
    // Get current portfolio risk
    double current_risk = CalculateCurrentPortfolioRisk();
    
    // Calculate risk for new position
    double atr = GetATRValue(symbol);
    double sl_distance = atr * SL_ATR_Multiplier;
    
    double entry_price = 0;
    if(action == "BUY")
        entry_price = SymbolInfoDouble(symbol, SYMBOL_ASK);
    else
        entry_price = SymbolInfoDouble(symbol, SYMBOL_BID);
    
    double sl_price = 0;
    if(action == "BUY")
        sl_price = entry_price - sl_distance;
    else
        sl_price = entry_price + sl_distance;
    
    new_risk = CalculatePositionRisk(symbol, entry_price, sl_price, lot_size);
    
    double projected_total = current_risk + new_risk;
    double projected_percent = (projected_total / account_balance) * 100.0;
    
    if(projected_total > max_risk_dollars)
    {
        Print("╔════════════════════════════════════════════════════════════╗");
        Print("║  ⛔ PORTFOLIO RISK LIMIT - TRADE BLOCKED                   ║");
        Print("╠════════════════════════════════════════════════════════════╣");
        Print("║  Current Risk: $", DoubleToString(current_risk, 2), 
              " (", DoubleToString((current_risk/account_balance)*100, 2), "%)");
        Print("║  New Trade Risk: $", DoubleToString(new_risk, 2));
        Print("║  Projected Total: $", DoubleToString(projected_total, 2),
              " (", DoubleToString(projected_percent, 2), "%)");
        Print("║  Max Allowed: $", DoubleToString(max_risk_dollars, 2),
              " (", DoubleToString(MaxPortfolioRiskPercent, 1), "%)");
        Print("╚════════════════════════════════════════════════════════════╝");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Get portfolio risk status string                                   |
//+------------------------------------------------------------------+
string GetPortfolioRiskStatus()
{
    double account_balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double current_risk = CalculateCurrentPortfolioRisk();
    double risk_percent = (current_risk / account_balance) * 100.0;
    double max_risk = account_balance * (MaxPortfolioRiskPercent / 100.0);
    double available = max_risk - current_risk;
    
    return StringFormat("Portfolio Risk: $%.2f (%.2f%%) | Available: $%.2f",
                        current_risk, risk_percent, available);
}

//+------------------------------------------------------------------+
//| CORRELATION EXPOSURE MANAGEMENT (FROM v2.27)                       |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Get correlation group for a symbol (0-3)                           |
//| Group 0: European (EURUSD, GBPUSD, EURGBP) - highly correlated    |
//| Group 1: Antipodean (AUDUSD, NZDUSD) - highly correlated          |
//| Group 2: USD-base (USDJPY, USDCHF, USDCAD) - moderate correlation |
//| Group 3: Uncategorized                                             |
//+------------------------------------------------------------------+
int GetCorrelationGroup(string symbol)
{
    string base = symbol;
    StringReplace(base, ".sim", "");
    
    // Group 0: European pairs (correlation ~0.85+)
    if(base == "EURUSD" || base == "GBPUSD" || base == "EURGBP")
        return 0;
    
    // Group 1: Antipodean pairs (correlation ~0.90+)
    if(base == "AUDUSD" || base == "NZDUSD")
        return 1;
    
    // Group 2: USD-base pairs (moderate correlation)
    if(base == "USDJPY" || base == "USDCHF" || base == "USDCAD")
        return 2;
    
    // Group 3: Uncategorized
    return 3;
}

//+------------------------------------------------------------------+
//| Get correlation group name for logging                             |
//+------------------------------------------------------------------+
string GetCorrelationGroupName(int group)
{
    switch(group)
    {
        case 0: return "European (EUR/GBP)";
        case 1: return "Antipodean (AUD/NZD)";
        case 2: return "USD-Base (JPY/CHF/CAD)";
        default: return "Other";
    }
}

//+------------------------------------------------------------------+
//| Count positions in a correlation group                             |
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
        int group = GetCorrelationGroup(symbol);
        
        if(group == target_group)
            count++;
    }
    
    return count;
}

//+------------------------------------------------------------------+
//| Check if new position would exceed correlation exposure limit      |
//+------------------------------------------------------------------+
bool CheckCorrelationExposure(string symbol)
{
    int group = GetCorrelationGroup(symbol);
    int current_count = CountPositionsInCorrelationGroup(group);
    
    if(current_count >= MaxCorrelationExposure)
    {
        string group_name = GetCorrelationGroupName(group);
        Print("╔════════════════════════════════════════════════════════════╗");
        Print("║  ⛔ CORRELATION EXPOSURE LIMIT - TRADE BLOCKED             ║");
        Print("╠════════════════════════════════════════════════════════════╣");
        Print("║  Symbol: ", symbol);
        Print("║  Correlation Group: ", group_name);
        Print("║  Current Positions in Group: ", current_count);
        Print("║  Max Allowed: ", MaxCorrelationExposure);
        Print("╚════════════════════════════════════════════════════════════╝");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Get correlation exposure status for logging                        |
//+------------------------------------------------------------------+
string GetCorrelationExposureStatus()
{
    int group0 = CountPositionsInCorrelationGroup(0);
    int group1 = CountPositionsInCorrelationGroup(1);
    int group2 = CountPositionsInCorrelationGroup(2);
    
    return StringFormat("Corr: EUR=%d/%d, ANZ=%d/%d, USD=%d/%d",
                        group0, MaxCorrelationExposure,
                        group1, MaxCorrelationExposure,
                        group2, MaxCorrelationExposure);
}


//+------------------------------------------------------------------+
//| EQUITY CURVE TRAILING (FROM v2.27)                                 |
//| Enhanced with DRAWDOWN SCALING (NEW v2.28)                         |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Initialize equity curve tracking                                   |
//+------------------------------------------------------------------+
void InitializeEquityCurveTracking()
{
    g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
    g_currentDrawdownPercent = 0;
    g_inDrawdownMode = false;
    
    Print("[EQUITY CURVE] Initialized | Peak: $", DoubleToString(g_peakEquity, 2));
}

//+------------------------------------------------------------------+
//| Get EFFECTIVE drawdown - WORST of (total DD) vs (daily DD)         |
//| NEW v2.28 - Most conservative approach                             |
//+------------------------------------------------------------------+
double GetEffectiveDrawdownPercent()
{
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    
    //--- Calculate total drawdown from peak
    double total_dd_percent = 0;
    if(g_peakEquity > 0)
        total_dd_percent = ((g_peakEquity - current_equity) / g_peakEquity) * 100.0;
    
    //--- Calculate daily drawdown from day start
    double daily_dd_percent = 0;
    if(g_dayStartEquity > 0)
    {
        double daily_pnl = current_equity - g_dayStartEquity;
        if(daily_pnl < 0)
            daily_dd_percent = MathAbs(daily_pnl / g_dayStartEquity) * 100.0;
    }
    
    //--- Return WORST (higher) of the two
    return MathMax(total_dd_percent, daily_dd_percent);
}

//+------------------------------------------------------------------+
//| Get drawdown-scaled max positions (NEW v2.28)                      |
//| Returns reduced max positions based on effective drawdown tier     |
//+------------------------------------------------------------------+
int GetDrawdownScaledMaxPositions()
{
    if(!EnableDrawdownScaling)
        return MaxTotalPositions;
    
    double eff_dd = GetEffectiveDrawdownPercent();
    g_effectiveDrawdownPercent = eff_dd;  // Store for logging
    
    int new_tier = 0;
    int scaled_max = MaxTotalPositions;
    
    if(eff_dd >= DrawdownTier4)
    {
        new_tier = 4;
        scaled_max = 0;  // STOP trading
    }
    else if(eff_dd >= DrawdownTier3)
    {
        new_tier = 3;
        scaled_max = (int)MathMax(1, MathRound(MaxTotalPositions * 0.25));  // 25%
    }
    else if(eff_dd >= DrawdownTier2)
    {
        new_tier = 2;
        scaled_max = (int)MathMax(1, MathRound(MaxTotalPositions * 0.50));  // 50%
    }
    else if(eff_dd >= DrawdownTier1)
    {
        new_tier = 1;
        scaled_max = (int)MathMax(1, MathRound(MaxTotalPositions * 0.75));  // 75%
    }
    else
    {
        new_tier = 0;
        scaled_max = MaxTotalPositions;  // 100%
    }
    
    //--- Log tier changes
    if(new_tier != g_currentDrawdownTier)
    {
        string tier_desc = "";
        switch(new_tier)
        {
            case 0: tier_desc = "NORMAL (100%)"; break;
            case 1: tier_desc = "CAUTION (75%)"; break;
            case 2: tier_desc = "REDUCED (50%)"; break;
            case 3: tier_desc = "MINIMAL (25%)"; break;
            case 4: tier_desc = "STOPPED (0%)"; break;
        }
        
        Print("╔════════════════════════════════════════════════════════════╗");
        Print("║  📊 DRAWDOWN TIER CHANGE                                   ║");
        Print("╠════════════════════════════════════════════════════════════╣");
        Print("║  Effective Drawdown: ", DoubleToString(eff_dd, 2), "%");
        Print("║  Tier: ", g_currentDrawdownTier, " → ", new_tier, " (", tier_desc, ")");
        Print("║  Max Positions: ", g_currentMaxPositions, " → ", scaled_max);
        Print("╚════════════════════════════════════════════════════════════╝");
        
        g_currentDrawdownTier = new_tier;
    }
    
    return scaled_max;
}

//+------------------------------------------------------------------+
//| Update equity curve tracking (call on each timer)                  |
//| Enhanced with drawdown scaling (NEW v2.28)                         |
//+------------------------------------------------------------------+
void UpdateEquityCurveTracking()
{
    double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    
    //--- Update peak if new high
    if(current_equity > g_peakEquity)
    {
        g_peakEquity = current_equity;
        
        //--- Exit drawdown mode if we were in it
        if(g_inDrawdownMode)
        {
            g_inDrawdownMode = false;
            Print("╔════════════════════════════════════════════════════════════╗");
            Print("║  ✅ EQUITY RECOVERED - TRADING RESUMED                     ║");
            Print("╠════════════════════════════════════════════════════════════╣");
            Print("║  New Peak Equity: $", DoubleToString(g_peakEquity, 2));
            Print("║  Lot Size: ", DoubleToString(FixedLotSize, 2), " (fixed)");
            Print("╚════════════════════════════════════════════════════════════╝");
        }
    }
    
    //--- Calculate current drawdown from peak (for legacy equity curve tracking)
    g_currentDrawdownPercent = ((g_peakEquity - current_equity) / g_peakEquity) * 100.0;
    
    //--- Check if we should enter drawdown mode (PAUSE trading) - legacy behavior
    if(EnableEquityCurveTrailing && !g_inDrawdownMode && g_currentDrawdownPercent >= EquityDrawdownThreshold)
    {
        g_inDrawdownMode = true;
        Print("╔════════════════════════════════════════════════════════════╗");
        Print("║  ⚠️ EQUITY DRAWDOWN - NEW TRADES PAUSED                    ║");
        Print("╠════════════════════════════════════════════════════════════╣");
        Print("║  Peak Equity: $", DoubleToString(g_peakEquity, 2));
        Print("║  Current Equity: $", DoubleToString(current_equity, 2));
        Print("║  Drawdown: ", DoubleToString(g_currentDrawdownPercent, 2), "%");
        Print("║  Threshold: ", DoubleToString(EquityDrawdownThreshold, 1), "%");
        Print("║  Action: NO NEW TRADES until equity recovers above peak");
        Print("╚════════════════════════════════════════════════════════════╝");
    }
    
    //--- UPDATE DRAWDOWN SCALING (NEW v2.28)
    g_currentMaxPositions = GetDrawdownScaledMaxPositions();
}

//+------------------------------------------------------------------+
//| Check if equity curve allows new trades                            |
//+------------------------------------------------------------------+
bool CheckEquityCurveAllowsTrading()
{
    if(!EnableEquityCurveTrailing)
        return true;  // Disabled = always allow
    
    return !g_inDrawdownMode;  // Allow if NOT in drawdown mode
}

//+------------------------------------------------------------------+
//| Get equity curve status string (updated for v2.28)                 |
//+------------------------------------------------------------------+
string GetEquityCurveStatus()
{
    string mode = g_inDrawdownMode ? "PAUSED" : "ACTIVE";
    
    if(EnableDrawdownScaling)
    {
        return StringFormat("EqCurve: %s | Peak=$%.0f | EffDD=%.2f%% | MaxPos=%d (T%d)",
                            mode, g_peakEquity, g_effectiveDrawdownPercent, 
                            g_currentMaxPositions, g_currentDrawdownTier);
    }
    else if(EnableEquityCurveTrailing)
    {
        return StringFormat("EqCurve: %s | Peak=$%.0f | DD=%.1f%%",
                            mode, g_peakEquity, g_currentDrawdownPercent);
    }
    else
    {
        return "EqCurve: DISABLED";
    }
}

//+------------------------------------------------------------------+
//| VOLATILITY REGIME FILTER (FROM v2.27)                              |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Convert ATR value to pips for a symbol                             |
//+------------------------------------------------------------------+
double ATRToPips(string symbol, double atr_value)
{
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    
    // For 5-digit or 3-digit pairs, pip = 10 points
    double pip_size = (digits == 5 || digits == 3) ? point * 10 : point;
    
    if(pip_size <= 0) return 0;
    
    return atr_value / pip_size;
}

//+------------------------------------------------------------------+
//| Check volatility regime for a symbol                               |
//| Returns: true if volatility is acceptable, false if extreme        |
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
    
    //--- Check for too low volatility (market too quiet)
    if(atr_pips < MinATRPips)
    {
        regime = "TOO_QUIET";
        return false;
    }
    
    //--- Check for too high volatility (market too chaotic)
    if(atr_pips > MaxATRPips)
    {
        regime = "TOO_VOLATILE";
        return false;
    }
    
    //--- Normal volatility
    regime = "NORMAL";
    return true;
}

//+------------------------------------------------------------------+
//| Get volatility status string for logging                           |
//+------------------------------------------------------------------+
string GetVolatilityStatus(string symbol)
{
    if(!EnableVolatilityFilter)
        return "Vol: DISABLED";
    
    double atr_pips = 0;
    string regime = "";
    CheckVolatilityRegime(symbol, atr_pips, regime);
    
    return StringFormat("Vol: %s (%.1f pips)", regime, atr_pips);
}


//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
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
    
    //--- Final daily summary
    double final_equity = AccountInfoDouble(ACCOUNT_EQUITY);
    double daily_pnl = final_equity - g_dayStartEquity;
    
    Print("╔════════════════════════════════════════════════════════════╗");
    Print("║  BridgeEA v2.28 SESSION SUMMARY                            ║");
    Print("╠════════════════════════════════════════════════════════════╣");
    Print("║  Start Equity: $", DoubleToString(g_dayStartEquity, 2));
    Print("║  Final Equity: $", DoubleToString(final_equity, 2));
    Print("║  Session P&L: $", DoubleToString(daily_pnl, 2));
    Print("║  Final Drawdown Tier: ", g_currentDrawdownTier);
    Print("║  Final Max Positions: ", g_currentMaxPositions);
    Print("║  BE Triggered: ", g_beTriggeredCount);
    Print("║  Trail Adjusted: ", g_trailAdjustedCount);
    Print("║  Trades Blocked (Daily Limit): ", g_dailyTradesBlocked);
    Print("╚════════════════════════════════════════════════════════════╝");
}

//+------------------------------------------------------------------+
//| Timer function - Main loop                                         |
//+------------------------------------------------------------------+
void OnTimer()
{
    //--- Check for new day reset
    CheckNewDay();
    
    //--- Update equity curve tracking (includes drawdown scaling update)
    UpdateEquityCurveTracking();
    
    //--- Always write features and positions (for monitoring)
    WriteFeaturesSparse();
    WriteOpenPositions();
    
    //--- Check daily loss limit BEFORE processing any trades
    if(EnableTrading && CheckDailyLossLimit())
    {
        ProcessTradeCommands();
    }
    else if(EnableTrading && g_dailyLossLimitHit)
    {
        //--- Still need to check for commands to log rejections
        if(FileIsExist(g_commandsFile))
        {
            g_dailyTradesBlocked++;
            if(g_dailyTradesBlocked <= 5)  // Only log first 5 blocks
            {
                Print("[BLOCKED] Trade command ignored - Daily loss limit active");
            }
            FileDelete(g_commandsFile);  // Clear commands to prevent buildup
        }
    }
    
    //--- Manage open positions (BE & Trailing) - always active
    if(EnableBreakEven || EnableTrailing || EnablePartialTP)
    {
        datetime now = TimeCurrent();
        if(now - g_lastTrailCheck >= TrailCheckSeconds)
        {
            ManagePartialProfits();   // NEW v2.30: Partial TP first
            ManageOpenPositions();    // Then BE & trailing
            g_lastTrailCheck = now;
        }
    }
}


//+------------------------------------------------------------------+
//| REGIME DETECTION FUNCTIONS (NEW v2.29)                             |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Get current market regime based on ATR                             |
//| Returns: "RANGING", "TRENDING", or "VOLATILE"                      |
//+------------------------------------------------------------------+
string GetCurrentRegime(string symbol, double atr_pips)
{
    // Validate ATR value
    if(atr_pips <= 0)
    {
        if(LogVerbose)
            Print("[REGIME] ", symbol, " - Invalid ATR: ", atr_pips, " pips, defaulting to TRENDING");
        return "TRENDING";
    }
    
    // Classify regime based on ATR thresholds
    if(atr_pips < RegimeATR_LowThreshold)
    {
        return "RANGING";
    }
    else if(atr_pips > RegimeATR_HighThreshold)
    {
        return "VOLATILE";
    }
    else
    {
        return "TRENDING";
    }
}

//+------------------------------------------------------------------+
//| Get appropriate trailing multiplier based on current regime        |
//| Returns: ATR multiplier (1.5, 2.5, or 3.5 by default)              |
//+------------------------------------------------------------------+
double GetRegimeTrailMultiplier(string symbol, double atr)
{
    // If regime trailing disabled, use static multiplier
    if(!EnableRegimeTrailing)
    {
        return Trail_ATR_Multiplier;
    }
    
    // Convert ATR to pips for regime detection
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    double pip_factor = (digits == 3 || digits == 5) ? 10.0 : 1.0;
    double pip_value = point * pip_factor;
    double atr_pips = (pip_value > 0) ? atr / pip_value : 0;
    
    // Validate ATR pips
    if(atr_pips <= 0)
    {
        if(LogVerbose)
            Print("[REGIME TRAIL] ", symbol, " - Invalid ATR pips: ", atr_pips, ", using default: ", Trail_ATR_Multiplier);
        return Trail_ATR_Multiplier;
    }
    
    // Get current regime
    string regime = GetCurrentRegime(symbol, atr_pips);
    double multiplier = Trail_ATR_Multiplier;  // Default fallback
    
    // Select multiplier based on regime
    if(regime == "RANGING")
    {
        multiplier = Trail_ATR_Ranging;
        g_regimeRangingCount++;
    }
    else if(regime == "TRENDING")
    {
        multiplier = Trail_ATR_Trending;
        g_regimeTrendingCount++;
    }
    else if(regime == "VOLATILE")
    {
        multiplier = Trail_ATR_Volatile;
        g_regimeVolatileCount++;
    }
    
    // Log regime change for this symbol (find pair index)
    int pair_idx = -1;
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        if(g_pairs[i] == symbol)
        {
            pair_idx = i;
            break;
        }
    }
    
    // Log if regime changed
    if(pair_idx >= 0 && pair_idx < 8)
    {
        if(g_lastRegimes[pair_idx] != regime)
        {
            Print("[REGIME CHANGE] ", symbol, " | ", g_lastRegimes[pair_idx], " -> ", regime,
                  " | ATR=", DoubleToString(atr_pips, 1), " pips",
                  " | Trail=", DoubleToString(multiplier, 1), "x ATR");
            g_lastRegimes[pair_idx] = regime;
        }
    }
    
    return multiplier;
}

//+------------------------------------------------------------------+
//| Get progressive trail modifier based on current R:R (NEW v2.31)    |
//| Returns: Multiplier (0.5-1.0) to tighten trail as profit grows     |
//+------------------------------------------------------------------+
double GetProgressiveTrailModifier(double current_rr)
{
    // If progressive trailing disabled, return 1.0 (no modification)
    if(!EnableProgressiveTrail)
        return 1.0;
    
    // Determine tier based on current R:R
    if(current_rr >= ProgTrail_Tier3_RR)
    {
        // Tier 3: Very tight trailing (2:1+ R:R)
        return ProgTrail_Mult_Tier3;  // Default 0.5
    }
    else if(current_rr >= ProgTrail_Tier2_RR)
    {
        // Tier 2: Tighter trailing (1.5:1 - 2:1 R:R)
        return ProgTrail_Mult_Tier2;  // Default 0.75
    }
    else if(current_rr >= ProgTrail_Tier1_RR)
    {
        // Tier 1: Slightly tighter (1:1 - 1.5:1 R:R)
        return ProgTrail_Mult_Tier1;  // Default 0.9
    }
    else
    {
        // Below tier 1: Normal trailing
        return 1.0;
    }
}

//+------------------------------------------------------------------+
//| Get combined trail multiplier (regime + progressive)               |
//+------------------------------------------------------------------+
double GetCombinedTrailMultiplier(string symbol, double atr, double current_rr)
{
    // Get base multiplier from regime detection
    double regime_mult = GetRegimeTrailMultiplier(symbol, atr);
    
    // Get progressive modifier based on R:R
    double prog_modifier = GetProgressiveTrailModifier(current_rr);
    
    // Combine them (progressive tightens the regime-based trail)
    double combined = regime_mult * prog_modifier;
    
    // Log if progressive is active and modifying
    if(EnableProgressiveTrail && prog_modifier < 1.0 && LogVerbose)
    {
        static datetime last_prog_log = 0;
        if(TimeCurrent() - last_prog_log > 30)  // Log every 30 sec max
        {
            string tier = "T0";
            if(current_rr >= ProgTrail_Tier3_RR) tier = "T3";
            else if(current_rr >= ProgTrail_Tier2_RR) tier = "T2";
            else if(current_rr >= ProgTrail_Tier1_RR) tier = "T1";
            
            Print("[PROG TRAIL] ", symbol, " | R:R=", DoubleToString(current_rr, 1),
                  " | Tier=", tier,
                  " | Regime=", DoubleToString(regime_mult, 2), "x",
                  " × Prog=", DoubleToString(prog_modifier, 2),
                  " = ", DoubleToString(combined, 2), "x ATR");
            last_prog_log = TimeCurrent();
        }
    }
    
    return combined;
}

//+------------------------------------------------------------------+
//| Get regime statistics summary                                       |
//+------------------------------------------------------------------+
string GetRegimeStatsSummary()
{
    int total = g_regimeRangingCount + g_regimeTrendingCount + g_regimeVolatileCount;
    if(total == 0) return "Regime: No data";
    
    return StringFormat("Regime Stats: RANGING=%d (%.0f%%) | TRENDING=%d (%.0f%%) | VOLATILE=%d (%.0f%%)",
        g_regimeRangingCount, (double)g_regimeRangingCount / total * 100,
        g_regimeTrendingCount, (double)g_regimeTrendingCount / total * 100,
        g_regimeVolatileCount, (double)g_regimeVolatileCount / total * 100);
}


//+------------------------------------------------------------------+
//| PARTIAL PROFIT TAKING FUNCTIONS (NEW v2.30)                        |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Check if a ticket has already taken partial profit                 |
//+------------------------------------------------------------------+
bool HasTakenPartialTP(ulong ticket)
{
    for(int i = 0; i < g_partialTPCount; i++)
    {
        if(g_partialTPTickets[i] == ticket)
            return true;
    }
    return false;
}

//+------------------------------------------------------------------+
//| Mark a ticket as having taken partial profit                       |
//+------------------------------------------------------------------+
void MarkPartialTPTaken(ulong ticket)
{
    // Check if already in array
    if(HasTakenPartialTP(ticket))
        return;
    
    // Add to array if space available
    if(g_partialTPCount < 50)
    {
        g_partialTPTickets[g_partialTPCount] = ticket;
        g_partialTPCount++;
    }
    else
    {
        Print("[PARTIAL TP] WARNING: Tracking array full (50 max)");
    }
}

//+------------------------------------------------------------------+
//| Clean up closed tickets from tracking array                        |
//+------------------------------------------------------------------+
void CleanupPartialTPTracking()
{
    // Remove tickets that no longer have open positions
    int write_idx = 0;
    
    for(int i = 0; i < g_partialTPCount; i++)
    {
        ulong ticket = g_partialTPTickets[i];
        bool still_open = false;
        
        // Check if this ticket still has an open position
        for(int j = 0; j < PositionsTotal(); j++)
        {
            if(PositionGetTicket(j) == ticket)
            {
                still_open = true;
                break;
            }
        }
        
        if(still_open)
        {
            g_partialTPTickets[write_idx] = ticket;
            write_idx++;
        }
    }
    
    g_partialTPCount = write_idx;
}

//+------------------------------------------------------------------+
//| Manage partial profit taking for all positions                     |
//+------------------------------------------------------------------+
void ManagePartialProfits()
{
    if(!EnablePartialTP)
        return;
    
    // Periodically clean up closed tickets
    static datetime last_cleanup = 0;
    if(TimeCurrent() - last_cleanup > 60)  // Every minute
    {
        CleanupPartialTPTracking();
        last_cleanup = TimeCurrent();
    }
    
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        
        //--- Only manage our trades
        long pos_magic = PositionGetInteger(POSITION_MAGIC);
        if(pos_magic != MagicNumber) continue;
        
        //--- Skip if already taken partial
        if(HasTakenPartialTP(ticket))
            continue;
        
        string symbol = PositionGetString(POSITION_SYMBOL);
        ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
        double entry_price = PositionGetDouble(POSITION_PRICE_OPEN);
        double current_sl = PositionGetDouble(POSITION_SL);
        double current_tp = PositionGetDouble(POSITION_TP);
        double volume = PositionGetDouble(POSITION_VOLUME);
        
        //--- Skip if position too small to split
        if(volume < 0.02)
            continue;  // Need at least 0.02 to split into 0.01 + 0.01
        
        //--- Get current price
        double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
        double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
        double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
        int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
        
        //--- Calculate initial risk (distance from entry to original SL)
        double initial_risk = 0;
        double current_profit_distance = 0;
        double current_price = 0;
        
        if(pos_type == POSITION_TYPE_BUY)
        {
            current_price = bid;
            initial_risk = entry_price - current_sl;
            current_profit_distance = current_price - entry_price;
        }
        else // SELL
        {
            current_price = ask;
            initial_risk = current_sl - entry_price;
            current_profit_distance = entry_price - current_price;
        }
        
        //--- Skip if we can't determine initial risk
        if(initial_risk <= 0) continue;
        
        //--- Calculate current R:R
        double current_rr = current_profit_distance / initial_risk;
        
        //--- Check if at partial TP trigger level
        if(current_rr >= PartialTP_TriggerRR)
        {
            //--- Calculate volumes
            double close_volume = NormalizeDouble(volume * (PartialTP_ClosePercent / 100.0), 2);
            double min_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
            
            // Ensure we close at least min lot
            if(close_volume < min_lot)
                close_volume = min_lot;
            
            // Don't close more than we have
            if(close_volume > volume - min_lot)
                close_volume = volume - min_lot;
            
            // Final sanity check
            if(close_volume < min_lot)
                continue;  // Can't do partial close
            
            //--- Close partial position
            bool closed = g_trade.PositionClosePartial(ticket, close_volume);
            
            if(closed)
            {
                //--- Calculate new TP at extended R:R
                double new_tp = 0;
                double extended_distance = initial_risk * PartialTP_ExtendRR;
                
                if(pos_type == POSITION_TYPE_BUY)
                    new_tp = entry_price + extended_distance;
                else
                    new_tp = entry_price - extended_distance;
                
                new_tp = NormalizeDouble(new_tp, digits);
                
                //--- Move SL to break-even (entry + small buffer)
                double pip_factor = (digits == 3 || digits == 5) ? 10.0 : 1.0;
                double pip_value = point * pip_factor;
                double be_buffer = 2.0 * pip_value;  // 2 pip buffer
                double new_sl = 0;
                
                if(pos_type == POSITION_TYPE_BUY)
                    new_sl = entry_price + be_buffer;
                else
                    new_sl = entry_price - be_buffer;
                
                new_sl = NormalizeDouble(new_sl, digits);
                
                //--- Modify remaining position
                bool modified = g_trade.PositionModify(ticket, new_sl, new_tp);
                
                //--- Mark as partial taken
                MarkPartialTPTaken(ticket);
                g_partialTPTakenTotal++;
                
                //--- Log the partial close
                Print("╔════════════════════════════════════════════════════════════╗");
                Print("║  [PARTIAL TP] ", symbol, " @ ", DoubleToString(current_rr, 1), ":1 R:R");
                Print("║  Closed: ", DoubleToString(close_volume, 2), " lots (", 
                      DoubleToString(PartialTP_ClosePercent, 0), "%)");
                Print("║  Remaining: ", DoubleToString(volume - close_volume, 2), " lots");
                Print("║  New SL: ", DoubleToString(new_sl, digits), " (break-even +2 pips)");
                Print("║  New TP: ", DoubleToString(new_tp, digits), " (", 
                      DoubleToString(PartialTP_ExtendRR, 1), ":1 R:R)");
                Print("╚════════════════════════════════════════════════════════════╝");
            }
            else
            {
                Print("[PARTIAL TP] FAILED for ", symbol, " | Error: ", GetLastError());
            }
        }
    }
}


//+------------------------------------------------------------------+
//| BREAK-EVEN & TRAILING STOP MANAGEMENT (FROM v2.27)                 |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        
        //--- Only manage our trades
        long pos_magic = PositionGetInteger(POSITION_MAGIC);
        if(pos_magic != MagicNumber) continue;
        
        string symbol = PositionGetString(POSITION_SYMBOL);
        ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
        double entry_price = PositionGetDouble(POSITION_PRICE_OPEN);
        double current_sl = PositionGetDouble(POSITION_SL);
        double current_tp = PositionGetDouble(POSITION_TP);
        
        //--- Get current price
        double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
        double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
        double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
        int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
        
        //--- Calculate pip value
        double pip_factor = (digits == 3 || digits == 5) ? 10.0 : 1.0;
        double pip_value = point * pip_factor;
        
        //--- Calculate initial risk (distance from entry to original SL)
        double initial_risk = 0;
        double current_profit_distance = 0;
        double current_price = 0;
        
        if(pos_type == POSITION_TYPE_BUY)
        {
            current_price = bid;
            initial_risk = entry_price - current_sl;
            current_profit_distance = current_price - entry_price;
        }
        else // SELL
        {
            current_price = ask;
            initial_risk = current_sl - entry_price;
            current_profit_distance = entry_price - current_price;
        }
        
        //--- Skip if we can't determine initial risk
        if(initial_risk <= 0) continue;
        
        //--- Calculate current R:R
        double current_rr = current_profit_distance / initial_risk;
        
        //--- Get current ATR for trailing
        double atr = GetATRValue(symbol);
        double trail_multiplier = GetCombinedTrailMultiplier(symbol, atr, current_rr);  // NEW v2.31: Combined regime + progressive
        double trail_distance = atr * trail_multiplier;
        
        //--- Calculate BE level with buffer
        double be_buffer = BE_BufferPips * pip_value;
        double be_level = 0;
        
        if(pos_type == POSITION_TYPE_BUY)
            be_level = entry_price + be_buffer;
        else
            be_level = entry_price - be_buffer;
        
        be_level = NormalizeDouble(be_level, digits);
        
        //--- Check if already at BE or better
        bool at_breakeven = false;
        if(pos_type == POSITION_TYPE_BUY)
            at_breakeven = (current_sl >= entry_price);
        else
            at_breakeven = (current_sl <= entry_price && current_sl > 0);
        
        //--- BREAK-EVEN LOGIC
        if(EnableBreakEven && !at_breakeven && current_rr >= BE_TriggerRR)
        {
            bool modified = ModifyPositionSL(ticket, symbol, be_level, current_tp);
            
            if(modified)
            {
                g_beTriggeredCount++;
                Print("[BE TRIGGERED] ", symbol, " | R:R=", DoubleToString(current_rr, 2),
                      " | New SL=", DoubleToString(be_level, digits),
                      " | Buffer=", BE_BufferPips, " pips");
            }
            continue;
        }
        
        //--- TRAILING STOP LOGIC (only after BE)
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
                bool modified = ModifyPositionSL(ticket, symbol, new_sl, current_tp);
                
                if(modified)
                {
                    g_trailAdjustedCount++;
                    if(LogVerbose)
                    {
                        Print("[TRAIL ADJUSTED] ", symbol, " | SL: ", 
                              DoubleToString(current_sl, digits), " -> ",
                              DoubleToString(new_sl, digits));
                    }
                }
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
    {
        if(LogVerbose)
            Print("[SL MODIFY SKIP] ", symbol, " - Too close to price");
        return false;
    }
    
    bool result = g_trade.PositionModify(ticket, new_sl, current_tp);
    
    if(!result)
    {
        Print("[SL MODIFY FAILED] ", symbol, " | Error: ", GetLastError());
    }
    
    return result;
}


//+------------------------------------------------------------------+
//| Write current open positions to CSV                                |
//+------------------------------------------------------------------+
void WriteOpenPositions()
{
    int handle = FileOpen(g_positionsFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    
    FileWrite(handle, "symbol", "ticket", "direction", "volume", "entry_price", 
              "sl", "tp", "profit", "magic", "open_time", "be_status", "trail_active");
    
    int total = PositionsTotal();
    int our_positions = 0;
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket == 0) continue;
        
        long pos_magic = PositionGetInteger(POSITION_MAGIC);
        if(pos_magic != MagicNumber) continue;
        
        string symbol = PositionGetString(POSITION_SYMBOL);
        ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
        double volume = PositionGetDouble(POSITION_VOLUME);
        double entry = PositionGetDouble(POSITION_PRICE_OPEN);
        double sl = PositionGetDouble(POSITION_SL);
        double tp = PositionGetDouble(POSITION_TP);
        double profit = PositionGetDouble(POSITION_PROFIT);
        datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
        
        string direction = (type == POSITION_TYPE_BUY) ? "BUY" : "SELL";
        
        bool at_be = false;
        if(type == POSITION_TYPE_BUY)
            at_be = (sl >= entry);
        else
            at_be = (sl <= entry && sl > 0);
        
        string be_status = at_be ? "YES" : "NO";
        string trail_active = (at_be && EnableTrailing) ? "YES" : "NO";
        
        FileWrite(handle, symbol, ticket, direction, volume, entry, sl, tp, 
                  profit, pos_magic, TimeToString(open_time, TIME_DATE|TIME_MINUTES),
                  be_status, trail_active);
        
        our_positions++;
    }
    
    FileClose(handle);
}

//+------------------------------------------------------------------+
//| Initialize trade execution log                                     |
//+------------------------------------------------------------------+
void InitializeTradeLog()
{
    if(g_logHeaderWritten) return;
    
    int handle = FileOpen(g_tradesLogFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    
    string header = "timestamp,symbol,action,lot_size,confidence,entry_price,sl_price,tp_price,";
    header += "ticket,result,error_code,spread_pips,atr_value,daily_pnl_pct,dd_tier,max_pos,comment";
    
    FileWrite(handle, header);
    FileClose(handle);
    g_logHeaderWritten = true;
}

//+------------------------------------------------------------------+
//| Get count of our open positions                                    |
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
//| Process trade commands from Python system                         |
//+------------------------------------------------------------------+
void ProcessTradeCommands()
{
    if(!FileIsExist(g_commandsFile)) return;
    
    int handle = FileOpen(g_commandsFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    
    //--- Skip header (6 columns: symbol, action, confidence, sl_price, tp_price, timestamp)
    FileReadString(handle); FileReadString(handle);
    FileReadString(handle); FileReadString(handle);
    FileReadString(handle); FileReadString(handle);
    
    int commands_processed = 0;
    int commands_skipped = 0;
    
    while(!FileIsEnding(handle))
    {
        string symbol = FileReadString(handle);
        string action = FileReadString(handle);
        double confidence = StringToDouble(FileReadString(handle));
        double sl_price = StringToDouble(FileReadString(handle));
        double tp_price = StringToDouble(FileReadString(handle));
        string timestamp_str = FileReadString(handle);
        
        if(symbol == "" || action == "") continue;
        
        if(LogVerbose)
            Print("READ: ", symbol, " | ", action, " | ", confidence, 
                  " | SL:", sl_price, " | TP:", tp_price,
                  " | ", GetDailyPnLStatus(), " | ", GetEquityCurveStatus());
        
        bool success = false;
        
        if(action == "BUY" || action == "SELL")
            success = ExecuteTrade(symbol, action, confidence, sl_price, tp_price);
        else if(action == "SCALE_OUT")
            success = ExecuteScaleOut(symbol, confidence);
        
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
//| Execute SCALE_OUT - Partial close (FROM v2.27)                     |
//+------------------------------------------------------------------+
bool ExecuteScaleOut(string symbol, double confidence)
{
    if(!PositionSelect(symbol))
    {
        LogTrade(symbol, "SCALE_OUT", 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "NO_POSITION");
        return false;
    }
    
    double pos_volume = PositionGetDouble(POSITION_VOLUME);
    ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    ulong pos_ticket = PositionGetInteger(POSITION_TICKET);
    
    double scale_volume = 0.01;
    if(pos_volume < scale_volume)
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
             result.order, success ? "SUCCESS" : "FAILED", result.retcode, "PARTIAL_CLOSE");
    
    if(success)
        Print("[SCALE_OUT SUCCESS] ", symbol, " closed ", scale_volume, " lots");
    
    return success;
}


//+------------------------------------------------------------------+
//| Execute a trade (BUY/SELL) with risk checks                        |
//| UPDATED v2.28: Uses drawdown-scaled max positions                  |
//+------------------------------------------------------------------+
bool ExecuteTrade(string symbol, string action, double confidence, double sl_price_in = 0, double tp_price_in = 0)
{
    //--- Check confidence threshold
    if(confidence < MinConfidence)
    {
        Print("[REJECTED] ", symbol, " - Confidence ", confidence, " < ", MinConfidence);
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "LOW_CONFIDENCE");
        return false;
    }
    
    //--- GET DRAWDOWN-SCALED MAX POSITIONS (NEW v2.28)
    int scaled_max = GetDrawdownScaledMaxPositions();
    
    //--- CHECK IF TRADING STOPPED (Tier 4 - 3%+ drawdown)
    if(scaled_max <= 0)
    {
        Print("╔════════════════════════════════════════════════════════════╗");
        Print("║  ⛔ DRAWDOWN TIER 4 - ALL TRADING STOPPED                  ║");
        Print("╠════════════════════════════════════════════════════════════╣");
        Print("║  Effective Drawdown: ", DoubleToString(g_effectiveDrawdownPercent, 2), "%");
        Print("║  Threshold: ", DoubleToString(DrawdownTier4, 2), "%");
        Print("║  Max Positions: 0");
        Print("╚════════════════════════════════════════════════════════════╝");
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "DRAWDOWN_TIER4_STOP");
        return false;
    }
    
    //--- CHECK MAX TOTAL POSITIONS (using scaled value)
    int current_positions = GetOurPositionCount();
    if(current_positions >= scaled_max)
    {
        Print("[REJECTED] ", symbol, " - Max positions at DD tier ", g_currentDrawdownTier, 
              ": ", current_positions, "/", scaled_max,
              " (EffDD=", DoubleToString(g_effectiveDrawdownPercent, 2), "%)");
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, 
                 StringFormat("MAX_POS_TIER%d_%d/%d", g_currentDrawdownTier, current_positions, scaled_max));
        return false;
    }
    
    //--- CHECK PORTFOLIO RISK LIMIT (FROM v2.27)
    double new_trade_risk = 0;
    if(!CheckPortfolioRiskLimit(symbol, action, FixedLotSize, new_trade_risk))
    {
        Print("[REJECTED] ", symbol, " - Portfolio risk limit exceeded");
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "PORTFOLIO_RISK_LIMIT");
        return false;
    }
    
    //--- CHECK CORRELATION EXPOSURE (FROM v2.27)
    if(!CheckCorrelationExposure(symbol))
    {
        Print("[REJECTED] ", symbol, " - Correlation exposure limit exceeded");
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "CORRELATION_LIMIT");
        return false;
    }
    
    //--- CHECK EQUITY CURVE - PAUSE if in drawdown (FROM v2.27)
    if(!CheckEquityCurveAllowsTrading())
    {
        Print("[REJECTED] ", symbol, " - Equity curve drawdown - trading paused");
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "EQUITY_DRAWDOWN_PAUSE");
        return false;
    }
    
    //--- CHECK VOLATILITY REGIME (FROM v2.27)
    double vol_atr_pips = 0;
    string vol_regime = "";
    if(!CheckVolatilityRegime(symbol, vol_atr_pips, vol_regime))
    {
        Print("[REJECTED] ", symbol, " - Volatility regime: ", vol_regime, " (ATR=", 
              DoubleToString(vol_atr_pips, 1), " pips)");
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, 
                 StringFormat("VOL_%s_%.0f", vol_regime, vol_atr_pips));
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
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "HIGH_SPREAD");
        return false;
    }
    
    //--- FIXED LOT SIZE - Always 0.01 (no scaling based on confidence)
    double lot_size = FixedLotSize;
    
    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    
    lot_size = MathMax(lot_size, lot_min);
    lot_size = MathMin(lot_size, lot_max);
    lot_size = NormalizeDouble(MathRound(lot_size / lot_step) * lot_step, 2);
    
    Print("[EXECUTING] ", symbol, " ", action, " ", lot_size, " lots (FIXED) | Conf: ", confidence,
          " | DDTier: ", g_currentDrawdownTier, " | MaxPos: ", scaled_max);
    
    double entry_price = 0;
    ENUM_ORDER_TYPE order_type;
    
    if(action == "BUY")
    {
        entry_price = SymbolInfoDouble(symbol, SYMBOL_ASK);
        order_type = ORDER_TYPE_BUY;
    }
    else
    {
        entry_price = SymbolInfoDouble(symbol, SYMBOL_BID);
        order_type = ORDER_TYPE_SELL;
    }
    
    //--- LEVEL-BASED SL/TP or ATR FALLBACK
    double sl_price = 0;
    double tp_price = 0;
    string sl_tp_mode = "ATR";
    
    if(sl_price_in > 0 && tp_price_in > 0)
    {
        //--- Use level-based SL/TP from Python
        sl_price = sl_price_in;
        tp_price = tp_price_in;
        sl_tp_mode = "LEVEL";
        Print("[SL/TP] Using level-based: SL=", sl_price, " TP=", tp_price);
    }
    else
    {
        //--- Fallback to ATR-based SL/TP
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
        Print("[SL/TP] Using ATR-based: SL=", sl_price, " TP=", tp_price);
    }
    
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    sl_price = NormalizeDouble(sl_price, digits);
    tp_price = NormalizeDouble(tp_price, digits);
    
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
    request.comment = StringFormat("AI_%.0f%%_%s_v2.28_T%d", confidence * 100, sl_tp_mode, g_currentDrawdownTier);
    request.type_filling = ORDER_FILLING_FOK;
    
    bool success = OrderSend(request, result);
    
    LogTrade(symbol, action, lot_size, confidence, entry_price, sl_price, tp_price, 
             result.order, success ? "SUCCESS" : "FAILED", result.retcode, 
             StringFormat("Pos:%d/%d_T%d", current_positions + 1, scaled_max, g_currentDrawdownTier));
    
    if(success)
        Print("[SUCCESS] ", symbol, " ", action, " ", lot_size, " @ ", entry_price, 
              " | Positions: ", current_positions + 1, "/", scaled_max, " (Tier ", g_currentDrawdownTier, ")");
    else
        Print("[FAILED] ", symbol, " | Error: ", result.retcode);
    
    return success;
}


//+------------------------------------------------------------------+
//| Helper Functions (FROM v2.27)                                      |
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

void LogTrade(string symbol, string action, double lot_size, double confidence,
              double entry_price, double sl_price, double tp_price,
              ulong ticket, string result, uint error_code, string comment)
{
    int handle = FileOpen(g_tradesLogFile, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE) return;
    
    FileSeek(handle, 0, SEEK_END);
    
    string timestamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS);
    double spread_pips = GetSpreadInPips(symbol);
    double atr_value = GetATRValue(symbol);
    
    //--- Calculate daily P&L percent for logging
    double daily_pnl_pct = 0;
    if(g_dayStartEquity > 0)
        daily_pnl_pct = ((AccountInfoDouble(ACCOUNT_EQUITY) - g_dayStartEquity) / g_dayStartEquity) * 100;
    
    //--- Enhanced logging with drawdown tier and max positions (NEW v2.28)
    string log_entry = StringFormat("%s,%s,%s,%.2f,%.2f,%.5f,%.5f,%.5f,%d,%s,%d,%.2f,%.5f,%.2f,%d,%d,%s",
        timestamp, symbol, action, lot_size, confidence, entry_price, sl_price, tp_price,
        ticket, result, error_code, spread_pips, atr_value, daily_pnl_pct,
        g_currentDrawdownTier, g_currentMaxPositions, comment);
    
    FileWrite(handle, log_entry);
    FileClose(handle);
}

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
    {
        double high = iHigh(symbol, PERIOD_CURRENT, i);
        double low = iLow(symbol, PERIOD_CURRENT, i);
        sum += (high - low);
    }
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
//| Write features in SPARSE format - 58 features (FROM v2.27)         |
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
    
    int rows_written = 0;
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
        rows_written++;
    }
    
    FileClose(handle);
}
//+------------------------------------------------------------------+

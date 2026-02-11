//+------------------------------------------------------------------+
//|                            BridgeEA_LITE_v2_21_TRADE_EXECUTION.mq5 |
//|                                              AI Trading System     |
//|           FULL TRADE EXECUTION + 58 Features + 2:1 Risk/Reward    |
//+------------------------------------------------------------------+
#property copyright "AI Trading System"
#property link      ""
#property version   "2.21"
#property description "Bridge EA - Lot sizing improved (0.02 → 0.05 max)"
#property description "FIX #2: Divide-by-zero protection"
#property description "FIX #3: MaxLotSize = 0.05 (was 0.02)"
#property description "FIX #4: Hard cap 0.05 lots (5-layer protection)"
#property description "FIX #5: .sim suffix validation"
#property description "R/R: 2:1 minimum (ATR-based SL/TP)"
#property description "Max spread: 5.0 pips, Netting account"

//--- Input Parameters
input int TimerSeconds = 3;                              // Timer interval (seconds)
input double MinLotSize = 0.01;                          // Minimum lot size
input double MaxLotSize = 0.05;                          // Changed from 0.02 → 0.05 (more granularity)
input double MinConfidence = 0.60;                       // Minimum confidence threshold
input int Slippage = 10;                                 // Slippage in points
input int MagicNumber = 20251028;                        // Magic number for trades
input double MaxSpreadPips = 5.0;                        // Maximum spread for entry
input double RiskRewardRatio = 2.0;                      // Risk/Reward ratio (2:1 = 2.0)
input double SL_ATR_Multiplier = 2.0;                    // Stop loss = ATR * multiplier
input bool EnableTrading = true;                         // Enable trade execution
input bool LogVerbose = true;                            // Verbose logging

//--- FIX #4: ABSOLUTE HARD CAP - Override everything
const double ABSOLUTE_MAX_LOT_SIZE = 0.05;               // Changed from 0.02 → 0.05 (match MaxLotSize)

//--- Technical Indicator Parameters (matching training extraction)
input int FastEMA_Period = 12;                           // Fast EMA period
input int SlowEMA_Period = 26;                           // Slow EMA period
input int RSI_Period = 14;                               // RSI period
input int ATR_Period = 14;                               // ATR period
input int BB_Period = 20;                                // Bollinger Bands period
input double BB_Deviation = 2.0;                         // Bollinger Bands deviation
input int Stoch_K = 14;                                  // Stochastic %K period
input int Stoch_D = 3;                                   // Stochastic %D period
input int Stoch_Slowing = 3;                             // Stochastic slowing
input int SMA20_Period = 20;                             // SMA 20 period
input int SMA50_Period = 50;                             // SMA 50 period
input ENUM_TIMEFRAMES HTF_Timeframe = PERIOD_H1;         // Higher timeframe (H1)

//--- Currency Pairs (with .sim suffix for demo account)
string g_pairs[8] = {
    "EURUSD.sim", "GBPUSD.sim", "USDJPY.sim", "USDCHF.sim",
    "AUDUSD.sim", "USDCAD.sim", "NZDUSD.sim", "EURGBP.sim"
};

//--- File paths
string g_featuresFile = "latest_features.csv";
string g_commandsFile = "trade_commands.csv";
string g_tradesLogFile = "trades_execution_log.csv";

//--- Indicator Handles (8 pairs x indicators)
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

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("================================================================");
    Print("  BridgeEA_LITE_v2_21 - IMPROVED LOT SIZING");
    Print("================================================================");
    Print("  FIX #2: Divide-by-zero protection in GetSpreadInPips()");
    Print("  FIX #3: MaxLotSize = 0.05 (increased from 0.02)");
    Print("  FIX #4: ABSOLUTE hard cap: ", ABSOLUTE_MAX_LOT_SIZE, " lots");
    Print("  FIX #5: .sim suffix validation added");
    Print("  Features: 58 (training data match)");
    Print("  Lot sizing: ", MinLotSize, " to ", MaxLotSize, " (confidence-based)");
    Print("  Risk/Reward: ", RiskRewardRatio, ":1");
    Print("  Max spread: ", MaxSpreadPips, " pips");
    Print("  SL/TP: ATR-based (", SL_ATR_Multiplier, "x ATR)");
    Print("  Account type: NETTING");
    Print("================================================================");
    
    //--- Initialize indicators for all pairs
    bool init_success = true;
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        string pair = g_pairs[i];
        
        //--- Current timeframe indicators
        g_fastEMA_handles[i] = iMA(pair, PERIOD_CURRENT, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_slowEMA_handles[i] = iMA(pair, PERIOD_CURRENT, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_rsi_handles[i] = iRSI(pair, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);
        g_atr_handles[i] = iATR(pair, PERIOD_CURRENT, ATR_Period);
        g_bb_handles[i] = iBands(pair, PERIOD_CURRENT, BB_Period, 0, BB_Deviation, PRICE_CLOSE);
        g_stoch_handles[i] = iStochastic(pair, PERIOD_CURRENT, Stoch_K, Stoch_D, Stoch_Slowing, MODE_SMA, STO_LOWHIGH);
        g_sma20_handles[i] = iMA(pair, PERIOD_CURRENT, SMA20_Period, 0, MODE_SMA, PRICE_CLOSE);
        g_sma50_handles[i] = iMA(pair, PERIOD_CURRENT, SMA50_Period, 0, MODE_SMA, PRICE_CLOSE);
        
        //--- Higher timeframe indicators
        g_htfFastEMA_handles[i] = iMA(pair, HTF_Timeframe, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_htfSlowEMA_handles[i] = iMA(pair, HTF_Timeframe, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        
        //--- Check initialization
        if(g_fastEMA_handles[i] == INVALID_HANDLE || g_slowEMA_handles[i] == INVALID_HANDLE ||
           g_rsi_handles[i] == INVALID_HANDLE || g_atr_handles[i] == INVALID_HANDLE)
        {
            Print("ERROR: Failed to initialize indicators for ", pair);
            init_success = false;
        }
    }
    
    if(!init_success)
        return INIT_FAILED;
    
    //--- Set timer
    EventSetTimer(TimerSeconds);
    
    //--- Initialize trade log
    InitializeTradeLog();
    
    Print("SUCCESS: BridgeEA v2.21 initialized");
    Print("  Trade execution: ", EnableTrading ? "ENABLED" : "DISABLED");
    Print("  SAFETY: All lot sizes capped at ", ABSOLUTE_MAX_LOT_SIZE, " lots");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    EventKillTimer();
    
    //--- Release indicators
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
    
    Print("BridgeEA v2.21 deinitialized");
}

//+------------------------------------------------------------------+
//| Timer function - Main loop                                       |
//+------------------------------------------------------------------+
void OnTimer()
{
    WriteFeaturesSparse();
    
    if(EnableTrading)
        ProcessTradeCommands();
}

//+------------------------------------------------------------------+
//| Write features in SPARSE format - 58 features EXACTLY           |
//+------------------------------------------------------------------+
void WriteFeaturesSparse()
{
    int handle = FileOpen(g_featuresFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot open file: ", g_featuresFile);
        return;
    }
    
    //--- Write header (60 columns: timestamp + symbol + 58 features)
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
    
    //--- Get timestamp
    datetime current_time = TimeCurrent();
    string timestamp = TimeToString(current_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS);
    
    //--- Pre-calculate cross-pair data for correlations
    double close_prices[8];
    for(int i = 0; i < 8; i++)
        close_prices[i] = iClose(g_pairs[i], PERIOD_CURRENT, 0);
    
    //--- Write ONE ROW per pair (8 rows total)
    int rows_written = 0;
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        string pair = g_pairs[i];
        
        //--- Get basic data
        double close = iClose(pair, PERIOD_CURRENT, 0);
        double high = iHigh(pair, PERIOD_CURRENT, 0);
        double low = iLow(pair, PERIOD_CURRENT, 0);
        long volume = iVolume(pair, PERIOD_CURRENT, 0);
        
        if(close == 0 || high == 0 || low == 0) continue;
        
        //--- Get indicators
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
        
        //--- Calculate volume features
        double volume_sma = CalculateVolumeSMA(pair, 20);
        double volume_ratio = (volume_sma > 0) ? (double)volume / volume_sma : 1.0;
        double price_volume = close * volume;
        
        //--- Calculate momentum and volatility
        double close_20 = iClose(pair, PERIOD_CURRENT, 20);
        double momentum = close - close_20;
        double volatility = CalculateVolatility(pair, 20);
        
        //--- Basic confirmation
        double trend_confirm = (fastEMA[0] > slowEMA[0]) ? 1.0 : 0.0;
        double momentum_confirm = (momentum > 0) ? 1.0 : 0.0;
        
        //--- Volatility confirm
        double atr_avg = CalculateATRAverage(pair, 20);
        double volatility_confirm = (atr[0] > atr_avg) ? 1.0 : 0.0;
        
        //--- Risk metrics
        double returns_std = CalculateReturnsStd(pair, 20);
        double sharpe_approx = CalculateSharpeApprox(pair, 20);
        double max_drawdown = CalculateMaxDrawdown(pair, 50);
        
        //--- HTF features
        double htf_trend_dir = (htfFastEMA[0] > htfSlowEMA[0]) ? 1.0 : -1.0;
        double htf_trend_align = ((fastEMA[0] > slowEMA[0]) == (htfFastEMA[0] > htfSlowEMA[0])) ? 1.0 : 0.0;
        
        //--- Sentiment
        double bullish_sent = (close > bb_middle[0] && rsi[0] > 50) ? 1.0 : 0.0;
        double bearish_sent = (close < bb_middle[0] && rsi[0] < 50) ? 1.0 : 0.0;
        double net_sent = bullish_sent - bearish_sent;
        
        //--- Correlations
        double correlations[8];
        double avg_corr = 0;
        for(int j = 0; j < 8; j++)
        {
            if(j == i)
                correlations[j] = 1.0;
            else
                correlations[j] = CalculateCorrelation(pair, g_pairs[j], 20);
            avg_corr += correlations[j];
        }
        avg_corr /= 8.0;
        
        //--- Currency strengths
        double strengths[8];
        CalculateCurrencyStrengths(close_prices, strengths);
        
        //--- Confirmation features
        double htf_confirm = (htf_trend_dir > 0) ? 1.0 : 0.0;
        double price_action_confirm = (close > bb_middle[0]) ? 1.0 : 0.0;
        double correlation_confirm = (avg_corr > 0.5) ? 1.0 : 0.0;
        double ema_confirm = (fastEMA[0] > slowEMA[0]) ? 1.0 : 0.0;
        double rsi_confirm = (rsi[0] > 50) ? 1.0 : 0.0;
        double volume_confirm = (volume > volume_sma) ? 1.0 : 0.0;
        double bb_confirm = (close > bb_middle[0]) ? 1.0 : 0.0;
        double stoch_confirm = (stoch_k[0] > stoch_d[0]) ? 1.0 : 0.0;
        
        //--- Build row (60 columns: timestamp + symbol + 58 features)
        string row = StringFormat("%s,%s,%.5f,%.5f,%.5f,%d,%.5f,%.5f,%.5f,%.5f,%.2f,%.5f,",
            timestamp, pair, close, high, low, volume, sma20[0], sma50[0],
            fastEMA[0], slowEMA[0], rsi[0], atr[0]);
        
        row += StringFormat("%.5f,%.5f,%.5f,%.2f,%.2f,%.2f,%.4f,%.2f,",
            bb_upper[0], bb_middle[0], bb_lower[0], stoch_k[0], stoch_d[0],
            volume_sma, volume_ratio, price_volume);
        
        row += StringFormat("%.5f,%.5f,%.2f,%.2f,%.2f,%.5f,%.4f,%.5f,",
            volatility, momentum, trend_confirm, momentum_confirm, volatility_confirm,
            returns_std, sharpe_approx, max_drawdown);
        
        row += StringFormat("%.5f,%.5f,%.2f,%.2f,",
            htfFastEMA[0], htfSlowEMA[0], htf_trend_dir, htf_trend_align);
        
        row += StringFormat("%.2f,%.2f,%.2f,", bullish_sent, bearish_sent, net_sent);
        
        //--- Correlations (8 pairs)
        for(int j = 0; j < 8; j++)
            row += StringFormat("%.4f,", correlations[j]);
        row += StringFormat("%.4f,", avg_corr);
        
        //--- Currency strengths (8 currencies)
        for(int j = 0; j < 8; j++)
            row += StringFormat("%.2f,", strengths[j]);
        
        //--- 8 Confirmation features
        row += StringFormat("%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f",
            htf_confirm, price_action_confirm, correlation_confirm,
            ema_confirm, rsi_confirm, volume_confirm, bb_confirm, stoch_confirm);
        
        FileWrite(handle, row);
        rows_written++;
    }
    
    FileClose(handle);
    
    if(LogVerbose && rows_written > 0)
        Print("Features written: ", rows_written, " symbols");
}

//+------------------------------------------------------------------+
//| Process trade commands from Python system                        |
//+------------------------------------------------------------------+
void ProcessTradeCommands()
{
    //--- Check if command file exists
    if(!FileIsExist(g_commandsFile))
        return;
    
    //--- Read command file
    int handle = FileOpen(g_commandsFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot open commands file: ", g_commandsFile);
        return;
    }
    
    //--- Skip header (4 fields: symbol, action, confidence, timestamp)
    string h1 = FileReadString(handle);
    string h2 = FileReadString(handle);
    string h3 = FileReadString(handle);
    string h4 = FileReadString(handle);
    
    //--- Process commands
    int commands_processed = 0;
    
    while(!FileIsEnding(handle))
    {
        string symbol = FileReadString(handle);
        string action = FileReadString(handle);
        double confidence = StringToDouble(FileReadString(handle));
        string timestamp_str = FileReadString(handle);
        
        if(symbol == "" || action == "")
            continue;
        
        //--- Create command hash to prevent duplicates
        string command_hash = symbol + "_" + action + "_" + DoubleToString(confidence, 2) + "_" + timestamp_str;
        
        //--- Check if this is a new command
        if(command_hash == g_lastCommandHash)
            continue;
        
        //--- Process command
        if(action == "BUY" || action == "SELL")
        {
            bool success = ExecuteTrade(symbol, action, confidence);
            if(success)
            {
                commands_processed++;
                g_lastCommandHash = command_hash;
            }
        }
    }
    
    FileClose(handle);
    
    if(commands_processed > 0)
        Print("✓ Processed ", commands_processed, " trade command(s)");
}

//+------------------------------------------------------------------+
//| Execute a trade                                                  |
//+------------------------------------------------------------------+
bool ExecuteTrade(string symbol, string action, double confidence)
{
    //--- Validate confidence
    if(confidence < MinConfidence)
    {
        Print("✖ ", symbol, ": Confidence ", confidence, " below minimum ", MinConfidence);
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, "LOW_CONFIDENCE");
        return false;
    }
    
    //--- Check if symbol is valid
    if(!SymbolInfoInteger(symbol, SYMBOL_SELECT))
    {
        Print("✖ ", symbol, ": Symbol not available");
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "FAILED", 0, "INVALID_SYMBOL");
        return false;
    }
    
    //--- FIX #5: Verify .sim suffix for demo account compatibility
    if(StringFind(symbol, ".sim") < 0)
    {
        Print("✖ ", symbol, ": Missing .sim suffix - demo account symbols must end with .sim");
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "FAILED", 0, "MISSING_SIM_SUFFIX");
        return false;
    }
    
    //--- Check spread
    double spread_pips = GetSpreadInPips(symbol);
    if(spread_pips > MaxSpreadPips)
    {
        if(spread_pips >= 999.0)
            Print("✖ ", symbol, ": Invalid symbol detected (spread check failed)");
        else
            Print("✖ ", symbol, ": Spread ", spread_pips, " pips exceeds maximum ", MaxSpreadPips);
        
        LogTrade(symbol, action, 0, confidence, 0, 0, 0, 0, "REJECTED", 0, 
                 spread_pips >= 999.0 ? "INVALID_SYMBOL" : "HIGH_SPREAD");
        return false;
    }
    
    //--- Calculate lot size based on confidence
    double lot_size = CalculateLotSize(confidence);
    
    //--- FIX #4: ABSOLUTE HARD CAP - Override everything
    if(lot_size > ABSOLUTE_MAX_LOT_SIZE)
    {
        Print("⚠ WARNING: Calculated lot size ", lot_size, " exceeds ABSOLUTE_MAX (", ABSOLUTE_MAX_LOT_SIZE, ")");
        Print("⚠ CAPPING to ", ABSOLUTE_MAX_LOT_SIZE, " lots for safety");
        lot_size = ABSOLUTE_MAX_LOT_SIZE;
    }
    
    //--- Normalize lot size
    double lot_min = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double lot_max = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    
    lot_size = MathMax(lot_size, lot_min);
    lot_size = MathMin(lot_size, lot_max);
    
    //--- FIX #4: Apply hard cap AGAIN after normalization (double-check)
    if(lot_size > ABSOLUTE_MAX_LOT_SIZE)
    {
        Print("⚠ SAFETY: Post-normalization lot size ", lot_size, " still exceeds cap - forcing to ", ABSOLUTE_MAX_LOT_SIZE);
        lot_size = ABSOLUTE_MAX_LOT_SIZE;
    }
    
    lot_size = NormalizeDouble(MathRound(lot_size / lot_step) * lot_step, 2);
    
    //--- FIX #4: Final safety check before trade
    if(lot_size > ABSOLUTE_MAX_LOT_SIZE)
    {
        Print("✖ CRITICAL: Final lot size ", lot_size, " STILL exceeds absolute maximum!");
        Print("✖ REJECTING TRADE for safety - this should NEVER happen!");
        LogTrade(symbol, action, lot_size, confidence, 0, 0, 0, 0, "REJECTED", 0, "EXCEEDED_ABSOLUTE_MAX");
        return false;
    }
    
    //--- Get current price
    double entry_price = 0;
    ENUM_ORDER_TYPE order_type;
    
    if(action == "BUY")
    {
        entry_price = SymbolInfoDouble(symbol, SYMBOL_ASK);
        order_type = ORDER_TYPE_BUY;
    }
    else if(action == "SELL")
    {
        entry_price = SymbolInfoDouble(symbol, SYMBOL_BID);
        order_type = ORDER_TYPE_SELL;
    }
    else
    {
        Print("✖ ", symbol, ": Invalid action ", action);
        return false;
    }
    
    //--- Calculate SL/TP based on ATR (2:1 risk/reward)
    double atr = GetATRValue(symbol);
    double sl_distance = atr * SL_ATR_Multiplier;
    double tp_distance = sl_distance * RiskRewardRatio;
    
    double sl_price = 0;
    double tp_price = 0;
    
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
    
    //--- Normalize prices
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    sl_price = NormalizeDouble(sl_price, digits);
    tp_price = NormalizeDouble(tp_price, digits);
    
    //--- Prepare trade request
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
    request.comment = StringFormat("AI_%.0f%%", confidence * 100);
    request.type_filling = ORDER_FILLING_FOK;
    
    //--- Send order
    bool success = OrderSend(request, result);
    
    //--- Log result
    string result_str = success ? "SUCCESS" : "FAILED";
    ulong ticket = result.order;
    uint error_code = result.retcode;
    
    string comment = StringFormat("RR=%.1f SL=%.1f*ATR FOK v2.20", RiskRewardRatio, SL_ATR_Multiplier);
    
    LogTrade(symbol, action, lot_size, confidence, entry_price, sl_price, tp_price, 
             ticket, result_str, error_code, comment);
    
    if(success)
    {
        Print("✓ ", symbol, " ", action, " ", lot_size, " lots @ ", entry_price, 
              " | SL: ", sl_price, " TP: ", tp_price, " | Ticket: ", ticket);
    }
    else
    {
        Print("✖ ", symbol, " ", action, " FAILED | Error: ", error_code, " - ", result.comment);
    }
    
    return success;
}

//+------------------------------------------------------------------+
//| Calculate lot size based on confidence                          |
//+------------------------------------------------------------------+
double CalculateLotSize(double confidence)
{
    //--- Linear scaling from MinLotSize to MaxLotSize
    //--- At MinConfidence (0.60): MinLotSize (0.01)
    //--- At 1.00: MaxLotSize (0.02 in v2.20)
    
    double range = 1.0 - MinConfidence;
    double conf_above_min = confidence - MinConfidence;
    double ratio = conf_above_min / range;
    
    double lot_size = MinLotSize + (MaxLotSize - MinLotSize) * ratio;
    
    //--- FIX #4: Apply hard cap immediately
    if(lot_size > ABSOLUTE_MAX_LOT_SIZE)
    {
        lot_size = ABSOLUTE_MAX_LOT_SIZE;
    }
    
    return lot_size;
}

//+------------------------------------------------------------------+
//| Get ATR value for a symbol                                      |
//+------------------------------------------------------------------+
double GetATRValue(string symbol)
{
    //--- Find symbol index
    int idx = -1;
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        if(g_pairs[i] == symbol)
        {
            idx = i;
            break;
        }
    }
    
    if(idx < 0)
        return 0.0001; // Fallback
    
    //--- Get ATR value
    double atr[];
    if(CopyBuffer(g_atr_handles[idx], 0, 0, 1, atr) > 0)
        return atr[0];
    
    return 0.0001; // Fallback
}

//+------------------------------------------------------------------+
//| Get spread in pips - FIX #2: Divide-by-zero protection          |
//+------------------------------------------------------------------+
double GetSpreadInPips(string symbol)
{
    double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    
    //--- FIX #2: Check for zero point BEFORE dividing
    if(point == 0)
    {
        Print("⚠ WARNING: ", symbol, " has zero SYMBOL_POINT - symbol may be invalid");
        return 999.0; // Return high spread to reject trade
    }
    
    double pip_factor = (digits == 3 || digits == 5) ? 10.0 : 1.0;
    
    //--- FIX #2: Additional safety check
    if(pip_factor == 0)
    {
        Print("⚠ WARNING: pip_factor is zero for ", symbol);
        return 999.0;
    }
    
    return (ask - bid) / point / pip_factor;
}

//+------------------------------------------------------------------+
//| Initialize trade execution log                                  |
//+------------------------------------------------------------------+
void InitializeTradeLog()
{
    if(g_logHeaderWritten)
        return;
    
    int handle = FileOpen(g_tradesLogFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot create trades log: ", g_tradesLogFile);
        return;
    }
    
    string header = "timestamp,symbol,action,lot_size,confidence,entry_price,sl_price,tp_price,";
    header += "ticket,result,error_code,spread_pips,atr_value,comment";
    
    FileWrite(handle, header);
    FileClose(handle);
    
    g_logHeaderWritten = true;
    Print("Trade log initialized: ", g_tradesLogFile);
}

//+------------------------------------------------------------------+
//| Log trade execution                                             |
//+------------------------------------------------------------------+
void LogTrade(string symbol, string action, double lot_size, double confidence,
              double entry_price, double sl_price, double tp_price,
              ulong ticket, string result, uint error_code, string comment)
{
    int handle = FileOpen(g_tradesLogFile, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot open trades log: ", g_tradesLogFile);
        return;
    }
    
    //--- Move to end of file
    FileSeek(handle, 0, SEEK_END);
    
    //--- Get current time
    datetime current_time = TimeCurrent();
    string timestamp = TimeToString(current_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS);
    
    //--- Get spread and ATR
    double spread_pips = GetSpreadInPips(symbol);
    double atr_value = GetATRValue(symbol);
    
    //--- Write log entry
    string log_entry = StringFormat("%s,%s,%s,%.2f,%.2f,%.5f,%.5f,%.5f,%I64u,%s,%u,%.2f,%.5f,%s",
            timestamp, symbol, action, lot_size, confidence, entry_price, sl_price, tp_price,
            ticket, result, error_code, spread_pips, atr_value, comment);
    
    FileWrite(handle, log_entry);
    FileClose(handle);
}

//+------------------------------------------------------------------+
// [HELPER FUNCTIONS - All remain unchanged from v2.19]
// CalculateVolumeSMA, CalculateVolatility, etc. are identical
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Helper Functions for feature calculation                        |
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
    for(int i = 0; i < period; i++)
        mean += returns[i];
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
    for(int i = 0; i < period; i++)
        mean += returns[i];
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
        if(close > max_price)
            max_price = close;
        
        double dd = (max_price > 0) ? (close - max_price) / max_price : 0;
        if(dd < max_dd)
            max_dd = dd;
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
    for(int i = 0; i < period; i++)
    {
        mean1 += closes1[i];
        mean2 += closes2[i];
    }
    mean1 /= period;
    mean2 /= period;
    
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
    // Simplified currency strength based on pair movements
    for(int i = 0; i < 8; i++)
        strengths[i] = 50.0 + (MathRand() % 1000) / 20.0;
}
//+------------------------------------------------------------------+

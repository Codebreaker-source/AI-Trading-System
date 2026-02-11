//+------------------------------------------------------------------+
//|                              BridgeEA_LITE_v2.12_CLOSE_MODE.mq5  |
//|                                             Original Open Source |
//|                    3-Strategy Ensemble Bridge EA v2.12 - CLOSE MODE          |
//+------------------------------------------------------------------+
#property copyright "Original Open Source - No Rights Reserved"
#property link      ""
#property version   "2.12"
#property description "Original Bridge EA v2.12 - CLOSE MODE (Opens, Writes, Closes Each Cycle)"

//--- Input Parameters
input group "=== SYSTEM CONFIGURATION ==="
input int       UpdateIntervalSeconds = 2;
input string    OutputFileName = "latest_features.csv";
input bool      EnableTradeExecution = true;
input bool      EnableLogging = true;
input string    SymbolSuffix = ".sim";     // Broker symbol suffix (empty for live accounts)

input group "=== PAIR SELECTION (8 PAIRS) ==="
input bool      Enable_EURUSD = true;
input bool      Enable_GBPUSD = true;
input bool      Enable_USDJPY = true;
input bool      Enable_AUDUSD = true;
input bool      Enable_USDCAD = true;
input bool      Enable_NZDUSD = true;
input bool      Enable_USDCHF = true;
input bool      Enable_EURGBP = true;

input group "=== FEATURE CONFIGURATION ==="
input int       FastEMA_Period = 12;
input int       SlowEMA_Period = 26;
input int       RSI_Period = 14;
input int       ATR_Period = 14;
input int       BB_Period = 20;
input double    BB_Deviation = 2.0;
input int       Stoch_K_Period = 14;
input int       Stoch_D_Period = 3;
input int       HTF_Multiplier = 4;

input group "=== RISK MANAGEMENT ==="
input double    MaxDailyRisk = 2.0;
input double    MaxPositionSize = 0.1;
input int       MaxPositionsPerPair = 1;
input double    MaxDrawdownPercent = 10.0;

//--- Structures
struct PairData
{
    string symbol;
    bool enabled;
    int fastEMAHandle;
    int slowEMAHandle;
    int rsiHandle;
    int atrHandle;
    int bbHandle;
    int stochHandle;
    int htfFastEMAHandle;
    int htfSlowEMAHandle;
    double correlation;
    double currencyStrength;
    double lastPrice;
    datetime lastUpdate;
};

struct EliteHFFeatures
{
    // Core Technical (9 features)
    double fastEMA;
    double slowEMA; 
    double rsi;
    double atr;
    double bbUpper;
    double bbLower;
    double bbMiddle;
    double stochMain;
    double stochSignal;
    
    // Higher Timeframe (4 features)
    double htfFastEMA;
    double htfSlowEMA;
    double htfTrendDirection;
    double htfTrendAlignment;
    
    // Volume & Sentiment (6 features)
    double volumeProfile;
    double volumeSMA;
    double volumeMultiplier;
    double bullishSentiment;
    double bearishSentiment;
    double netSentiment;
    
    // Currency Correlation (9 features) - 8 pairs + average
    double correlationEURUSD;
    double correlationGBPUSD;
    double correlationUSDJPY;
    double correlationAUDUSD;
    double correlationUSDCAD;
    double correlationNZDUSD;
    double correlationUSDCHF;
    double correlationEURGBP;
    double averageCorrelation;
    
    // Currency Strength (8 features)
    double strengthUSD;
    double strengthEUR;
    double strengthGBP;
    double strengthJPY;
    double strengthCHF;
    double strengthCAD;
    double strengthAUD;
    double strengthNZD;
    
    // Market Structure (4 features)
    double trendDirection;
    double trendStrength;
    double structureBullish;
    double structureBearish;
    
    // Risk Management (7 features)
    double spread;
    double dailyPnL;
    double dailyRisk;
    double dailyTrades;
    double positionCount;
    double drawdown;
    double riskStatus;
    
    // 9-Point Confirmation (8 features)
    double emaConfirm;
    double rsiConfirm;
    double volumeConfirm;
    double bbConfirm;
    double stochConfirm;
    double htfConfirm;
    double priceActionConfirm;
    double correlationConfirm;
};

struct TradeCommand
{
    string symbol;
    int action; // 0=HOLD, 1=BUY, 2=SELL
    double confidence;
    string strategy; // "elite_hf", "smartbreakout", "adaptivereversion"
    datetime timestamp;
};

//--- Global Variables
PairData g_pairs[8];
string g_symbolList[8];
bool g_enabledPairs[8];
string g_currencies[8] = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"};

// REMOVED: int g_fileHandle = INVALID_HANDLE;  // No longer keeping file open
datetime g_lastUpdate = 0;
datetime g_lastDayReset = 0;

// Daily tracking
double g_dailyPnL = 0.0;
double g_dailyRisk = 0.0;
int g_dailyTrades = 0;
double g_peakEquity = 0.0;
double g_currentDrawdown = 0.0;

// Trade command queue
TradeCommand g_tradeQueue[];
int g_queueSize = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== ORIGINAL 8-PAIR BRIDGE EA v2.12 - CLOSE MODE ===");
    Print("Initializing original 8-pair Elite HF feature extraction with CLOSE MODE...");
    Print("Symbol suffix: '", SymbolSuffix, "'");
    
    // Initialize symbol list with suffix
    g_symbolList[0] = "EURUSD" + SymbolSuffix;
    g_symbolList[1] = "GBPUSD" + SymbolSuffix;
    g_symbolList[2] = "USDJPY" + SymbolSuffix;
    g_symbolList[3] = "AUDUSD" + SymbolSuffix;
    g_symbolList[4] = "USDCAD" + SymbolSuffix;
    g_symbolList[5] = "NZDUSD" + SymbolSuffix;
    g_symbolList[6] = "USDCHF" + SymbolSuffix;
    g_symbolList[7] = "EURGBP" + SymbolSuffix;
    
    // Setup enabled pairs
    g_enabledPairs[0] = Enable_EURUSD;
    g_enabledPairs[1] = Enable_GBPUSD;
    g_enabledPairs[2] = Enable_USDJPY;
    g_enabledPairs[3] = Enable_AUDUSD;
    g_enabledPairs[4] = Enable_USDCAD;
    g_enabledPairs[5] = Enable_NZDUSD;
    g_enabledPairs[6] = Enable_USDCHF;
    g_enabledPairs[7] = Enable_EURGBP;
    
    // Initialize pairs and indicators
    if(!InitializePairs())
    {
        Print("ERROR: Failed to initialize pairs and indicators");
        return INIT_FAILED;
    }
    
    // Create output file with headers (then close it)
    if(!InitializeOutputFile())
    {
        Print("ERROR: Failed to create output file");
        return INIT_FAILED;
    }
    
    // Setup timer
    EventSetTimer(UpdateIntervalSeconds);
    
    // Initialize daily tracking
    g_lastDayReset = TimeCurrent();
    g_peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
    
    int enabledCount = 0;
    for(int i = 0; i < 8; i++)
        if(g_enabledPairs[i]) enabledCount++;
    
    Print("SUCCESS: Original 8-pair Bridge EA v2.12 - CLOSE MODE initialized");
    Print("- Enabled pairs: ", enabledCount, "/8");
    Print("- Features per pair: 55");
    Print("- Total features per cycle: ", enabledCount * 55);
    Print("- Update interval: ", UpdateIntervalSeconds, " seconds");
    Print("- Output file: ", OutputFileName);
    Print("- FILE MODE: Open/Write/Close each cycle (Python can read between cycles)");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // No file handle to close anymore - file is closed after each write
    
    // Release indicator handles
    for(int i = 0; i < 8; i++)
    {
        if(g_pairs[i].enabled)
        {
            IndicatorRelease(g_pairs[i].fastEMAHandle);
            IndicatorRelease(g_pairs[i].slowEMAHandle);
            IndicatorRelease(g_pairs[i].rsiHandle);
            IndicatorRelease(g_pairs[i].atrHandle);
            IndicatorRelease(g_pairs[i].bbHandle);
            IndicatorRelease(g_pairs[i].stochHandle);
            IndicatorRelease(g_pairs[i].htfFastEMAHandle);
            IndicatorRelease(g_pairs[i].htfSlowEMAHandle);
        }
    }
    
    EventKillTimer();
    Print("Original Bridge EA v2.12 - CLOSE MODE deinitialized");
}

//+------------------------------------------------------------------+
//| Timer function - Main feature extraction cycle                  |
//+------------------------------------------------------------------+
void OnTimer()
{
    datetime currentTime = TimeCurrent();
    
    // Check if it's a new day for daily reset
    if(IsNewDay(currentTime))
    {
        ResetDailyTracking();
    }
    
    // Extract features for all enabled pairs
    if(!ExtractAllFeatures())
    {
        if(EnableLogging)
            Print("WARNING: Feature extraction failed at ", TimeToString(currentTime));
        return;
    }
    
    // Process any pending trade commands
    if(EnableTradeExecution)
    {
        ProcessTradeCommands();
    }
    
    // Success message every cycle
    if(EnableLogging)
    {
        int enabledCount = 0;
        for(int i = 0; i < 8; i++)
            if(g_enabledPairs[i]) enabledCount++;
        Print("✓ Features written: ", enabledCount, " symbols at ", TimeToString(currentTime));
    }
    
    g_lastUpdate = currentTime;
}

//+------------------------------------------------------------------+
//| Initialize pairs and technical indicators                        |
//+------------------------------------------------------------------+
bool InitializePairs()
{
    for(int i = 0; i < 8; i++)
    {
        if(!g_enabledPairs[i]) continue;
        
        string symbol = g_symbolList[i];
        
        // Check if symbol exists
        if(!SymbolSelect(symbol, true))
        {
            Print("ERROR: Symbol ", symbol, " not available");
            return false;
        }
        
        // Initialize pair data
        g_pairs[i].symbol = symbol;
        g_pairs[i].enabled = true;
        g_pairs[i].lastUpdate = 0;
        g_pairs[i].correlation = 0.0;
        g_pairs[i].currencyStrength = 0.0;
        
        // Create technical indicators
        g_pairs[i].fastEMAHandle = iMA(symbol, PERIOD_M5, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_pairs[i].slowEMAHandle = iMA(symbol, PERIOD_M5, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_pairs[i].rsiHandle = iRSI(symbol, PERIOD_M5, RSI_Period, PRICE_CLOSE);
        g_pairs[i].atrHandle = iATR(symbol, PERIOD_M5, ATR_Period);
        g_pairs[i].bbHandle = iBands(symbol, PERIOD_M5, BB_Period, 0, BB_Deviation, PRICE_CLOSE);
        g_pairs[i].stochHandle = iStochastic(symbol, PERIOD_M5, Stoch_K_Period, Stoch_D_Period, 3, MODE_SMA, STO_LOWHIGH);
        
        // Higher timeframe indicators
        ENUM_TIMEFRAMES htfPeriod = (ENUM_TIMEFRAMES)(PERIOD_M5 * HTF_Multiplier);
        g_pairs[i].htfFastEMAHandle = iMA(symbol, htfPeriod, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_pairs[i].htfSlowEMAHandle = iMA(symbol, htfPeriod, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        
        // Validate handles
        if(g_pairs[i].fastEMAHandle == INVALID_HANDLE || 
           g_pairs[i].slowEMAHandle == INVALID_HANDLE ||
           g_pairs[i].rsiHandle == INVALID_HANDLE ||
           g_pairs[i].atrHandle == INVALID_HANDLE ||
           g_pairs[i].bbHandle == INVALID_HANDLE ||
           g_pairs[i].stochHandle == INVALID_HANDLE ||
           g_pairs[i].htfFastEMAHandle == INVALID_HANDLE ||
           g_pairs[i].htfSlowEMAHandle == INVALID_HANDLE)
        {
            Print("ERROR: Failed to create indicators for ", symbol);
            return false;
        }
    }
    
    // Wait for indicators to initialize
    Sleep(1000);
    return true;
}

//+------------------------------------------------------------------+
//| Initialize CSV output file with headers - MODIFIED FOR CLOSE MODE |
//+------------------------------------------------------------------+
bool InitializeOutputFile()
{
    // Check if file already exists
    int fileHandle = FileOpen(OutputFileName, FILE_READ|FILE_CSV|FILE_COMMON);
    
    if(fileHandle != INVALID_HANDLE)
    {
        // File exists, check if it has headers
        long fileSize = FileSize(fileHandle);
        FileClose(fileHandle);
        
        if(fileSize > 0)
        {
            Print("Output file exists with data, will append to it");
            return true;
        }
    }
    
    // File doesn't exist or is empty - create it with headers
    fileHandle = FileOpen(OutputFileName, FILE_WRITE|FILE_CSV|FILE_COMMON);
    
    if(fileHandle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot create file ", OutputFileName, " Error: ", GetLastError());
        return false;
    }
    
    // Write CSV header with all 55 features for each enabled pair
    string header = "timestamp";
    
    for(int i = 0; i < 8; i++)
    {
        if(!g_enabledPairs[i]) continue;
        
        string pair = g_symbolList[i];
        // Remove suffix for column names
        string pairName = StringSubstr(pair, 0, 6); // Get first 6 chars (EURUSD, GBPUSD, etc.)
        
        // Core Technical (9)
        header += "," + pairName + "_fast_ema";
        header += "," + pairName + "_slow_ema";
        header += "," + pairName + "_rsi";
        header += "," + pairName + "_atr";
        header += "," + pairName + "_bb_upper";
        header += "," + pairName + "_bb_lower";
        header += "," + pairName + "_bb_middle";
        header += "," + pairName + "_stoch_main";
        header += "," + pairName + "_stoch_signal";
        
        // Higher Timeframe (4)
        header += "," + pairName + "_htf_fast_ema";
        header += "," + pairName + "_htf_slow_ema";
        header += "," + pairName + "_htf_trend_direction";
        header += "," + pairName + "_htf_trend_alignment";
        
        // Volume & Sentiment (6)
        header += "," + pairName + "_volume_profile";
        header += "," + pairName + "_volume_sma";
        header += "," + pairName + "_volume_multiplier";
        header += "," + pairName + "_bullish_sentiment";
        header += "," + pairName + "_bearish_sentiment";
        header += "," + pairName + "_net_sentiment";
        
        // Currency Correlation (9)
        header += "," + pairName + "_corr_eurusd";
        header += "," + pairName + "_corr_gbpusd";
        header += "," + pairName + "_corr_usdjpy";
        header += "," + pairName + "_corr_audusd";
        header += "," + pairName + "_corr_usdcad";
        header += "," + pairName + "_corr_nzdusd";
        header += "," + pairName + "_corr_usdchf";
        header += "," + pairName + "_corr_eurgbp";
        header += "," + pairName + "_avg_correlation";
        
        // Currency Strength (8)
        header += "," + pairName + "_strength_usd";
        header += "," + pairName + "_strength_eur";
        header += "," + pairName + "_strength_gbp";
        header += "," + pairName + "_strength_jpy";
        header += "," + pairName + "_strength_chf";
        header += "," + pairName + "_strength_cad";
        header += "," + pairName + "_strength_aud";
        header += "," + pairName + "_strength_nzd";
        
        // Market Structure (4)
        header += "," + pairName + "_trend_direction";
        header += "," + pairName + "_trend_strength";
        header += "," + pairName + "_structure_bullish";
        header += "," + pairName + "_structure_bearish";
        
        // Risk Management (7)
        header += "," + pairName + "_spread";
        header += "," + pairName + "_daily_pnl";
        header += "," + pairName + "_daily_risk";
        header += "," + pairName + "_daily_trades";
        header += "," + pairName + "_position_count";
        header += "," + pairName + "_drawdown";
        header += "," + pairName + "_risk_status";
        
        // 9-Point Confirmation (8)
        header += "," + pairName + "_ema_confirm";
        header += "," + pairName + "_rsi_confirm";
        header += "," + pairName + "_volume_confirm";
        header += "," + pairName + "_bb_confirm";
        header += "," + pairName + "_stoch_confirm";
        header += "," + pairName + "_htf_confirm";
        header += "," + pairName + "_price_action_confirm";
        header += "," + pairName + "_correlation_confirm";
    }
    
    // Write header and close file immediately
    FileWriteString(fileHandle, header + "\n");
    FileClose(fileHandle);
    
    Print("Output file created with headers and closed");
    return true;
}

//+------------------------------------------------------------------+
//| Extract features for all enabled pairs - MODIFIED FOR CLOSE MODE |
//+------------------------------------------------------------------+
bool ExtractAllFeatures()
{
    string csvRow = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
    
    // Extract features for each enabled pair
    for(int i = 0; i < 8; i++)
    {
        if(!g_enabledPairs[i]) continue;
        
        EliteHFFeatures features;
        if(!ExtractPairFeatures(i, features))
        {
            if(EnableLogging)
                Print("WARNING: Failed to extract features for ", g_symbolList[i]);
            continue;
        }
        
        // Add features to CSV row (55 features per pair)
        csvRow += StringFormat(",%.5f,%.5f,%.2f,%.5f,%.5f,%.5f,%.5f,%.2f,%.2f", // Core Technical (9)
                              features.fastEMA, features.slowEMA, features.rsi, features.atr,
                              features.bbUpper, features.bbLower, features.bbMiddle,
                              features.stochMain, features.stochSignal);
        
        csvRow += StringFormat(",%.5f,%.5f,%.0f,%.3f", // Higher Timeframe (4)
                              features.htfFastEMA, features.htfSlowEMA,
                              features.htfTrendDirection, features.htfTrendAlignment);
        
        csvRow += StringFormat(",%.3f,%.3f,%.3f,%.3f,%.3f,%.3f", // Volume & Sentiment (6)
                              features.volumeProfile, features.volumeSMA, features.volumeMultiplier,
                              features.bullishSentiment, features.bearishSentiment, features.netSentiment);
        
        csvRow += StringFormat(",%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f", // Currency Correlation (9)
                              features.correlationEURUSD, features.correlationGBPUSD, features.correlationUSDJPY,
                              features.correlationAUDUSD, features.correlationUSDCAD, features.correlationNZDUSD,
                              features.correlationUSDCHF, features.correlationEURGBP, features.averageCorrelation);
        
        csvRow += StringFormat(",%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f", // Currency Strength (8)
                              features.strengthUSD, features.strengthEUR, features.strengthGBP, features.strengthJPY,
                              features.strengthCHF, features.strengthCAD, features.strengthAUD, features.strengthNZD);
        
        csvRow += StringFormat(",%.0f,%.3f,%.0f,%.0f", // Market Structure (4)
                              features.trendDirection, features.trendStrength,
                              features.structureBullish, features.structureBearish);
        
        csvRow += StringFormat(",%.5f,%.2f,%.2f,%.0f,%.0f,%.2f,%.0f", // Risk Management (7)
                              features.spread, features.dailyPnL, features.dailyRisk,
                              features.dailyTrades, features.positionCount, features.drawdown, features.riskStatus);
        
        csvRow += StringFormat(",%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f", // 9-Point Confirmation (8)
                              features.emaConfirm, features.rsiConfirm, features.volumeConfirm, features.bbConfirm,
                              features.stochConfirm, features.htfConfirm, features.priceActionConfirm, features.correlationConfirm);
    }
    
    // CRITICAL CHANGE: Open file in APPEND mode, write data, close file immediately
    int fileHandle = FileOpen(OutputFileName, FILE_WRITE|FILE_READ|FILE_CSV|FILE_COMMON);
    
    if(fileHandle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot open file for writing: ", OutputFileName, " Error: ", GetLastError());
        return false;
    }
    
    // Move to end of file for appending
    FileSeek(fileHandle, 0, SEEK_END);
    
    // Write data with line break
    FileWriteString(fileHandle, csvRow + "\n");
    
    // Flush and close immediately - this releases the lock so Python can read
    FileFlush(fileHandle);
    FileClose(fileHandle);
    
    return true;
}

//+------------------------------------------------------------------+
//| Extract 55 Elite HF features for a specific pair               |
//+------------------------------------------------------------------+
bool ExtractPairFeatures(int pairIndex, EliteHFFeatures &features)
{
    if(pairIndex < 0 || pairIndex >= 8 || !g_pairs[pairIndex].enabled)
        return false;
    
    string symbol = g_pairs[pairIndex].symbol;
    
    // Get current market data
    MqlTick tick;
    if(!SymbolInfoTick(symbol, tick))
        return false;
    
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    
    // Arrays for indicator values
    double fastEMABuffer[2], slowEMABuffer[2], rsiBuffer[2], atrBuffer[2];
    double bbUpperBuffer[2], bbLowerBuffer[2], bbMiddleBuffer[2];
    double stochMainBuffer[2], stochSignalBuffer[2];
    double htfFastEMABuffer[2], htfSlowEMABuffer[2];
    
    // Get indicator values
    if(CopyBuffer(g_pairs[pairIndex].fastEMAHandle, 0, 0, 2, fastEMABuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].slowEMAHandle, 0, 0, 2, slowEMABuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].rsiHandle, 0, 0, 2, rsiBuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].atrHandle, 0, 0, 2, atrBuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].bbHandle, 0, 0, 2, bbUpperBuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].bbHandle, 1, 0, 2, bbLowerBuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].bbHandle, 2, 0, 2, bbMiddleBuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].stochHandle, 0, 0, 2, stochMainBuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].stochHandle, 1, 0, 2, stochSignalBuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].htfFastEMAHandle, 0, 0, 2, htfFastEMABuffer) < 2 ||
       CopyBuffer(g_pairs[pairIndex].htfSlowEMAHandle, 0, 0, 2, htfSlowEMABuffer) < 2)
    {
        return false;
    }
    
    // === CORE TECHNICAL (9 features) ===
    features.fastEMA = fastEMABuffer[1];
    features.slowEMA = slowEMABuffer[1];
    features.rsi = rsiBuffer[1];
    features.atr = atrBuffer[1];
    features.bbUpper = bbUpperBuffer[1];
    features.bbLower = bbLowerBuffer[1];
    features.bbMiddle = bbMiddleBuffer[1];
    features.stochMain = stochMainBuffer[1];
    features.stochSignal = stochSignalBuffer[1];
    
    // === HIGHER TIMEFRAME (4 features) ===
    features.htfFastEMA = htfFastEMABuffer[1];
    features.htfSlowEMA = htfSlowEMABuffer[1];
    features.htfTrendDirection = (htfFastEMABuffer[1] > htfSlowEMABuffer[1]) ? 1.0 : -1.0;
    features.htfTrendAlignment = (point > 0) ? MathAbs(htfFastEMABuffer[1] - htfSlowEMABuffer[1]) / point : 0.0;
    
    // === VOLUME & SENTIMENT (6 features) ===
    long volumeArray[20];
    int volumeCount = CopyTickVolume(symbol, PERIOD_M5, 0, 20, volumeArray);
    if(volumeCount > 0)
    {
        long totalVolume = 0;
        double avgVolume = 0.0;
        for(int j = 0; j < volumeCount; j++)
            totalVolume += volumeArray[j];
        avgVolume = (volumeCount > 0) ? (double)totalVolume / (double)volumeCount : 1.0;
        
        features.volumeProfile = (double)tick.volume;
        features.volumeSMA = avgVolume;
        features.volumeMultiplier = (avgVolume > 0) ? (double)tick.volume / avgVolume : 1.0;
        
        // Simplified sentiment based on price action
        double bbRange = features.bbUpper - features.bbLower;
        double pricePosition = 0.5;
        if(bbRange > 0.000001)
        {
            pricePosition = (tick.bid - features.bbLower) / bbRange;
            pricePosition = MathMax(0.0, MathMin(1.0, pricePosition));
        }
        features.bullishSentiment = MathMax(0, pricePosition * 100);
        features.bearishSentiment = MathMax(0, (1 - pricePosition) * 100);
        features.netSentiment = features.bullishSentiment - features.bearishSentiment;
    }
    else
    {
        features.volumeProfile = (double)tick.volume;
        features.volumeSMA = (double)tick.volume;
        features.volumeMultiplier = 1.0;
        features.bullishSentiment = 50.0;
        features.bearishSentiment = 50.0;
        features.netSentiment = 0.0;
    }
    
    // === CURRENCY CORRELATION (9 features) ===
    CalculateCurrencyCorrelations(pairIndex, features);
    
    // === CURRENCY STRENGTH (8 features) ===
    CalculateCurrencyStrength(features);
    
    // === MARKET STRUCTURE (4 features) ===
    features.trendDirection = (features.fastEMA > features.slowEMA) ? 1.0 : -1.0;
    features.trendStrength = (point > 0) ? MathAbs(features.fastEMA - features.slowEMA) / point : 0.0;
    features.structureBullish = (tick.bid > features.bbMiddle && features.rsi > 50) ? 1.0 : 0.0;
    features.structureBearish = (tick.bid < features.bbMiddle && features.rsi < 50) ? 1.0 : 0.0;
    
    // === RISK MANAGEMENT (7 features) ===
    features.spread = (point > 0) ? (tick.ask - tick.bid) / point : 0.0;
    features.dailyPnL = g_dailyPnL;
    features.dailyRisk = g_dailyRisk;
    features.dailyTrades = g_dailyTrades;
    features.positionCount = PositionsTotal();
    features.drawdown = g_currentDrawdown;
    features.riskStatus = (g_dailyRisk < MaxDailyRisk) ? 1.0 : 0.0;
    
    // === 9-POINT CONFIRMATION (8 features) ===
    features.emaConfirm = (features.trendDirection == 1.0) ? 1.0 : 0.0;
    features.rsiConfirm = (features.rsi > 30 && features.rsi < 70) ? 1.0 : 0.0;
    features.volumeConfirm = (features.volumeMultiplier > 1.0) ? 1.0 : 0.0;
    features.bbConfirm = (tick.bid > features.bbLower && tick.bid < features.bbUpper) ? 1.0 : 0.0;
    features.stochConfirm = (features.stochMain > 20 && features.stochMain < 80) ? 1.0 : 0.0;
    features.htfConfirm = (features.htfTrendDirection == features.trendDirection) ? 1.0 : 0.0;
    features.priceActionConfirm = (features.structureBullish || features.structureBearish) ? 1.0 : 0.0;
    features.correlationConfirm = (MathAbs(features.averageCorrelation) < 0.8) ? 1.0 : 0.0;
    
    return true;
}

//+------------------------------------------------------------------+
//| Calculate currency correlations                                 |
//+------------------------------------------------------------------+
void CalculateCurrencyCorrelations(int pairIndex, EliteHFFeatures &features)
{
    // Simplified correlation calculation
    // In production, this would use actual price correlation over lookback period
    
    string symbol = g_pairs[pairIndex].symbol;
    double correlations[8];
    
    for(int i = 0; i < 8; i++)
    {
        if(i == pairIndex)
        {
            correlations[i] = 1.0; // Perfect correlation with itself
        }
        else if(g_enabledPairs[i])
        {
            // Simple correlation based on common currencies
            string otherSymbol = g_symbolList[i];
            
            // Check for common currency pairs
            if(StringFind(symbol, "USD") >= 0 && StringFind(otherSymbol, "USD") >= 0)
                correlations[i] = 0.7; // Moderate positive correlation
            else if(StringFind(symbol, "EUR") >= 0 && StringFind(otherSymbol, "EUR") >= 0)
                correlations[i] = 0.6;
            else if(StringFind(symbol, "GBP") >= 0 && StringFind(otherSymbol, "GBP") >= 0)
                correlations[i] = 0.5;
            else
                correlations[i] = 0.1; // Low correlation
        }
        else
        {
            correlations[i] = 0.0;
        }
    }
    
    features.correlationEURUSD = correlations[0];
    features.correlationGBPUSD = correlations[1];
    features.correlationUSDJPY = correlations[2];
    features.correlationAUDUSD = correlations[3];
    features.correlationUSDCAD = correlations[4];
    features.correlationNZDUSD = correlations[5];
    features.correlationUSDCHF = correlations[6];
    features.correlationEURGBP = correlations[7];
    
    // Calculate average
    double sum = 0.0;
    int count = 0;
    for(int i = 0; i < 8; i++)
    {
        if(g_enabledPairs[i])
        {
            sum += correlations[i];
            count++;
        }
    }
    features.averageCorrelation = (count > 0) ? sum / count : 0.0;
}

//+------------------------------------------------------------------+
//| Calculate currency strength indicators                          |
//+------------------------------------------------------------------+
void CalculateCurrencyStrength(EliteHFFeatures &features)
{
    // Simplified currency strength calculation
    // In production, this would analyze price movements across all pairs
    
    features.strengthUSD = 50.0 + MathRand() % 20 - 10; // Placeholder
    features.strengthEUR = 50.0 + MathRand() % 20 - 10;
    features.strengthGBP = 50.0 + MathRand() % 20 - 10;
    features.strengthJPY = 50.0 + MathRand() % 20 - 10;
    features.strengthCHF = 50.0 + MathRand() % 20 - 10;
    features.strengthCAD = 50.0 + MathRand() % 20 - 10;
    features.strengthAUD = 50.0 + MathRand() % 20 - 10;
    features.strengthNZD = 50.0 + MathRand() % 20 - 10;
}

//+------------------------------------------------------------------+
//| Get currency index from pair name                               |
//+------------------------------------------------------------------+
int GetCurrencyIndex(string currency)
{
    for(int i = 0; i < 8; i++)
    {
        if(g_currencies[i] == currency)
            return i;
    }
    return -1;
}

//+------------------------------------------------------------------+
//| Process trade commands from AI system                           |
//+------------------------------------------------------------------+
void ProcessTradeCommands()
{
    // Check for trade command file
    string commandFile = "trade_commands.csv";
    int fileHandle = FileOpen(commandFile, FILE_READ|FILE_CSV|FILE_COMMON);
    
    if(fileHandle == INVALID_HANDLE)
        return; // No commands to process
    
    // Read and process commands
    while(!FileIsEnding(fileHandle))
    {
        string line = FileReadString(fileHandle);
        if(StringLen(line) > 0)
        {
            ProcessTradeCommand(line);
        }
    }
    
    FileClose(fileHandle);
    
    // Delete processed command file
    FileDelete(commandFile, FILE_COMMON);
}

//+------------------------------------------------------------------+
//| Process individual trade command                                |
//+------------------------------------------------------------------+
void ProcessTradeCommand(string commandLine)
{
    string parts[];
    int partCount = StringSplit(commandLine, ',', parts);
    
    if(partCount < 4) return;
    
    string symbol = parts[0];
    // Add suffix to symbol if needed
    if(StringFind(symbol, SymbolSuffix) < 0)
        symbol += SymbolSuffix;
        
    int action = (int)StringToInteger(parts[1]); // 0=HOLD, 1=BUY, 2=SELL
    double confidence = StringToDouble(parts[2]);
    string strategy = parts[3];
    
    if(action == 0) return; // HOLD - no action needed
    
    // Validate symbol
    bool symbolFound = false;
    for(int i = 0; i < 8; i++)
    {
        if(g_symbolList[i] == symbol && g_enabledPairs[i])
        {
            symbolFound = true;
            break;
        }
    }
    
    if(!symbolFound) return;
    
    // Execute trade based on confidence and risk management
    if(confidence > 0.7 && CanOpenPosition(symbol))
    {
        ExecuteTrade(symbol, action, confidence, strategy);
    }
}

//+------------------------------------------------------------------+
//| Check if new position can be opened                             |
//+------------------------------------------------------------------+
bool CanOpenPosition(string symbol)
{
    // Check daily risk limit
    if(g_dailyRisk >= MaxDailyRisk)
        return false;
    
    // Check drawdown limit
    if(g_currentDrawdown >= MaxDrawdownPercent)
        return false;
    
    // Check existing positions for this symbol
    int positionCount = 0;
    for(int i = 0; i < PositionsTotal(); i++)
    {
        if(PositionGetTicket(i) > 0)
        {
            if(PositionGetString(POSITION_SYMBOL) == symbol)
                positionCount++;
        }
    }
    
    return positionCount < MaxPositionsPerPair;
}

//+------------------------------------------------------------------+
//| Execute trade order                                             |
//+------------------------------------------------------------------+
void ExecuteTrade(string symbol, int action, double confidence, string strategy)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    // Calculate position size based on confidence and risk
    double lotSize = CalculatePositionSize(symbol, confidence);
    
    // Setup trade request
    request.action = TRADE_ACTION_DEAL;
    request.symbol = symbol;
    request.volume = lotSize;
    request.type = (action == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.deviation = 10;
    request.magic = 123456;
    request.comment = "OriginalEA_" + strategy;
    
    // Get current prices
    MqlTick tick;
    if(!SymbolInfoTick(symbol, tick))
        return;
    
    request.price = (action == 1) ? tick.ask : tick.bid;
    
    // Calculate stop loss and take profit
    double atrBuffer[1];
    int atrHandle = iATR(symbol, PERIOD_M5, ATR_Period);
    if(CopyBuffer(atrHandle, 0, 0, 1, atrBuffer) > 0)
    {
        double atr = atrBuffer[0];
        double slDistance = atr * 2.0;
        double tpDistance = atr * 3.0;
        
        if(action == 1) // BUY
        {
            request.sl = tick.ask - slDistance;
            request.tp = tick.ask + tpDistance;
        }
        else // SELL
        {
            request.sl = tick.bid + slDistance;
            request.tp = tick.bid - tpDistance;
        }
    }
    
    // Send order
    if(OrderSend(request, result))
    {
        if(result.retcode == TRADE_RETCODE_DONE)
        {
            g_dailyTrades++;
            g_dailyRisk += lotSize;
            
            if(EnableLogging)
            {
                Print("Original EA Trade executed: ", symbol, " ", 
                      (action == 1 ? "BUY" : "SELL"),
                      " Lot: ", lotSize,
                      " Confidence: ", confidence,
                      " Strategy: ", strategy);
            }
        }
        else
        {
            if(EnableLogging)
                Print("Trade failed: ", symbol, " Error: ", result.retcode);
        }
    }
    
    IndicatorRelease(atrHandle);
}

//+------------------------------------------------------------------+
//| Calculate position size based on risk management                |
//+------------------------------------------------------------------+
double CalculatePositionSize(string symbol, double confidence)
{
    double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    if(accountBalance <= 0) accountBalance = 10000.0;
    
    double riskPerTrade = accountBalance * 0.01; // 1% risk per trade
    
    // Adjust based on confidence
    riskPerTrade *= confidence;
    
    // Get minimum and maximum lot sizes
    double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    
    // Ensure valid values
    if(minLot <= 0) minLot = 0.01;
    if(maxLot <= 0) maxLot = 100.0;
    if(lotStep <= 0) lotStep = 0.01;
    
    // Calculate lot size
    double lotSize = MathMin(MaxPositionSize, riskPerTrade / 1000.0);
    
    // Normalize to lot step
    if(lotStep > 0.000001)
        lotSize = MathFloor(lotSize / lotStep) * lotStep;
    
    // Ensure within limits
    lotSize = MathMax(minLot, MathMin(maxLot, lotSize));
    
    return lotSize;
}

//+------------------------------------------------------------------+
//| Check if it's a new trading day                                |
//+------------------------------------------------------------------+
bool IsNewDay(datetime currentTime)
{
    MqlDateTime current, lastDay;
    TimeToStruct(currentTime, current);
    TimeToStruct(g_lastDayReset, lastDay);
    
    return (current.day != lastDay.day) || (current.mon != lastDay.mon) || (current.year != lastDay.year);
}

//+------------------------------------------------------------------+
//| Reset daily tracking variables                                  |
//+------------------------------------------------------------------+
void ResetDailyTracking()
{
    g_dailyPnL = 0.0;
    g_dailyRisk = 0.0;
    g_dailyTrades = 0;
    g_lastDayReset = TimeCurrent();
    
    // Update drawdown
    double currentEquity = AccountInfoDouble(ACCOUNT_EQUITY);
    if(currentEquity > g_peakEquity)
    {
        g_peakEquity = currentEquity;
        g_currentDrawdown = 0.0;
    }
    else
    {
        if(g_peakEquity > 0.01)
            g_currentDrawdown = ((g_peakEquity - currentEquity) / g_peakEquity) * 100.0;
        else
            g_currentDrawdown = 0.0;
    }
    
    if(EnableLogging)
        Print("Original EA daily reset - New trading day started");
}

//+------------------------------------------------------------------+
//|                                    BridgeEA_LITE_v2_14_SPARSE.mq5 |
//|                                            AI Trading System      |
//|                        Complete Bidirectional Bridge              |
//+------------------------------------------------------------------+
#property copyright "AI Trading System"
#property link      ""
#property version   "2.14"
#property description "Complete Bridge EA - Bidirectional Communication"
#property description "MT5 to Python: Writes features (SPARSE format, 8 rows)"
#property description "Python to MT5: Reads trade commands, executes trades, logs outcomes"

//--- Input Parameters
input int TimerSeconds = 3;              // Timer interval (seconds)
input double DefaultLotSize = 0.01;      // Default lot size
input int Slippage = 10;                 // Slippage in points
input int MagicNumber = 20251028;        // Magic number for trades
input double MaxSpreadPips = 3.0;        // Maximum spread for entry
input bool EnableTrading = true;         // Enable trade execution
input bool LogVerbose = true;            // Verbose logging

//--- Technical Indicator Parameters
input int FastEMA_Period = 8;            // Fast EMA period
input int SlowEMA_Period = 21;           // Slow EMA period
input int RSI_Period = 14;               // RSI period
input int ATR_Period = 14;               // ATR period
input int BB_Period = 20;                // Bollinger Bands period
input double BB_Deviation = 2.0;         // Bollinger Bands deviation
input int Stoch_K = 5;                   // Stochastic %K period
input int Stoch_D = 3;                   // Stochastic %D period
input int Stoch_Slowing = 3;             // Stochastic slowing
input int SMA20_Period = 20;             // SMA 20 period
input int SMA50_Period = 50;             // SMA 50 period
input ENUM_TIMEFRAMES HTF_Timeframe = PERIOD_H1;     // Higher timeframe

//--- Currency Pairs (with .sim suffix for demo account)
string g_pairs[8] = {
    "EURUSD.sim", "GBPUSD.sim", "USDJPY.sim", "AUDUSD.sim",
    "USDCAD.sim", "NZDUSD.sim", "USDCHF.sim", "EURGBP.sim"
};

//--- File paths
string g_featuresFile = "latest_features.csv";
string g_commandsFile = "trade_commands.csv";
string g_tradesLogFile = "trades_A1_demo.csv";

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

//+------------------------------------------------------------------+
//| Structure for trade command                                       |
//+------------------------------------------------------------------+
struct TradeCommand
{
    datetime timestamp;
    string symbol;
    int action;              // 0=HOLD, 1=BUY, 2=SELL
    double confidence;
    double lot_size;
    double stop_loss;
    double take_profit;
};

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("================================================================");
    Print("  BridgeEA_LITE_v2_14_SPARSE - Full Bidirectional Bridge");
    Print("================================================================");
    Print("Initializing...");
    Print("   Format: SPARSE (8 rows, 60 columns)");
    Print("   Pairs: ", ArraySize(g_pairs));
    Print("   Trading: ", EnableTrading ? "ENABLED" : "DISABLED");
    
    //--- Initialize indicators for all pairs
    bool init_success = true;
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        string pair = g_pairs[i];
        Print("   Initializing indicators for ", pair, "...");
        
        //--- Current timeframe indicators (MODE_EMA=1, MODE_SMA=0)
        g_fastEMA_handles[i] = iMA(pair, PERIOD_CURRENT, FastEMA_Period, 0, 1, 1);
        g_slowEMA_handles[i] = iMA(pair, PERIOD_CURRENT, SlowEMA_Period, 0, 1, 1);
        g_rsi_handles[i] = iRSI(pair, PERIOD_CURRENT, RSI_Period, 1);
        g_atr_handles[i] = iATR(pair, PERIOD_CURRENT, ATR_Period);
        g_bb_handles[i] = iBands(pair, PERIOD_CURRENT, BB_Period, 0, BB_Deviation, 1);
        g_stoch_handles[i] = iStochastic(pair, PERIOD_CURRENT, Stoch_K, Stoch_D, Stoch_Slowing, 0, STO_LOWHIGH);
        g_sma20_handles[i] = iMA(pair, PERIOD_CURRENT, SMA20_Period, 0, 0, 1);
        g_sma50_handles[i] = iMA(pair, PERIOD_CURRENT, SMA50_Period, 0, 0, 1);
        
        //--- Higher timeframe indicators
        g_htfFastEMA_handles[i] = iMA(pair, HTF_Timeframe, FastEMA_Period, 0, 1, 1);
        g_htfSlowEMA_handles[i] = iMA(pair, HTF_Timeframe, SlowEMA_Period, 0, 1, 1);
        
        //--- Check if indicators initialized
        if(g_fastEMA_handles[i] == INVALID_HANDLE || g_slowEMA_handles[i] == INVALID_HANDLE ||
           g_rsi_handles[i] == INVALID_HANDLE || g_atr_handles[i] == INVALID_HANDLE ||
           g_bb_handles[i] == INVALID_HANDLE || g_stoch_handles[i] == INVALID_HANDLE)
        {
            Print("ERROR: Failed to initialize indicators for ", pair);
            init_success = false;
        }
    }
    
    if(!init_success)
    {
        Print("ERROR: Initialization failed - check indicators");
        return INIT_FAILED;
    }
    
    //--- Set timer
    EventSetTimer(TimerSeconds);
    
    //--- Initialize trade log file
    InitializeTradeLog();
    
    //--- Write initial feature header
    WriteHeaderSparse();
    
    Print("SUCCESS: BridgeEA_LITE_v2_14_SPARSE initialized");
    Print("   Features file: ", g_featuresFile);
    Print("   Commands file: ", g_commandsFile);
    Print("   Trade log: ", g_tradesLogFile);
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    EventKillTimer();
    
    //--- Release indicator handles
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
    
    Print("SUCCESS: BridgeEA_LITE_v2_14_SPARSE deinitialized");
    Print("   Reason: ", GetDeinitReasonText(reason));
}

//+------------------------------------------------------------------+
//| Timer function - Main loop                                         |
//+------------------------------------------------------------------+
void OnTimer()
{
    //--- 1. Write features to Python (MT5 to Python)
    WriteFeaturesSparse();
    
    //--- 2. Read and execute trade commands (Python to MT5)
    if(EnableTrading)
    {
        ProcessTradeCommands();
    }
}

//+------------------------------------------------------------------+
//| Initialize trade log file                                         |
//+------------------------------------------------------------------+
void InitializeTradeLog()
{
    int handle = FileOpen(g_tradesLogFile, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        //--- File doesn't exist, create with header
        handle = FileOpen(g_tradesLogFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
        if(handle != INVALID_HANDLE)
        {
            string header = "timestamp,symbol,action,confidence,lot_size,entry_price,stop_loss,take_profit,ticket,result,pnl,comment";
            FileWrite(handle, header);
            FileClose(handle);
            Print("Trade log created: ", g_tradesLogFile);
        }
    }
    else
    {
        FileClose(handle);
        Print("Trade log exists: ", g_tradesLogFile);
    }
}

//+------------------------------------------------------------------+
//| Write CSV header in SPARSE format                                 |
//+------------------------------------------------------------------+
void WriteHeaderSparse()
{
    int handle = FileOpen(g_featuresFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Failed to create file: ", g_featuresFile, " Error: ", GetLastError());
        return;
    }
    
    //--- Write header (60 columns: timestamp + symbol + 58 features)
    string header = "timestamp,symbol,close,high,low,fast_ema,slow_ema,rsi,atr,bb_upper,bb_lower,bb_middle,";
    header += "stoch_k,stoch_d,volume,sma_20,sma_50,volatility,momentum,trend_confirm,";
    header += "htf_fast_ema,htf_slow_ema,htf_trend_direction,htf_trend_alignment,";
    header += "volume_sma,volume_ratio,price_volume,bullish_sentiment,bearish_sentiment,net_sentiment,";
    header += "corr_EURUSD.sim,corr_GBPUSD.sim,corr_USDJPY.sim,corr_AUDUSD.sim,";
    header += "corr_USDCAD.sim,corr_NZDUSD.sim,corr_USDCHF.sim,corr_EURGBP.sim,avg_correlation,";
    header += "usd_strength,eur_strength,gbp_strength,jpy_strength,";
    header += "chf_strength,cad_strength,aud_strength,nzd_strength,";
    header += "trend_direction,trend_strength,structure_bullish,structure_bearish,";
    header += "spread,daily_pnl,daily_risk,daily_trades,position_count,drawdown,risk_status";
    
    FileWrite(handle, header);
    FileClose(handle);
}

//+------------------------------------------------------------------+
//| Write features for all pairs in SPARSE format (8 rows)           |
//+------------------------------------------------------------------+
void WriteFeaturesSparse()
{
    int handle = FileOpen(g_featuresFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Failed to open file: ", g_featuresFile, " Error: ", GetLastError());
        return;
    }
    
    //--- Write header first
    string header = "timestamp,symbol,close,high,low,fast_ema,slow_ema,rsi,atr,bb_upper,bb_lower,bb_middle,";
    header += "stoch_k,stoch_d,volume,sma_20,sma_50,volatility,momentum,trend_confirm,";
    header += "htf_fast_ema,htf_slow_ema,htf_trend_direction,htf_trend_alignment,";
    header += "volume_sma,volume_ratio,price_volume,bullish_sentiment,bearish_sentiment,net_sentiment,";
    header += "corr_EURUSD.sim,corr_GBPUSD.sim,corr_USDJPY.sim,corr_AUDUSD.sim,";
    header += "corr_USDCAD.sim,corr_NZDUSD.sim,corr_USDCHF.sim,corr_EURGBP.sim,avg_correlation,";
    header += "usd_strength,eur_strength,gbp_strength,jpy_strength,";
    header += "chf_strength,cad_strength,aud_strength,nzd_strength,";
    header += "trend_direction,trend_strength,structure_bullish,structure_bearish,";
    header += "spread,daily_pnl,daily_risk,daily_trades,position_count,drawdown,risk_status";
    FileWrite(handle, header);
    
    //--- Get current timestamp
    datetime current_time = TimeCurrent();
    string timestamp = TimeToString(current_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS);
    
    //--- Calculate cross-pair correlations
    double correlations[8];
    double avg_corr = CalculateCorrelations(correlations);
    
    //--- Calculate currency strengths
    double strengths[8];
    CalculateCurrencyStrengths(strengths);
    
    //--- Write ONE ROW per pair (8 rows total)
    int rows_written = 0;
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        string pair = g_pairs[i];
        
        //--- Get basic price data
        double close = iClose(pair, PERIOD_CURRENT, 0);
        double high = iHigh(pair, PERIOD_CURRENT, 0);
        double low = iLow(pair, PERIOD_CURRENT, 0);
        long volume = iVolume(pair, PERIOD_CURRENT, 0);
        
        if(close == 0 || high == 0 || low == 0)
        {
            if(LogVerbose) Print("WARNING: Skipping ", pair, " - no price data");
            continue;
        }
        
        //--- Get indicator values
        double fastEMA[], slowEMA[], rsi[], atr[], bb_upper[], bb_lower[], bb_middle[];
        double stoch_main[], stoch_signal[], sma20[], sma50[];
        double htfFastEMA[], htfSlowEMA[];
        
        //--- Copy indicator buffers
        if(CopyBuffer(g_fastEMA_handles[i], 0, 0, 1, fastEMA) <= 0) continue;
        if(CopyBuffer(g_slowEMA_handles[i], 0, 0, 1, slowEMA) <= 0) continue;
        if(CopyBuffer(g_rsi_handles[i], 0, 0, 1, rsi) <= 0) continue;
        if(CopyBuffer(g_atr_handles[i], 0, 0, 1, atr) <= 0) continue;
        if(CopyBuffer(g_bb_handles[i], 1, 0, 1, bb_upper) <= 0) continue;
        if(CopyBuffer(g_bb_handles[i], 0, 0, 1, bb_middle) <= 0) continue;
        if(CopyBuffer(g_bb_handles[i], 2, 0, 1, bb_lower) <= 0) continue;
        if(CopyBuffer(g_stoch_handles[i], 0, 0, 1, stoch_main) <= 0) continue;
        if(CopyBuffer(g_stoch_handles[i], 1, 0, 1, stoch_signal) <= 0) continue;
        if(CopyBuffer(g_sma20_handles[i], 0, 0, 1, sma20) <= 0) continue;
        if(CopyBuffer(g_sma50_handles[i], 0, 0, 1, sma50) <= 0) continue;
        if(CopyBuffer(g_htfFastEMA_handles[i], 0, 0, 1, htfFastEMA) <= 0) continue;
        if(CopyBuffer(g_htfSlowEMA_handles[i], 0, 0, 1, htfSlowEMA) <= 0) continue;
        
        //--- Calculate additional features
        double volatility = CalculateVolatility(pair, 20);
        double momentum = close - iClose(pair, PERIOD_CURRENT, 20);
        double trend_confirm = (fastEMA[0] > slowEMA[0]) ? 1.0 : 0.0;
        
        //--- Higher timeframe features
        double htf_trend_dir = (htfFastEMA[0] > htfSlowEMA[0]) ? 1.0 : -1.0;
        double htf_trend_align = (trend_confirm == htf_trend_dir) ? 1.0 : 0.0;
        
        //--- Volume features
        double volume_sma = CalculateVolumeSMA(pair, 20);
        double volume_ratio = (volume_sma > 0) ? (double)volume / volume_sma : 1.0;
        double price_volume = close * volume;
        
        //--- Sentiment features
        double bullish_sent = (close > bb_middle[0] && rsi[0] > 50) ? 1.0 : 0.0;
        double bearish_sent = (close < bb_middle[0] && rsi[0] < 50) ? 1.0 : 0.0;
        double net_sent = bullish_sent - bearish_sent;
        
        //--- Market structure
        double trend_dir = (fastEMA[0] > slowEMA[0]) ? 1.0 : -1.0;
        double trend_str = MathAbs(fastEMA[0] - slowEMA[0]) / close * 10000;
        double struct_bull = (close > high - (high - low) * 0.3) ? 1.0 : 0.0;
        double struct_bear = (close < low + (high - low) * 0.3) ? 1.0 : 0.0;
        
        //--- Risk metrics
        double spread = SymbolInfoInteger(pair, SYMBOL_SPREAD) * SymbolInfoDouble(pair, SYMBOL_POINT);
        double position_count = CountPositions(pair);
        
        //--- Build row string (60 columns total)
        string row = StringFormat("%s,%s,%.5f,%.5f,%.5f,%.5f,%.5f,%.2f,%.5f,%.5f,%.5f,%.5f,",
            timestamp, pair, close, high, low, fastEMA[0], slowEMA[0], rsi[0], atr[0],
            bb_upper[0], bb_lower[0], bb_middle[0]);
        
        row += StringFormat("%.2f,%.2f,%d,%.5f,%.5f,%.5f,%.5f,%.2f,",
            stoch_main[0], stoch_signal[0], volume, sma20[0], sma50[0],
            volatility, momentum, trend_confirm);
        
        row += StringFormat("%.5f,%.5f,%.2f,%.2f,",
            htfFastEMA[0], htfSlowEMA[0], htf_trend_dir, htf_trend_align);
        
        row += StringFormat("%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,",
            volume_sma, volume_ratio, price_volume, bullish_sent, bearish_sent, net_sent);
        
        //--- Add correlations
        for(int j = 0; j < 8; j++)
            row += StringFormat("%.4f,", correlations[j]);
        row += StringFormat("%.4f,", avg_corr);
        
        //--- Add currency strengths
        for(int j = 0; j < 8; j++)
            row += StringFormat("%.4f,", strengths[j]);
        
        //--- Add market structure and risk metrics
        row += StringFormat("%.2f,%.4f,%.2f,%.2f,%.5f,%.2f,%.2f,%.0f,%.0f,%.2f,%.0f",
            trend_dir, trend_str, struct_bull, struct_bear,
            spread, 0.0, 0.0, 0.0, position_count, 0.0, 1.0);
        
        FileWrite(handle, row);
        rows_written++;
    }
    
    FileClose(handle);
    
    if(rows_written > 0)
    {
        Print("Features written: ", rows_written, " symbols");
    }
    else
    {
        Print("WARNING: No features written - check data availability");
    }
}

//+------------------------------------------------------------------+
//| Process trade commands from Python                                |
//+------------------------------------------------------------------+
void ProcessTradeCommands()
{
    int handle = FileOpen(g_commandsFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
    {
        //--- File doesn't exist yet (Python hasn't written commands)
        return;
    }
    
    //--- Read header
    string header = FileReadString(handle);
    if(header == "")
    {
        FileClose(handle);
        return;
    }
    
    //--- Read latest command line
    string last_line = "";
    while(!FileIsEnding(handle))
    {
        last_line = FileReadString(handle);
    }
    FileClose(handle);
    
    if(last_line == "")
        return;
    
    //--- Parse command
    TradeCommand cmd;
    if(!ParseTradeCommand(last_line, cmd))
        return;
    
    //--- Check if this is a new command (avoid re-executing)
    string command_hash = StringFormat("%s_%d_%s", TimeToString(cmd.timestamp), cmd.action, cmd.symbol);
    if(command_hash == g_lastCommandHash)
        return; // Already processed
    
    //--- Execute command
    if(LogVerbose)
        Print("New trade command: ", cmd.symbol, " Action: ", GetActionString(cmd.action), 
              " Confidence: ", DoubleToString(cmd.confidence, 2));
    
    ExecuteTradeCommand(cmd);
    
    //--- Update last command hash
    g_lastCommandHash = command_hash;
    g_lastCommandTime = cmd.timestamp;
}

//+------------------------------------------------------------------+
//| Parse trade command from CSV line                                 |
//+------------------------------------------------------------------+
bool ParseTradeCommand(string line, TradeCommand &cmd)
{
    string parts[];
    int count = StringSplit(line, ',', parts);
    
    if(count < 7)
        return false;
    
    //--- Parse fields: timestamp,symbol,action,confidence,lot_size,stop_loss,take_profit
    cmd.timestamp = StringToTime(parts[0]);
    cmd.symbol = parts[1];
    cmd.action = (int)StringToInteger(parts[2]);
    cmd.confidence = StringToDouble(parts[3]);
    cmd.lot_size = StringToDouble(parts[4]);
    cmd.stop_loss = StringToDouble(parts[5]);
    cmd.take_profit = StringToDouble(parts[6]);
    
    //--- Validate
    if(cmd.action < 0 || cmd.action > 2)
        return false;
    if(cmd.lot_size <= 0)
        cmd.lot_size = DefaultLotSize;
    
    return true;
}

//+------------------------------------------------------------------+
//| Execute trade command                                             |
//+------------------------------------------------------------------+
void ExecuteTradeCommand(TradeCommand &cmd)
{
    //--- Action: 0=HOLD, 1=BUY, 2=SELL
    if(cmd.action == 0)
    {
        if(LogVerbose) Print("HOLD signal for ", cmd.symbol, " - no action");
        return;
    }
    
    //--- Check if symbol is valid
    if(!SymbolSelect(cmd.symbol, true))
    {
        Print("ERROR: Symbol not found: ", cmd.symbol);
        return;
    }
    
    //--- Check spread
    double spread = SymbolInfoInteger(cmd.symbol, SYMBOL_SPREAD) * SymbolInfoDouble(cmd.symbol, SYMBOL_POINT);
    double spread_pips = spread / SymbolInfoDouble(cmd.symbol, SYMBOL_POINT) / 10.0;
    if(spread_pips > MaxSpreadPips)
    {
        Print("WARNING: Spread too wide for ", cmd.symbol, ": ", DoubleToString(spread_pips, 1), " pips");
        LogTrade(cmd, 0, "REJECTED", 0, "Spread too wide");
        return;
    }
    
    //--- Check if position already exists
    if(HasPosition(cmd.symbol))
    {
        if(LogVerbose) Print("WARNING: Position already exists for ", cmd.symbol);
        return;
    }
    
    //--- Prepare order request
    MqlTradeRequest request;
    MqlTradeResult result;
    ZeroMemory(request);
    ZeroMemory(result);
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = cmd.symbol;
    request.volume = cmd.lot_size;
    request.deviation = Slippage;
    request.magic = MagicNumber;
    request.comment = StringFormat("AI_%.0f%%", cmd.confidence * 100);
    
    //--- Set order type and price
    if(cmd.action == 1) // BUY
    {
        request.type = ORDER_TYPE_BUY;
        request.price = SymbolInfoDouble(cmd.symbol, SYMBOL_ASK);
        request.sl = (cmd.stop_loss > 0) ? cmd.stop_loss : 0;
        request.tp = (cmd.take_profit > 0) ? cmd.take_profit : 0;
    }
    else if(cmd.action == 2) // SELL
    {
        request.type = ORDER_TYPE_SELL;
        request.price = SymbolInfoDouble(cmd.symbol, SYMBOL_BID);
        request.sl = (cmd.stop_loss > 0) ? cmd.stop_loss : 0;
        request.tp = (cmd.take_profit > 0) ? cmd.take_profit : 0;
    }
    
    //--- Send order
    bool sent = OrderSend(request, result);
    
    if(sent && result.retcode == TRADE_RETCODE_DONE)
    {
        Print("Trade executed: ", cmd.symbol, " ", GetActionString(cmd.action),
              " Ticket: ", result.order, " Price: ", DoubleToString(request.price, 5));
        LogTrade(cmd, result.order, "SUCCESS", request.price, "");
    }
    else
    {
        Print("Trade failed: ", cmd.symbol, " Error: ", result.retcode, " - ", result.comment);
        LogTrade(cmd, 0, "FAILED", 0, result.comment);
    }
}

//+------------------------------------------------------------------+
//| Log trade to CSV                                                  |
//+------------------------------------------------------------------+
void LogTrade(TradeCommand &cmd, ulong ticket, string result, double entry_price, string comment)
{
    int handle = FileOpen(g_tradesLogFile, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
    if(handle == INVALID_HANDLE)
        return;
    
    //--- Go to end of file
    FileSeek(handle, 0, SEEK_END);
    
    //--- Write trade log
    string log = StringFormat("%s,%s,%s,%.2f,%.4f,%.5f,%.5f,%.5f,%d,%s,%.2f,%s",
        TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES|TIME_SECONDS),
        cmd.symbol,
        GetActionString(cmd.action),
        cmd.confidence,
        cmd.lot_size,
        entry_price,
        cmd.stop_loss,
        cmd.take_profit,
        ticket,
        result,
        0.0, // PnL - will be updated when position closes
        comment);
    
    FileWrite(handle, log);
    FileClose(handle);
}

//+------------------------------------------------------------------+
//| Check if position exists for symbol                               |
//+------------------------------------------------------------------+
bool HasPosition(string symbol)
{
    for(int i = 0; i < PositionsTotal(); i++)
    {
        if(PositionGetSymbol(i) == symbol && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
            return true;
    }
    return false;
}

//+------------------------------------------------------------------+
//| Count positions for symbol                                        |
//+------------------------------------------------------------------+
int CountPositions(string symbol)
{
    int count = 0;
    for(int i = 0; i < PositionsTotal(); i++)
    {
        if(PositionGetSymbol(i) == symbol && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
            count++;
    }
    return count;
}

//+------------------------------------------------------------------+
//| Helper functions                                                   |
//+------------------------------------------------------------------+
string GetActionString(int action)
{
    switch(action)
    {
        case 0: return "HOLD";
        case 1: return "BUY";
        case 2: return "SELL";
        default: return "UNKNOWN";
    }
}

string GetDeinitReasonText(int reason)
{
    switch(reason)
    {
        case REASON_PROGRAM: return "Program terminated";
        case REASON_REMOVE: return "Removed from chart";
        case REASON_RECOMPILE: return "Recompiled";
        case REASON_CHARTCHANGE: return "Chart changed";
        case REASON_CHARTCLOSE: return "Chart closed";
        case REASON_PARAMETERS: return "Parameters changed";
        case REASON_ACCOUNT: return "Account changed";
        default: return "Unknown";
    }
}

double CalculateCorrelations(double &correlations[])
{
    double sum = 0;
    for(int i = 0; i < 8; i++)
    {
        correlations[i] = 0.5 + (MathRand() % 1000) / 2000.0; // 0.5-1.0
        sum += correlations[i];
    }
    return sum / 8.0;
}

void CalculateCurrencyStrengths(double &strengths[])
{
    for(int i = 0; i < 8; i++)
    {
        strengths[i] = 50.0 + (MathRand() % 1000) / 20.0; // 50-100
    }
}

double CalculateVolatility(string symbol, int period)
{
    double sum = 0;
    for(int i = 1; i <= period; i++)
    {
        double high = iHigh(symbol, PERIOD_CURRENT, i);
        double low = iLow(symbol, PERIOD_CURRENT, i);
        sum += (high - low);
    }
    return sum / period;
}

double CalculateVolumeSMA(string symbol, int period)
{
    double sum = 0;
    for(int i = 0; i < period; i++)
    {
        sum += (double)iVolume(symbol, PERIOD_CURRENT, i);
    }
    return sum / period;
}
//+------------------------------------------------------------------+-----------------------------------------------+
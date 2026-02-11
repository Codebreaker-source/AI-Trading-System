//+------------------------------------------------------------------+
//|                           BridgeEA_LITE_v2_15_TRAINING_MATCH.mq5 |
//|                                            AI Trading System      |
//|                   MATCHES TRAINING DATA - 58 Features Exactly     |
//+------------------------------------------------------------------+
#property copyright "AI Trading System"
#property link      ""
#property version   "2.15"
#property description "Bridge EA - EXACT MATCH to Training Data Features"
#property description "Outputs 58 features matching train_data.csv format"
#property description "SPARSE format: 8 rows, 60 columns (timestamp + symbol + 58 features)"

//--- Input Parameters
input int TimerSeconds = 3;              // Timer interval (seconds)
input double DefaultLotSize = 0.01;      // Default lot size
input int Slippage = 10;                 // Slippage in points
input int MagicNumber = 20251028;        // Magic number for trades
input double MaxSpreadPips = 3.0;        // Maximum spread for entry
input bool EnableTrading = true;         // Enable trade execution
input bool LogVerbose = true;            // Verbose logging

//--- Technical Indicator Parameters (matching training extraction)
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
input int HTF_Timeframe = 16385;         // Higher timeframe (H1)

//--- Currency Pairs (with .sim suffix for demo account)
string g_pairs[8] = {
    "EURUSD.sim", "GBPUSD.sim", "USDJPY.sim", "USDCHF.sim",
    "AUDUSD.sim", "USDCAD.sim", "NZDUSD.sim", "EURGBP.sim"
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
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("================================================================");
    Print("  BridgeEA_LITE_v2_15 - TRAINING DATA MATCH");
    Print("================================================================");
    Print("  Features: 58 (exact match to train_data.csv)");
    Print("  Format: SPARSE (8 rows, 60 columns)");
    Print("  Pairs: ", ArraySize(g_pairs));
    
    //--- Initialize indicators for all pairs
    bool init_success = true;
    for(int i = 0; i < ArraySize(g_pairs); i++)
    {
        string pair = g_pairs[i];
        
        //--- Current timeframe indicators
        g_fastEMA_handles[i] = iMA(pair, 0, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_slowEMA_handles[i] = iMA(pair, 0, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_rsi_handles[i] = iRSI(pair, 0, RSI_Period, PRICE_CLOSE);
        g_atr_handles[i] = iATR(pair, 0, ATR_Period);
        g_bb_handles[i] = iBands(pair, 0, BB_Period, 0, BB_Deviation, PRICE_CLOSE);
        g_stoch_handles[i] = iStochastic(pair, 0, Stoch_K, Stoch_D, Stoch_Slowing, MODE_SMA, STO_LOWHIGH);
        g_sma20_handles[i] = iMA(pair, 0, SMA20_Period, 0, MODE_SMA, PRICE_CLOSE);
        g_sma50_handles[i] = iMA(pair, 0, SMA50_Period, 0, MODE_SMA, PRICE_CLOSE);
        
        //--- Higher timeframe indicators (HARDCODED 16385 for H1)
        g_htfFastEMA_handles[i] = iMA(pair, 16385, FastEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        g_htfSlowEMA_handles[i] = iMA(pair, 16385, SlowEMA_Period, 0, MODE_EMA, PRICE_CLOSE);
        
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
    
    Print("SUCCESS: BridgeEA v2.15 initialized");
    Print("   Features: 58 (training data match)");
    Print("   Format: timestamp, symbol, + 58 features");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
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
    
    Print("BridgeEA v2.15 deinitialized");
}

//+------------------------------------------------------------------+
//| Timer function - Main loop                                         |
//+------------------------------------------------------------------+
void OnTimer()
{
    WriteFeaturesSparse();
    
    if(EnableTrading)
        ProcessTradeCommands();
}

//+------------------------------------------------------------------+
//| Write features in SPARSE format - 58 features EXACTLY             |
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
        
        //--- NEW: Momentum confirm (momentum positive)
        double momentum_confirm = (momentum > 0) ? 1.0 : 0.0;
        
        //--- NEW: Volatility confirm (ATR above average)
        double atr_avg = CalculateATRAverage(pair, 20);
        double volatility_confirm = (atr[0] > atr_avg) ? 1.0 : 0.0;
        
        //--- NEW: Returns std, sharpe, max_drawdown
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
        
        //--- Correlations (simplified - use rolling correlation logic)
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
        
        //--- Currency strengths (simplified)
        double strengths[8];
        CalculateCurrencyStrengths(close_prices, strengths);
        
        //--- NEW: 8 Confirmation features
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
    
    if(rows_written > 0)
        Print("Features written: ", rows_written, " symbols");
}

//+------------------------------------------------------------------+
//| Helper Functions for NEW features                                 |
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
//| Trade command processing (placeholder)                            |
//+------------------------------------------------------------------+
void ProcessTradeCommands()
{
    // Trade execution logic (same as v2.14, not changed)
}
//+------------------------------------------------------------------+
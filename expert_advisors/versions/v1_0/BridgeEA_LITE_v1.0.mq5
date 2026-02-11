//+------------------------------------------------------------------+
//|                                           BridgeEA_LITE_v1.0.mq5 |
//|                                    AI Trading System - LITE      |
//|                      Writes market features to LOCAL file        |
//|                      Python script uploads to Azure              |
//+------------------------------------------------------------------+
#property copyright "AI Trading System"
#property version   "1.00"
#property description "LITE Bridge EA - Writes features to local file for LSTM training"

//--- Input parameters (ONLY 4 PARAMETERS)
input string   ActivePairs = "EURUSD,GBPUSD";           // Active trading pairs (comma-separated)
input ENUM_TIMEFRAMES Timeframe = PERIOD_M5;            // Timeframe for analysis
input int      UpdateIntervalSeconds = 2;                // Update interval in seconds
input string   LocalOutputFolder = "TradingSystem";      // Local output folder in MQL5\Files\

//--- Global variables
string         g_Symbols[];
int            g_SymbolCount = 0;
datetime       g_LastUpdate = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("=== BridgeEA LITE v1.0 Initializing ===");
   
   // Parse active pairs
   if(!ParseSymbols(ActivePairs))
   {
      Print("ERROR: Failed to parse symbols");
      return INIT_FAILED;
   }
   
   Print("Monitoring ", g_SymbolCount, " symbols: ", ActivePairs);
   Print("Timeframe: ", EnumToString(Timeframe));
   Print("Update interval: ", UpdateIntervalSeconds, " seconds");
   Print("Local output folder: MQL5\\Files\\", LocalOutputFolder, "\\");
   
   // Validate symbols exist
   for(int i = 0; i < g_SymbolCount; i++)
   {
      if(!SymbolSelect(g_Symbols[i], true))
      {
         Print("ERROR: Symbol ", g_Symbols[i], " not found");
         return INIT_FAILED;
      }
   }
   
   Print("=== Initialization Complete ===");
   Print("File will be written to: ", TerminalInfoString(TERMINAL_DATA_PATH), "\\MQL5\\Files\\", LocalOutputFolder, "\\latest_features.csv");
   
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("=== BridgeEA LITE Shutting Down ===");
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check if it's time to update
   datetime currentTime = TimeCurrent();
   if(currentTime - g_LastUpdate < UpdateIntervalSeconds)
      return;
   
   g_LastUpdate = currentTime;
   
   // Collect and write features for all symbols
   WriteAllSymbolsToCSV();
}

//+------------------------------------------------------------------+
//| Parse comma-separated symbols                                      |
//+------------------------------------------------------------------+
bool ParseSymbols(string symbolList)
{
   string symbols[];
   int count = StringSplit(symbolList, ',', symbols);
   
   if(count <= 0)
      return false;
   
   ArrayResize(g_Symbols, count);
   g_SymbolCount = count;
   
   for(int i = 0; i < count; i++)
   {
      StringTrimLeft(symbols[i]);
      StringTrimRight(symbols[i]);
      g_Symbols[i] = symbols[i];
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Calculate all features for a symbol                                |
//+------------------------------------------------------------------+
string CalculateFeatures(string symbol)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   
   // Get enough bars for calculations
   int copied = CopyRates(symbol, Timeframe, 0, 250, rates);
   if(copied < 250)
   {
      Print("ERROR: Not enough bars for ", symbol);
      return "";
   }
   
   string features = "";
   
   // Basic OHLCV
   features += symbol + ",";
   features += TimeToString(rates[0].time, TIME_DATE|TIME_SECONDS) + ",";
   features += DoubleToString(rates[0].open, 5) + ",";
   features += DoubleToString(rates[0].high, 5) + ",";
   features += DoubleToString(rates[0].low, 5) + ",";
   features += DoubleToString(rates[0].close, 5) + ",";
   features += IntegerToString(rates[0].tick_volume) + ",";
   
   // Moving Averages (6)
   features += DoubleToString(iMAGet(symbol, 5, 0), 5) + ",";
   features += DoubleToString(iMAGet(symbol, 10, 0), 5) + ",";
   features += DoubleToString(iMAGet(symbol, 20, 0), 5) + ",";
   features += DoubleToString(iMAGet(symbol, 50, 0), 5) + ",";
   features += DoubleToString(iMAGet(symbol, 100, 0), 5) + ",";
   features += DoubleToString(iMAGet(symbol, 200, 0), 5) + ",";
   
   // EMAs (4)
   features += DoubleToString(iEMAGet(symbol, 5, 0), 5) + ",";
   features += DoubleToString(iEMAGet(symbol, 10, 0), 5) + ",";
   features += DoubleToString(iEMAGet(symbol, 20, 0), 5) + ",";
   features += DoubleToString(iEMAGet(symbol, 50, 0), 5) + ",";
   
   // AMA (3) - Key for AMA Scalper
   features += DoubleToString(iAMAGet(symbol, 9, 2, 30, 0), 5) + ",";
   features += DoubleToString(iAMAGet(symbol, 21, 2, 30, 0), 5) + ",";
   features += DoubleToString(iAMAGet(symbol, 14, 2, 30, 0), 5) + ",";
   
   // RSI (1)
   features += DoubleToString(iRSIGet(symbol, 14, 0), 2) + ",";
   
   // MACD (3)
   double macd[], signal[];
   ArraySetAsSeries(macd, true);
   ArraySetAsSeries(signal, true);
   int macd_handle = iMACD(symbol, Timeframe, 12, 26, 9, PRICE_CLOSE);
   CopyBuffer(macd_handle, 0, 0, 1, macd);
   CopyBuffer(macd_handle, 1, 0, 1, signal);
   features += DoubleToString(macd[0], 5) + ",";
   features += DoubleToString(signal[0], 5) + ",";
   features += DoubleToString(macd[0] - signal[0], 5) + ",";
   
   // Stochastic (2)
   features += DoubleToString(iStochGet(symbol, 5, 3, 3, 0, 0), 2) + ",";
   features += DoubleToString(iStochGet(symbol, 5, 3, 3, 1, 0), 2) + ",";
   
   // CCI, Williams, Momentum, ROC (4)
   features += DoubleToString(iCCIGet(symbol, 14, 0), 2) + ",";
   features += DoubleToString(iWPRGet(symbol, 14, 0), 2) + ",";
   features += DoubleToString(iMomGet(symbol, 14, 0), 5) + ",";
   features += DoubleToString(CalcROC(symbol, 12, rates), 2) + ",";
   
   // ATR (2) + StdDev (1)
   features += DoubleToString(iATRGet(symbol, 14, 0), 5) + ",";
   features += DoubleToString(iATRGet(symbol, 20, 0), 5) + ",";
   features += DoubleToString(iStdDevGet(symbol, 20, 0), 5) + ",";
   
   // Bollinger Bands (4)
   double bb_up[], bb_mid[], bb_low[];
   ArraySetAsSeries(bb_up, true);
   ArraySetAsSeries(bb_mid, true);
   ArraySetAsSeries(bb_low, true);
   int bb_handle = iBands(symbol, Timeframe, 20, 0, 2, PRICE_CLOSE);
   CopyBuffer(bb_handle, 1, 0, 1, bb_up);
   CopyBuffer(bb_handle, 0, 0, 1, bb_mid);
   CopyBuffer(bb_handle, 2, 0, 1, bb_low);
   features += DoubleToString(bb_up[0], 5) + ",";
   features += DoubleToString(bb_mid[0], 5) + ",";
   features += DoubleToString(bb_low[0], 5) + ",";
   features += DoubleToString(bb_up[0] - bb_low[0], 5) + ",";
   
   // ADX + DI (3)
   features += DoubleToString(iADXGet(symbol, 14, 0, 0), 2) + ",";
   features += DoubleToString(iADXGet(symbol, 14, 1, 0), 2) + ",";
   features += DoubleToString(iADXGet(symbol, 14, 2, 0), 2) + ",";
   
   // SAR (1)
   features += DoubleToString(iSARGet(symbol, 0.02, 0.2, 0), 5) + ",";
   
   // Volume indicators (3)
   features += DoubleToString(CalcVolumeMA(symbol, 20, rates), 0) + ",";
   features += DoubleToString(CalcOBV(symbol, rates), 0) + ",";
   features += DoubleToString(CalcVolumeROC(symbol, 10, rates), 2) + ",";
   
   // Support/Resistance/Pivot (3)
   features += DoubleToString(CalcSupport(symbol, rates), 5) + ",";
   features += DoubleToString(CalcResistance(symbol, rates), 5) + ",";
   features += DoubleToString(CalcPivot(symbol), 5) + ",";
   
   // Price-MA differences (3)
   double price = rates[0].close;
   double ma5 = iMAGet(symbol, 5, 0);
   double ma20 = iMAGet(symbol, 20, 0);
   double ma50 = iMAGet(symbol, 50, 0);
   features += DoubleToString(price - ma5, 5) + ",";
   features += DoubleToString(price - ma20, 5) + ",";
   features += DoubleToString(price - ma50, 5) + ",";
   
   // MA crosses (2)
   features += DoubleToString(ma5 - ma20, 5) + ",";
   features += DoubleToString(ma20 - ma50, 5) + ",";
   
   // Volatility percentile + Trend strength (2)
   features += DoubleToString(CalcVolPercentile(symbol, 20), 2) + ",";
   features += DoubleToString(iADXGet(symbol, 14, 0, 0), 2) + ",";
   
   // Session indicators (3)
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   features += IntegerToString((dt.hour >= 0 && dt.hour < 9) ? 1 : 0) + ",";
   features += IntegerToString((dt.hour >= 8 && dt.hour < 17) ? 1 : 0) + ",";
   features += IntegerToString((dt.hour >= 13 && dt.hour < 22) ? 1 : 0) + ",";
   
   // Time features (2)
   features += IntegerToString(dt.hour) + ",";
   features += IntegerToString(dt.day_of_week) + ",";
   
   // Additional ROC (2)
   features += DoubleToString(CalcROC(symbol, 5, rates), 2) + ",";
   features += DoubleToString(CalcROC(symbol, 10, rates), 2) + ",";
   
   // Ranges (2)
   features += DoubleToString(rates[0].high - rates[0].low, 5) + ",";
   features += DoubleToString(CalcTrueRange(symbol, rates), 5) + ",";
   
   // Market regime (2)
   bool trending = iADXGet(symbol, 14, 0, 0) > 25;
   features += IntegerToString(trending ? 1 : 0) + ",";
   features += IntegerToString(!trending ? 1 : 0) + ",";
   
   // Spread (2)
   double spread = SymbolInfoDouble(symbol, SYMBOL_ASK) - SymbolInfoDouble(symbol, SYMBOL_BID);
   double spreadPips = spread / SymbolInfoDouble(symbol, SYMBOL_POINT) / 10.0;
   double atr = iATRGet(symbol, 14, 0);
   features += DoubleToString(spreadPips, 2) + ",";
   features += DoubleToString(atr > 0 ? spreadPips / atr : 0, 2);
   
   return features;
}

//+------------------------------------------------------------------+
//| Write CSV with all symbols                                         |
//+------------------------------------------------------------------+
void WriteAllSymbolsToCSV()
{
   string filename = LocalOutputFolder + "\\latest_features.csv";
   int handle = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_ANSI);
   
   if(handle == INVALID_HANDLE)
   {
      Print("ERROR: Cannot open file: ", filename);
      return;
   }
   
   // Write header
   string header = "Symbol,Timestamp,Open,High,Low,Close,Volume,";
   header += "MA_5,MA_10,MA_20,MA_50,MA_100,MA_200,";
   header += "EMA_5,EMA_10,EMA_20,EMA_50,";
   header += "AMA_Fast,AMA_Slow,AMA_Signal,";
   header += "RSI_14,MACD_Main,MACD_Signal,MACD_Hist,";
   header += "Stoch_K,Stoch_D,CCI_14,WilliamsR_14,Momentum_14,ROC_12,";
   header += "ATR_14,ATR_20,StdDev_20,";
   header += "BB_Upper,BB_Middle,BB_Lower,BB_Width,";
   header += "ADX_14,Plus_DI,Minus_DI,ParabolicSAR,";
   header += "Volume_MA,OBV,Volume_ROC,";
   header += "Support_Level,Resistance_Level,Pivot_Point,";
   header += "Price_MA5_Diff,Price_MA20_Diff,Price_MA50_Diff,";
   header += "MA5_MA20_Cross,MA20_MA50_Cross,";
   header += "Volatility_Percentile,Trend_Strength,";
   header += "Is_Asian_Session,Is_European_Session,Is_US_Session,";
   header += "Hour_Of_Day,Day_Of_Week,";
   header += "Rate_Of_Change_5,Rate_Of_Change_10,";
   header += "High_Low_Range,True_Range,";
   header += "Is_Trending,Is_Ranging,";
   header += "Spread_Pips,Spread_To_ATR_Ratio\n";
   
   FileWriteString(handle, header);
   
   // Write data for each symbol
   int count = 0;
   for(int i = 0; i < g_SymbolCount; i++)
   {
      string features = CalculateFeatures(g_Symbols[i]);
      if(StringLen(features) > 0)
      {
         FileWriteString(handle, features + "\n");
         count++;
      }
   }
   
   FileClose(handle);
   
   if(count > 0)
      Print("✓ Features written: ", count, " symbols at ", TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
}

//+------------------------------------------------------------------+
//| Helper functions - Get indicator values                           |
//+------------------------------------------------------------------+

double iMAGet(string symbol, int period, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iMA(symbol, Timeframe, period, 0, MODE_SMA, PRICE_CLOSE);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iEMAGet(string symbol, int period, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iMA(symbol, Timeframe, period, 0, MODE_EMA, PRICE_CLOSE);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iAMAGet(string symbol, int period, int fast, int slow, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iAMA(symbol, Timeframe, period, fast, slow, 0, PRICE_CLOSE);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iRSIGet(string symbol, int period, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iRSI(symbol, Timeframe, period, PRICE_CLOSE);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iStochGet(string symbol, int k, int d, int slow, int line, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iStochastic(symbol, Timeframe, k, d, slow, MODE_SMA, STO_LOWHIGH);
   return (CopyBuffer(h, line, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iCCIGet(string symbol, int period, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iCCI(symbol, Timeframe, period, PRICE_TYPICAL);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iWPRGet(string symbol, int period, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iWPR(symbol, Timeframe, period);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iMomGet(string symbol, int period, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iMomentum(symbol, Timeframe, period, PRICE_CLOSE);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iATRGet(string symbol, int period, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iATR(symbol, Timeframe, period);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iStdDevGet(string symbol, int period, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iStdDev(symbol, Timeframe, period, 0, MODE_SMA, PRICE_CLOSE);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iADXGet(string symbol, int period, int line, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iADX(symbol, Timeframe, period);
   return (CopyBuffer(h, line, shift, 1, buf) > 0) ? buf[0] : 0;
}

double iSARGet(string symbol, double step, double max, int shift)
{
   double buf[];
   ArraySetAsSeries(buf, true);
   int h = iSAR(symbol, Timeframe, step, max);
   return (CopyBuffer(h, 0, shift, 1, buf) > 0) ? buf[0] : 0;
}

//+------------------------------------------------------------------+
//| Calculation functions                                              |
//+------------------------------------------------------------------+

double CalcROC(string symbol, int period, MqlRates &rates[])
{
   if(ArraySize(rates) < period + 1) return 0;
   return ((rates[0].close - rates[period].close) / rates[period].close) * 100.0;
}

double CalcVolumeMA(string symbol, int period, MqlRates &rates[])
{
   if(ArraySize(rates) < period) return 0;
   long sum = 0;
   for(int i = 0; i < period; i++)
      sum += rates[i].tick_volume;
   return (double)sum / period;
}

double CalcOBV(string symbol, MqlRates &rates[])
{
   if(ArraySize(rates) < 50) return 0;
   double obv = 0;
   for(int i = 49; i >= 0; i--)
   {
      if(i < 49)
      {
         if(rates[i].close > rates[i+1].close)
            obv += rates[i].tick_volume;
         else if(rates[i].close < rates[i+1].close)
            obv -= rates[i].tick_volume;
      }
   }
   return obv;
}

double CalcVolumeROC(string symbol, int period, MqlRates &rates[])
{
   if(ArraySize(rates) < period + 1) return 0;
   return ((rates[0].tick_volume - rates[period].tick_volume) / (double)rates[period].tick_volume) * 100.0;
}

double CalcSupport(string symbol, MqlRates &rates[])
{
   if(ArraySize(rates) < 50) return 0;
   double lowest = rates[0].low;
   for(int i = 1; i < 50; i++)
      if(rates[i].low < lowest)
         lowest = rates[i].low;
   return lowest;
}

double CalcResistance(string symbol, MqlRates &rates[])
{
   if(ArraySize(rates) < 50) return 0;
   double highest = rates[0].high;
   for(int i = 1; i < 50; i++)
      if(rates[i].high > highest)
         highest = rates[i].high;
   return highest;
}

double CalcPivot(string symbol)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(symbol, PERIOD_D1, 1, 1, rates) == 1)
      return (rates[0].high + rates[0].low + rates[0].close) / 3.0;
   return 0;
}

double CalcVolPercentile(string symbol, int period)
{
   double atr = iATRGet(symbol, period, 0);
   int below = 0;
   for(int i = 0; i < period; i++)
      if(iATRGet(symbol, period, i) < atr)
         below++;
   return (double)below / period * 100.0;
}

double CalcTrueRange(string symbol, MqlRates &rates[])
{
   if(ArraySize(rates) < 2) return 0;
   double tr1 = rates[0].high - rates[0].low;
   double tr2 = MathAbs(rates[0].high - rates[1].close);
   double tr3 = MathAbs(rates[0].low - rates[1].close);
   return MathMax(tr1, MathMax(tr2, tr3));
}
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//|                                XAUUSD_Apex_Champion_v16.mq5     |
//|               Copyright 2026, Apex Institutional Trading             |
//|                Master Sculptor 1-Trade-Per-Day Edition (v16.0)   |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Apex Institutional Trading"
#property link      "https://www.mql5.com"
#property version   "16.00"
#property description "XAUUSD Apex Champion v16 (1-Trade-Per-Day High Conviction Sculptor)"
#property description "Engineered for 650 USC ($6.50 USD) Cent Accounts"

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters ---
input group "=== Risk & Daily Limit ==="
input double   InitialRiskPercent   = 2.0;       // Risk % per Trade (2.0%)
input double   MaxLotLimit          = 2.0;       // Max Lot Cap
input int      InpMaxDailyTrades    = 1;         // Maximum Trades Allowed Per Day (1 Trade/Day)
input double   InpMaxDailyDrawdown  = 3.0;       // Max Daily Equity Drawdown Limit (%)
input double   MaxAllowedPullback   = 15.0;      // Max Pullback % from Peak High-Water Mark
input ulong    MagicNumber          = 160001;    // Magic Number

input group "=== Signal & Indicators ==="
input bool     UseH1TrendFilter     = true;      // Enable H1 EMA Trend Filter
input int      H1_EMA_Fast          = 20;        // H1 Fast EMA
input int      H1_EMA_Slow          = 50;        // H1 Slow EMA
input int      M5_BreakoutPeriod    = 15;        // M5 Donchian Breakout Period
input int      RSI_Period           = 14;        // RSI Period
input double   RSI_Buy_Min          = 52.0;      // Buy RSI Min
input double   RSI_Buy_Max          = 70.0;      // Buy RSI Max
input double   RSI_Sell_Min         = 30.0;      // Sell RSI Min
input double   RSI_Sell_Max         = 48.0;      // Sell RSI Max
input int      InpMaxSpreadPips     = 25;        // Max Spread Pips

input group "=== High RR Target & Breakeven ==="
input double   InpTargetRR          = 2.8;       // Target Risk-Reward Ratio (1:2.8)
input bool     InpUseBreakeven      = true;      // Enable Breakeven Move
input double   InpBreakevenTrigger  = 1.0;       // Move SL to BE at 1.0R Profit
input bool     InpUseTrailing       = true;      // Enable ATR Trailing Stop
input double   InpTrailingStepATR   = 1.2;       // Trailing Step ATR Multiplier

input group "=== Trading Sessions (GMT+7) ==="
input bool     UseTimeFilter        = true;      // Enable Session Window
input int      StartHour            = 12;        // Session Start Hour (London)
input int      EndHour              = 22;        // Session End Hour (NY Close)
input bool     SkipFridayEvening    = true;      // Skip Friday after 17:00

//--- Global Objects ---
CTrade         m_trade;
CPositionInfo  m_posInfo;
CSymbolInfo    m_symInfo;

int            m_handle_h1_fast     = INVALID_HANDLE;
int            m_handle_h1_slow     = INVALID_HANDLE;
int            m_handle_m5_rsi      = INVALID_HANDLE;
int            m_handle_m5_atr      = INVALID_HANDLE;

double         m_high_water_mark    = 650.0;
int            m_last_day           = -1;
double         m_day_start_equity   = 0.0;
int            m_daily_trade_count  = 0;
bool           m_day_stopped        = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   m_trade.SetExpertMagicNumber(MagicNumber);
   m_trade.SetDeviationInPoints(10);
   
   if(!m_symInfo.Name(_Symbol)) return INIT_FAILED;
   m_symInfo.RefreshRates();
   
   m_handle_h1_fast = iMA(_Symbol, PERIOD_H1, H1_EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h1_slow = iMA(_Symbol, PERIOD_H1, H1_EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_m5_rsi  = iRSI(_Symbol, PERIOD_M5, RSI_Period, PRICE_CLOSE);
   m_handle_m5_atr  = iATR(_Symbol, PERIOD_M5, 14);
   
   if(m_handle_h1_fast == INVALID_HANDLE || m_handle_h1_slow == INVALID_HANDLE ||
      m_handle_m5_rsi == INVALID_HANDLE || m_handle_m5_atr == INVALID_HANDLE)
   {
      Print("Error creating indicator handles in v16");
      return INIT_FAILED;
   }
   
   m_high_water_mark = AccountInfoDouble(ACCOUNT_BALANCE);
   if(m_high_water_mark <= 0) m_high_water_mark = 650.0;
   
   m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   Print("EA v16 Master Sculptor Initialized Successfully for ", _Symbol);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(m_handle_h1_fast);
   IndicatorRelease(m_handle_h1_slow);
   IndicatorRelease(m_handle_m5_rsi);
   IndicatorRelease(m_handle_m5_atr);
}

//+------------------------------------------------------------------+
//| Session Filter Check                                             |
//+------------------------------------------------------------------+
bool IsTradingTimeAllowed()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   
   if(SkipFridayEvening && dt.day_of_week == 5 && dt.hour >= 17) return false;
   if(!UseTimeFilter) return true;
   
   return (dt.hour >= StartHour && dt.hour < EndHour);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   m_symInfo.RefreshRates();
   
   // Update Peak High-Water Mark
   double current_balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(current_balance > m_high_water_mark)
   {
      m_high_water_mark = current_balance;
   }
   
   // Daily Reset
   MqlDateTime dt;
   TimeCurrent(dt);
   if(dt.day != m_last_day)
   {
      m_last_day = dt.day;
      m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_daily_trade_count = 0;
      m_day_stopped = false;
   }
   
   if(m_day_stopped) return;
   if(m_daily_trade_count >= InpMaxDailyTrades) return; // Strict 1 Trade/Day Limit
   
   double curr_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double daily_dd_pct = (m_day_start_equity > 0) ? ((m_day_start_equity - curr_equity) / m_day_start_equity) * 100.0 : 0.0;
   
   if(daily_dd_pct >= InpMaxDailyDrawdown)
   {
      m_day_stopped = true;
      return;
   }
   
   // Manage Open Position (Breakeven & Trailing)
   ManageOpenPosition();
   
   // Check Position Count
   if(CountPositions() >= 1) return;
   
   // Session & Spread Filter
   if(!IsTradingTimeAllowed()) return;
   
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double point = m_symInfo.Point();
   double spread_pips = (point > 0) ? (spread * point / 0.1) : spread;
   if(spread_pips > InpMaxSpreadPips) return;
   
   CheckSignal();
}

//+------------------------------------------------------------------+
//| Entry Signal Check                                               |
//+------------------------------------------------------------------+
void CheckSignal()
{
   int h1_trend = GetH1Trend();
   if(UseH1TrendFilter && h1_trend == 0) return;
   
   double rsi[], atr[];
   ArraySetAsSeries(rsi, true); ArraySetAsSeries(atr, true);
   if(CopyBuffer(m_handle_m5_rsi, 0, 0, 2, rsi) < 2 ||
      CopyBuffer(m_handle_m5_atr, 0, 0, 2, atr) < 2) return;
      
   double close_1 = iClose(_Symbol, PERIOD_M5, 1);
   double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
   
   double highest_h = GetHighestHigh(M5_BreakoutPeriod, 2);
   double lowest_l  = GetLowestLow(M5_BreakoutPeriod, 2);
   
   bool buy_signal  = (h1_trend > 0) && (close_1 > highest_h) && (close_1 > open_1) && (rsi[0] >= RSI_Buy_Min && rsi[0] <= RSI_Buy_Max);
   bool sell_signal = (h1_trend < 0) && (close_1 < lowest_l)  && (close_1 < open_1) && (rsi[0] >= RSI_Sell_Min && rsi[0] <= RSI_Sell_Max);
   
   if(buy_signal)
   {
      ExecuteOrder(1, atr[0]);
   }
   else if(sell_signal)
   {
      ExecuteOrder(-1, atr[0]);
   }
}

int GetH1Trend()
{
   double f[], s[];
   ArraySetAsSeries(f, true); ArraySetAsSeries(s, true);
   if(CopyBuffer(m_handle_h1_fast, 0, 0, 2, f) < 2 ||
      CopyBuffer(m_handle_h1_slow, 0, 0, 2, s) < 2) return 0;
      
   double close_h1 = iClose(_Symbol, PERIOD_H1, 1);
   
   if(close_h1 > s[0] && f[0] > s[0]) return 1;
   if(close_h1 < s[0] && f[0] < s[0]) return -1;
   return 0;
}

double GetHighestHigh(int count, int start_bar)
{
   double h_max = 0;
   for(int i = start_bar; i < start_bar + count; i++)
   {
      double val = iHigh(_Symbol, PERIOD_M5, i);
      if(val > h_max) h_max = val;
   }
   return h_max;
}

double GetLowestLow(int count, int start_bar)
{
   double l_min = 999999;
   for(int i = start_bar; i < start_bar + count; i++)
   {
      double val = iLow(_Symbol, PERIOD_M5, i);
      if(val < l_min) l_min = val;
   }
   return l_min;
}

void ExecuteOrder(int type, double atr_val)
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (type == 1) ? ask : bid;
   
   double point = m_symInfo.Point();
   double sl_dist_pts = (atr_val * 1.5) / point;
   if(sl_dist_pts < 250) sl_dist_pts = 250;
   if(sl_dist_pts > 450) sl_dist_pts = 450;
   
   double sl_price = (type == 1) ? (entry - sl_dist_pts * point) : (entry + sl_dist_pts * point);
   double tp_price = (type == 1) ? (entry + sl_dist_pts * InpTargetRR * point) : (entry - sl_dist_pts * InpTargetRR * point);
   
   sl_price = NormalizeDouble(sl_price, _Digits);
   tp_price = NormalizeDouble(tp_price, _Digits);
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double dynamic_risk = InitialRiskPercent;
   
   double pullback_pct = 0;
   if(m_high_water_mark > 0)
   {
      pullback_pct = ((m_high_water_mark - balance) / m_high_water_mark) * 100.0;
   }
   if(pullback_pct >= MaxAllowedPullback)
   {
      dynamic_risk = 1.0;
   }
   
   double risk_amt = balance * (dynamic_risk / 100.0);
   double lot_size = CalculateLot(risk_amt, sl_dist_pts * point);
   
   if(type == 1)
   {
      if(m_trade.Buy(lot_size, _Symbol, entry, sl_price, tp_price, "Apex_v16_Buy"))
      {
         m_daily_trade_count++;
         Print("v16 BUY Executed! Lot: ", lot_size, " SL: ", sl_price, " TP: ", tp_price);
      }
   }
   else
   {
      if(m_trade.Sell(lot_size, _Symbol, entry, sl_price, tp_price, "Apex_v16_Sell"))
      {
         m_daily_trade_count++;
         Print("v16 SELL Executed! Lot: ", lot_size, " SL: ", sl_price, " TP: ", tp_price);
      }
   }
}

double CalculateLot(double risk_amt, double sl_dist)
{
   if(sl_dist <= 0) return m_symInfo.LotsMin();
   
   double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double point_sz = m_symInfo.Point();
   if(tick_val <= 0 || point_sz <= 0) return m_symInfo.LotsMin();
   
   double lot = risk_amt / ((sl_dist / point_sz) * tick_val);
   double step = m_symInfo.LotsStep();
   if(step > 0) lot = MathFloor(lot / step) * step;
   
   double min_lot = m_symInfo.LotsMin();
   if(lot < min_lot) lot = min_lot;
   if(lot > MaxLotLimit) lot = MaxLotLimit;
   
   return NormalizeDouble(lot, (min_lot < 0.01) ? 4 : 2);
}

void ManageOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_posInfo.SelectByIndex(i))
      {
         if(m_posInfo.Symbol() == _Symbol && m_posInfo.Magic() == MagicNumber)
         {
            double entry = m_posInfo.PriceOpen();
            double current_sl = m_posInfo.StopLoss();
            double current_tp = m_posInfo.TakeProfit();
            double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            double current_price = (m_posInfo.PositionType() == POSITION_TYPE_BUY) ? bid : ask;
            
            double point = m_symInfo.Point();
            double atr[];
            ArraySetAsSeries(atr, true);
            if(CopyBuffer(m_handle_m5_atr, 0, 0, 1, atr) < 1) continue;
            
            if(m_posInfo.PositionType() == POSITION_TYPE_BUY)
            {
               double risk_dist = entry - current_sl;
               if(risk_dist > 0 && InpUseBreakeven)
               {
                  if(current_price >= (entry + risk_dist * InpBreakevenTrigger))
                  {
                     double new_sl = NormalizeDouble(entry + (10 * point), _Digits);
                     if(current_sl < new_sl)
                     {
                        m_trade.PositionModify(m_posInfo.Ticket(), new_sl, current_tp);
                        Print("v16 BUY Moved to Breakeven: ", new_sl);
                     }
                  }
               }
               
               if(InpUseTrailing && current_sl >= entry)
               {
                  double trail_dist = atr[0] * InpTrailingStepATR;
                  double new_sl = NormalizeDouble(current_price - trail_dist, _Digits);
                  if(new_sl > current_sl + (10 * point))
                  {
                     m_trade.PositionModify(m_posInfo.Ticket(), new_sl, current_tp);
                  }
               }
            }
            else if(m_posInfo.PositionType() == POSITION_TYPE_SELL)
            {
               double risk_dist = current_sl - entry;
               if(risk_dist > 0 && InpUseBreakeven)
               {
                  if(current_price <= (entry - risk_dist * InpBreakevenTrigger))
                  {
                     double new_sl = NormalizeDouble(entry - (10 * point), _Digits);
                     if(current_sl > new_sl || current_sl == 0)
                     {
                        m_trade.PositionModify(m_posInfo.Ticket(), new_sl, current_tp);
                        Print("v16 SELL Moved to Breakeven: ", new_sl);
                     }
                  }
               }
               
               if(InpUseTrailing && current_sl > 0 && current_sl <= entry)
               {
                  double trail_dist = atr[0] * InpTrailingStepATR;
                  double new_sl = NormalizeDouble(current_price + trail_dist, _Digits);
                  if(new_sl < current_sl - (10 * point))
                  {
                     m_trade.PositionModify(m_posInfo.Ticket(), new_sl, current_tp);
                  }
               }
            }
         }
      }
   }
}

int CountPositions()
{
   int count = 0;
   for(int i = 0; i < PositionsTotal(); i++)
   {
      if(m_posInfo.SelectByIndex(i))
      {
         if(m_posInfo.Symbol() == _Symbol && m_posInfo.Magic() == MagicNumber)
         {
            count++;
         }
      }
   }
   return count;
}

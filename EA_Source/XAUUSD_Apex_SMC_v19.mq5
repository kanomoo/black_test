//+------------------------------------------------------------------+
//|                                   XAUUSD_Apex_SMC_v19.mq5        |
//|               Copyright 2026, Apex Institutional Trading             |
//|         Institutional Asian Sweep & Dual Regime Engine (v19.0)   |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Apex Institutional Trading"
#property link      "https://www.mql5.com"
#property version   "19.00"
#property description "XAUUSD Apex SMC v19 (Asian Range Width Filter + Hybrid Trend/Mean Reversion)"
#property description "Engineered to maximize winning months on 650 USC Cent Accounts"

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Inputs ---
input group "=== Risk & Limits ==="
input double   InitialRiskPercent   = 1.5;       // Risk % per Trade (1.5%)
input int      InpMaxDailyTrades    = 1;         // Maximum Trades Per Day (1 Trade/Day)
input double   InpMaxDailyDrawdown  = 2.5;       // Max Daily Equity Drawdown Limit (%)
input ulong    MagicNumber          = 190001;    // Magic Number

input group "=== Asian Range & Filters ==="
input int      AsianStartHour       = 1;         // Asian Start Hour (01:00 GMT+7)
input int      AsianEndHour         = 9;         // Asian End Hour (09:00 GMT+7)
input int      TradeStartHour       = 11;        // Trade Start Hour (11:00 GMT+7)
input int      TradeEndHour         = 21;        // Trade End Hour (21:00 GMT+7)
input double   MinAsianRangePts     = 600;       // Min Asian Range (6.0 Gold Pts)
input double   MaxAsianRangePts     = 2800;      // Max Asian Range (28.0 Gold Pts)

input group "=== Entry & Profit Lock ==="
input int      H1_EMA_Period        = 34;        // H1 EMA Period
input int      RSI_Period           = 14;        // RSI Period
input double   InpTP1_RR            = 1.0;       // TP1 Risk-Reward (1:1.0) -> BE + 50% Lock
input double   InpTP2_RR            = 2.5;       // TP2 Risk-Reward (1:2.5) -> Final TP
input int      InpMaxSpreadPips     = 25;        // Max Spread Pips

//--- Global Objects ---
CTrade         m_trade;
CPositionInfo  m_posInfo;
CSymbolInfo    m_symInfo;

int            m_handle_h1_ema      = INVALID_HANDLE;
int            m_handle_m5_rsi      = INVALID_HANDLE;
int            m_handle_m5_atr      = INVALID_HANDLE;

double         m_asian_high         = 0.0;
double         m_asian_low          = 999999.0;
int            m_last_day           = -1;
double         m_day_start_equity   = 0.0;
int            m_daily_trade_count  = 0;
bool           m_day_stopped        = false;
bool           m_tp1_done           = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   m_trade.SetExpertMagicNumber(MagicNumber);
   m_trade.SetDeviationInPoints(10);
   
   if(!m_symInfo.Name(_Symbol)) return INIT_FAILED;
   m_symInfo.RefreshRates();
   
   m_handle_h1_ema = iMA(_Symbol, PERIOD_H1, H1_EMA_Period, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_m5_rsi = iRSI(_Symbol, PERIOD_M5, RSI_Period, PRICE_CLOSE);
   m_handle_m5_atr = iATR(_Symbol, PERIOD_M5, 14);
   
   if(m_handle_h1_ema == INVALID_HANDLE || m_handle_m5_rsi == INVALID_HANDLE ||
      m_handle_m5_atr == INVALID_HANDLE)
   {
      Print("Error creating indicator handles in v19");
      return INIT_FAILED;
   }
   
   m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   Print("EA v19 Apex SMC Master Initialized Successfully for ", _Symbol);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(m_handle_h1_ema);
   IndicatorRelease(m_handle_m5_rsi);
   IndicatorRelease(m_handle_m5_atr);
}

void CalculateAsianRange()
{
   m_asian_high = 0.0;
   m_asian_low  = 999999.0;
   
   MqlDateTime dt;
   for(int i = 1; i < 300; i++)
   {
      datetime bar_time = iTime(_Symbol, PERIOD_M5, i);
      TimeToStruct(bar_time, dt);
      
      if(dt.hour >= AsianStartHour && dt.hour < AsianEndHour)
      {
         double h = iHigh(_Symbol, PERIOD_M5, i);
         double l = iLow(_Symbol, PERIOD_M5, i);
         if(h > m_asian_high) m_asian_high = h;
         if(l < m_asian_low)  m_asian_low  = l;
      }
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   m_symInfo.RefreshRates();
   
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
   
   // Manage Open Positions
   ManagePositions();
   
   if(CountPositions() >= 1) return;
   
   // Session Window
   if(dt.hour < TradeStartHour || dt.hour >= TradeEndHour) return;
   if(dt.day_of_week == 5 && dt.hour >= 16) return;
   
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double point = m_symInfo.Point();
   double spread_pips = (point > 0) ? (spread * point / 0.1) : spread;
   if(spread_pips > InpMaxSpreadPips) return;
   
   CalculateAsianRange();
   if(m_asian_high <= 0 || m_asian_low >= 999999.0) return;
   
   double range_pts = (m_asian_high - m_asian_low) / point;
   if(range_pts < MinAsianRangePts || range_pts > MaxAsianRangePts) return;
   
   CheckSignal();
}

//+------------------------------------------------------------------+
//| Entry Signal Check                                               |
//+------------------------------------------------------------------+
void CheckSignal()
{
   double ema[], rsi[], atr[];
   ArraySetAsSeries(ema, true); ArraySetAsSeries(rsi, true); ArraySetAsSeries(atr, true);
   
   if(CopyBuffer(m_handle_h1_ema, 0, 0, 2, ema) < 2) return;
   if(CopyBuffer(m_handle_m5_rsi, 0, 0, 2, rsi) < 2) return;
   if(CopyBuffer(m_handle_m5_atr, 0, 0, 2, atr) < 2) return;
   
   double close_1 = iClose(_Symbol, PERIOD_M5, 1);
   double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
   
   bool h1_bull = (close_1 > ema[0]);
   bool h1_bear = (close_1 < ema[0]);
   
   bool buy_signal  = h1_bull && (close_1 > m_asian_high) && (close_1 > open_1) && (rsi[0] >= 50.0 && rsi[0] <= 70.0);
   bool sell_signal = h1_bear && (close_1 < m_asian_low)  && (close_1 < open_1) && (rsi[0] >= 30.0 && rsi[0] <= 50.0);
   
   if(buy_signal)
   {
      ExecuteOrder(1, atr[0]);
   }
   else if(sell_signal)
   {
      ExecuteOrder(-1, atr[0]);
   }
}

void ExecuteOrder(int type, double atr_val)
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double entry = (type == 1) ? ask : bid;
   
   double point = m_symInfo.Point();
   double sl_dist_pts = (atr_val * 1.5) / point;
   if(sl_dist_pts < 220) sl_dist_pts = 220;
   if(sl_dist_pts > 380) sl_dist_pts = 380;
   
   double sl_price = (type == 1) ? (entry - sl_dist_pts * point) : (entry + sl_dist_pts * point);
   double tp_price = (type == 1) ? (entry + sl_dist_pts * InpTP2_RR * point) : (entry - sl_dist_pts * InpTP2_RR * point);
   
   sl_price = NormalizeDouble(sl_price, _Digits);
   tp_price = NormalizeDouble(tp_price, _Digits);
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amt = balance * (InitialRiskPercent / 100.0);
   double lot_size = CalculateLot(risk_amt, sl_dist_pts * point);
   
   if(type == 1)
   {
      if(m_trade.Buy(lot_size, _Symbol, entry, sl_price, tp_price, "Apex_v19_Buy"))
      {
         m_daily_trade_count++;
         m_tp1_done = false;
         Print("v19 BUY Executed! Lot: ", lot_size, " SL: ", sl_price, " TP: ", tp_price);
      }
   }
   else
   {
      if(m_trade.Sell(lot_size, _Symbol, entry, sl_price, tp_price, "Apex_v19_Sell"))
      {
         m_daily_trade_count++;
         m_tp1_done = false;
         Print("v19 SELL Executed! Lot: ", lot_size, " SL: ", sl_price, " TP: ", tp_price);
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
   if(lot > 2.0) lot = 2.0;
   
   return NormalizeDouble(lot, (min_lot < 0.01) ? 4 : 2);
}

void ManagePositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_posInfo.SelectByIndex(i))
      {
         if(m_posInfo.Symbol() == _Symbol && m_posInfo.Magic() == MagicNumber)
         {
            ulong ticket = m_posInfo.Ticket();
            
            double entry = m_posInfo.PriceOpen();
            double current_sl = m_posInfo.StopLoss();
            double current_tp = m_posInfo.TakeProfit();
            double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            double current_price = (m_posInfo.PositionType() == POSITION_TYPE_BUY) ? bid : ask;
            
            double point = m_symInfo.Point();
            
            if(m_posInfo.PositionType() == POSITION_TYPE_BUY)
            {
               double risk_dist = entry - current_sl;
               if(risk_dist > 0)
               {
                  if(!m_tp1_done && current_price >= (entry + risk_dist * InpTP1_RR))
                  {
                     double vol = m_posInfo.Volume();
                     double min_lot = m_symInfo.LotsMin();
                     double close_vol = NormalizeDouble(vol * 0.5, 2);
                     if(close_vol >= min_lot && close_vol < vol)
                     {
                        m_trade.PositionClosePartial(ticket, close_vol);
                     }
                     double new_sl = NormalizeDouble(entry + (10 * point), _Digits);
                     if(current_sl < new_sl)
                     {
                        m_trade.PositionModify(ticket, new_sl, current_tp);
                     }
                     m_tp1_done = true;
                  }
               }
            }
            else if(m_posInfo.PositionType() == POSITION_TYPE_SELL)
            {
               double risk_dist = current_sl - entry;
               if(risk_dist > 0)
               {
                  if(!m_tp1_done && current_price <= (entry - risk_dist * InpTP1_RR))
                  {
                     double vol = m_posInfo.Volume();
                     double min_lot = m_symInfo.LotsMin();
                     double close_vol = NormalizeDouble(vol * 0.5, 2);
                     if(close_vol >= min_lot && close_vol < vol)
                     {
                        m_trade.PositionClosePartial(ticket, close_vol);
                     }
                     double new_sl = NormalizeDouble(entry - (10 * point), _Digits);
                     if(current_sl > new_sl || current_sl == 0)
                     {
                        m_trade.PositionModify(ticket, new_sl, current_tp);
                     }
                     m_tp1_done = true;
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

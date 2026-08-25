//+------------------------------------------------------------------+
//|                                XAUUSD_Apex_Champion_v14.mq5     |
//|               Copyright 2026, Apex Institutional Trading             |
//|             Ultimate Cent Account Edition (650 USC Micro-Grid)   |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Apex Institutional Trading"
#property link      "https://www.mql5.com"
#property version   "14.00"
#property description "XAUUSD Apex Champion v14 (Micro-Lot Sizing + Multi-Tier Profit Lock)"
#property description "Engineered specifically for 650 USC ($6.50 USD) Cent Accounts"

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Inputs ---
input group "=== Micro-Lot & Risk Management ==="
input double   InpLotSize           = 0.01;      // Micro Lot Size (0.01 for 650 USC)
input int      InpMaxOpenPositions  = 1;         // Max Simultaneous Open Positions
input double   InpMaxDailyDrawdown  = 3.0;       // Hard Daily Drawdown Limit (%)
input int      InpMaxDailyLossCount = 3;         // Max Daily Loss Count -> Stop Day

input group "=== Entry Signal & Filters ==="
input int      InpDonchianPeriod    = 15;        // M5 Donchian Breakout Period
input int      InpH1FastEMA         = 20;        // H1 Fast EMA
input int      InpH1SlowEMA         = 50;        // H1 Slow EMA
input int      InpRSI_Period        = 14;        // RSI Period
input double   InpRSI_Buy_Min       = 52.0;      // Buy RSI Lower
input double   InpRSI_Buy_Max       = 72.0;      // Buy RSI Upper
input double   InpRSI_Sell_Min      = 28.0;      // Sell RSI Lower
input double   InpRSI_Sell_Max      = 48.0;      // Sell RSI Upper
input int      InpMaxSpreadPips     = 25;        // Max Spread Pips

input group "=== Multi-Tier Profit Lock ==="
input bool     InpUsePartialClose   = true;      // Enable Multi-Tier Partial Close
input double   InpTP1_Close_Pct     = 40.0;      // TP1 Close % (40%)
input double   InpTP2_Close_Pct     = 30.0;      // TP2 Close % (30%)
input double   InpRR_Level_1        = 1.5;       // TP1 RR (1:1.5) -> Lock BE+
input double   InpRR_Level_2        = 3.0;       // TP2 RR (1:3.0) -> Lock 1.0 RR
input double   InpRR_Level_3        = 6.0;       // TP3 RR (1:6.0) -> Runner

input group "=== Session Filters (GMT+7) ==="
input bool     InpUseTimeFilter     = true;      // Enable Session Time Filter
input int      InpStartHour         = 11;        // Session Start Hour (London)
input int      InpEndHour           = 23;        // Session End Hour (NY Close)
input bool     InpSkipFridayEvening = true;      // Skip Friday after 17:00

input group "=== System Identification ==="
input ulong    InpMagicNumber       = 140001;    // Magic Number
input string   InpTradeComment      = "Apex_v14"; // Order Comment

//--- Objects ---
CTrade         m_trade;
CPositionInfo  m_position;
CSymbolInfo    m_symInfo;

int            m_handle_h1_fast     = INVALID_HANDLE;
int            m_handle_h1_slow     = INVALID_HANDLE;
int            m_handle_m5_rsi      = INVALID_HANDLE;
int            m_handle_m5_atr      = INVALID_HANDLE;

int            m_last_day           = -1;
double         m_day_start_equity   = 0.0;
int            m_daily_loss_count   = 0;
bool           m_day_stopped        = false;

struct V14_STATE {
   ulong  ticket;
   bool   tp1_done;
   bool   tp2_done;
   double initial_sl_dist;
};

V14_STATE v14_states[20];

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(10);
   
   if(!m_symInfo.Name(_Symbol)) return INIT_FAILED;
   m_symInfo.RefreshRates();
   
   m_handle_h1_fast = iMA(_Symbol, PERIOD_H1, InpH1FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h1_slow = iMA(_Symbol, PERIOD_H1, InpH1SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_m5_rsi  = iRSI(_Symbol, PERIOD_M5, InpRSI_Period, PRICE_CLOSE);
   m_handle_m5_atr  = iATR(_Symbol, PERIOD_M5, 14);
   
   if(m_handle_h1_fast == INVALID_HANDLE || m_handle_h1_slow == INVALID_HANDLE ||
      m_handle_m5_rsi == INVALID_HANDLE || m_handle_m5_atr == INVALID_HANDLE)
   {
      Print("Error initializing indicator handles in v14");
      return INIT_FAILED;
   }
   
   ResetStates();
   m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   Print("XAUUSD Apex Champion EA v14 Initialized Successfully.");
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

void ResetStates()
{
   for(int i = 0; i < 20; i++) {
      v14_states[i].ticket = 0;
      v14_states[i].tp1_done = false;
      v14_states[i].tp2_done = false;
      v14_states[i].initial_sl_dist = 0;
   }
}

//+------------------------------------------------------------------+
//| Session Filter Check                                             |
//+------------------------------------------------------------------+
bool IsTradingTimeAllowed()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   
   if(InpSkipFridayEvening && dt.day_of_week == 5 && dt.hour >= 17) return false;
   if(!InpUseTimeFilter) return true;
   
   return (dt.hour >= InpStartHour && dt.hour < InpEndHour);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   m_symInfo.RefreshRates();
   
   // 1. Daily Reset & Loss Control
   MqlDateTime dt;
   TimeCurrent(dt);
   if(dt.day != m_last_day)
   {
      m_last_day = dt.day;
      m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_daily_loss_count = 0;
      m_day_stopped = false;
   }
   
   if(m_day_stopped) return;
   
   double curr_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double daily_dd_pct = (m_day_start_equity > 0) ? ((m_day_start_equity - curr_equity) / m_day_start_equity) * 100.0 : 0.0;
   
   if(daily_dd_pct >= InpMaxDailyDrawdown || m_daily_loss_count >= InpMaxDailyLossCount)
   {
      m_day_stopped = true;
      return;
   }
   
   // 2. Position Management (Multi-Tier Profit Lock)
   ManagePositions();
   
   // 3. Count Open Positions
   if(CountPositions() >= InpMaxOpenPositions) return;
   
   // 4. Session & Spread Filter
   if(!IsTradingTimeAllowed()) return;
   
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double point = m_symInfo.Point();
   double spread_pips = (point > 0) ? (spread * point / 0.1) : spread;
   if(spread_pips > InpMaxSpreadPips) return;
   
   // 5. Check Signal
   CheckSignal();
}

//+------------------------------------------------------------------+
//| Signal Check                                                     |
//+------------------------------------------------------------------+
void CheckSignal()
{
   double h1_fast[], h1_slow[], rsi[], atr[];
   ArraySetAsSeries(h1_fast, true); ArraySetAsSeries(h1_slow, true);
   ArraySetAsSeries(rsi, true); ArraySetAsSeries(atr, true);
   
   if(CopyBuffer(m_handle_h1_fast, 0, 0, 2, h1_fast) < 2) return;
   if(CopyBuffer(m_handle_h1_slow, 0, 0, 2, h1_slow) < 2) return;
   if(CopyBuffer(m_handle_m5_rsi, 0, 0, 2, rsi) < 2) return;
   if(CopyBuffer(m_handle_m5_atr, 0, 0, 2, atr) < 2) return;
   
   int h1_trend = 0;
   if(h1_fast[0] > h1_slow[0]) h1_trend = 1;
   if(h1_fast[0] < h1_slow[0]) h1_trend = -1;
   if(h1_trend == 0) return;
   
   double close_1 = iClose(_Symbol, PERIOD_M5, 1);
   double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
   
   double highest_h = GetHighestHigh(InpDonchianPeriod, 2);
   double lowest_l  = GetLowestLow(InpDonchianPeriod, 2);
   
   bool buy_signal  = (h1_trend > 0) && (close_1 > highest_h) && (close_1 > open_1) && (rsi[0] >= InpRSI_Buy_Min && rsi[0] <= InpRSI_Buy_Max);
   bool sell_signal = (h1_trend < 0) && (close_1 < lowest_l)  && (close_1 < open_1) && (rsi[0] >= InpRSI_Sell_Min && rsi[0] <= InpRSI_Sell_Max);
   
   if(buy_signal)
   {
      ExecuteOrder(1, atr[0]);
   }
   else if(sell_signal)
   {
      ExecuteOrder(-1, atr[0]);
   }
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
   double tp_price = (type == 1) ? (entry + sl_dist_pts * InpRR_Level_3 * point) : (entry - sl_dist_pts * InpRR_Level_3 * point);
   
   sl_price = NormalizeDouble(sl_price, _Digits);
   tp_price = NormalizeDouble(tp_price, _Digits);
   
   double lot = InpLotSize;
   double min_lot = m_symInfo.LotsMin();
   if(lot < min_lot) lot = min_lot;
   
   if(type == 1)
   {
      if(m_trade.Buy(lot, _Symbol, entry, sl_price, tp_price, InpTradeComment))
      {
         ulong ticket = m_trade.ResultOrder();
         RegisterState(ticket, sl_dist_pts * point);
      }
   }
   else
   {
      if(m_trade.Sell(lot, _Symbol, entry, sl_price, tp_price, InpTradeComment))
      {
         ulong ticket = m_trade.ResultOrder();
         RegisterState(ticket, sl_dist_pts * point);
      }
   }
}

void RegisterState(ulong ticket, double sl_dist)
{
   for(int i = 0; i < 20; i++)
   {
      if(v14_states[i].ticket == 0)
      {
         v14_states[i].ticket = ticket;
         v14_states[i].tp1_done = false;
         v14_states[i].tp2_done = false;
         v14_states[i].initial_sl_dist = sl_dist;
         break;
      }
   }
}

void OnTradeTransaction(const MqlTradeTransaction& trans, const MqlTradeRequest& request, const MqlTradeResult& result)
{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      ulong deal_ticket = trans.deal;
      if(HistoryDealSelect(deal_ticket))
      {
         long magic = HistoryDealGetInteger(deal_ticket, DEAL_MAGIC);
         long entry_type = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
         if(magic == InpMagicNumber && entry_type == DEAL_ENTRY_OUT)
         {
            double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
            if(profit < 0)
            {
               m_daily_loss_count++;
            }
         }
      }
   }
}

void ManagePositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_position.SelectByIndex(i))
      {
         if(m_position.Symbol() == _Symbol && m_position.Magic() == InpMagicNumber)
         {
            ulong ticket = m_position.Ticket();
            int idx = GetStateIndex(ticket);
            
            double entry = m_position.PriceOpen();
            double current_sl = m_position.StopLoss();
            double current_tp = m_position.TakeProfit();
            double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            double current_price = (m_position.PositionType() == POSITION_TYPE_BUY) ? bid : ask;
            
            double profit = (m_position.PositionType() == POSITION_TYPE_BUY) ? (current_price - entry) : (entry - current_price);
            if(profit <= 0) continue;
            
            double initial_risk = (idx >= 0 && v14_states[idx].initial_sl_dist > 0) ? v14_states[idx].initial_sl_dist : MathAbs(entry - current_sl);
            if(initial_risk <= 0) continue;
            
            double current_rr = profit / initial_risk;
            
            // TP1 Stage (Lock BE + 0.3 R)
            if(current_rr >= InpRR_Level_1 && (idx < 0 || !v14_states[idx].tp1_done))
            {
               double new_sl = (m_position.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 0.3), _Digits) : NormalizeDouble(entry - (initial_risk * 0.3), _Digits);
               if(InpUsePartialClose) PartialClose(ticket, InpTP1_Close_Pct);
               m_trade.PositionModify(ticket, new_sl, current_tp);
               if(idx >= 0) v14_states[idx].tp1_done = true;
            }
            // TP2 Stage (Lock 1.0 R)
            else if(current_rr >= InpRR_Level_2 && (idx < 0 || !v14_states[idx].tp2_done))
            {
               double new_sl = (m_position.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 1.0), _Digits) : NormalizeDouble(entry - (initial_risk * 1.0), _Digits);
               if(InpUsePartialClose) PartialClose(ticket, InpTP2_Close_Pct);
               m_trade.PositionModify(ticket, new_sl, current_tp);
               if(idx >= 0) v14_states[idx].tp2_done = true;
            }
         }
      }
   }
}

int GetStateIndex(ulong ticket)
{
   for(int i = 0; i < 20; i++)
   {
      if(v14_states[i].ticket == ticket) return i;
   }
   return -1;
}

void PartialClose(ulong ticket, double pct)
{
   if(m_position.SelectByTicket(ticket))
   {
      double current_vol = m_position.Volume();
      double min_lot = m_symInfo.LotsMin();
      double close_vol = NormalizeDouble(current_vol * (pct / 100.0), 2);
      if(close_vol >= min_lot && close_vol < current_vol)
      {
         m_trade.PositionClosePartial(ticket, close_vol);
      }
   }
}

int CountPositions()
{
   int count = 0;
   for(int i = 0; i < PositionsTotal(); i++)
   {
      if(m_position.SelectByIndex(i))
      {
         if(m_position.Symbol() == _Symbol && m_position.Magic() == InpMagicNumber)
         {
            count++;
         }
      }
   }
   return count;
}

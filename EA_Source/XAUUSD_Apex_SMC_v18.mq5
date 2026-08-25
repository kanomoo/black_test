//+------------------------------------------------------------------+
//|                                   XAUUSD_Apex_SMC_v18.mq5        |
//|               Copyright 2026, Apex Institutional Trading             |
//|              Asian Range Expansion & SMC Liquidity Engine        |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Apex Institutional Trading"
#property link      "https://www.mql5.com"
#property version   "18.00"
#property description "XAUUSD Apex SMC v18 (Asian Range Breakout + High Win-Rate Partial Lock)"
#property description "Engineered for 650 USC Cent Accounts"

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Inputs ---
input group "=== Risk & Protection ==="
input double   InitialRiskPercent   = 1.5;       // Risk % per Trade (1.5%)
input int      InpMaxDailyLosses    = 1;         // Max Losses Allowed Per Day (1 Loss -> Stop Day)
input double   InpMaxDailyDrawdown  = 2.5;       // Max Daily Equity Drawdown Limit (%)
input ulong    MagicNumber          = 180001;    // Magic Number

input group "=== Asian Range & Session ==="
input int      AsianStartHour       = 1;         // Asian Range Start Hour (01:00 GMT+7)
input int      AsianEndHour         = 9;         // Asian Range End Hour (09:00 GMT+7)
input int      TradeStartHour       = 11;        // Trading Start Hour (11:00 GMT+7)
input int      TradeEndHour         = 22;        // Trading End Hour (22:00 GMT+7)

input group "=== Trend & Profit Target ==="
input int      H1_EMA_Fast          = 20;        // H1 Fast EMA
input int      H1_EMA_Slow          = 50;        // H1 Slow EMA
input double   InpTP1_RR            = 1.2;       // TP1 Risk-Reward Ratio (1:1.2)
input double   InpTP1_Close_Pct     = 60.0;      // TP1 Partial Close % (60%)
input double   InpTP2_RR            = 2.8;       // TP2 Risk-Reward Ratio (1:2.8)
input int      InpMaxSpreadPips     = 25;        // Max Spread Pips

//--- Global Objects ---
CTrade         m_trade;
CPositionInfo  m_posInfo;
CSymbolInfo    m_symInfo;

int            m_handle_h1_fast     = INVALID_HANDLE;
int            m_handle_h1_slow     = INVALID_HANDLE;
int            m_handle_m5_atr      = INVALID_HANDLE;

double         m_asian_high         = 0.0;
double         m_asian_low          = 999999.0;
int            m_last_day           = -1;
double         m_day_start_equity   = 0.0;
int            m_daily_loss_count   = 0;
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
   
   m_handle_h1_fast = iMA(_Symbol, PERIOD_H1, H1_EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h1_slow = iMA(_Symbol, PERIOD_H1, H1_EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_m5_atr  = iATR(_Symbol, PERIOD_M5, 14);
   
   if(m_handle_h1_fast == INVALID_HANDLE || m_handle_h1_slow == INVALID_HANDLE ||
      m_handle_m5_atr == INVALID_HANDLE)
   {
      Print("Error creating indicator handles in v18");
      return INIT_FAILED;
   }
   
   m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   Print("EA v18 Apex SMC Initialized Successfully for ", _Symbol);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(m_handle_h1_fast);
   IndicatorRelease(m_handle_h1_slow);
   IndicatorRelease(m_handle_m5_atr);
}

//+------------------------------------------------------------------+
//| Calculate Asian Session High & Low                               |
//+------------------------------------------------------------------+
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
   
   // Daily Reset & Asian Range Update
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
   
   if(daily_dd_pct >= InpMaxDailyDrawdown || m_daily_loss_count >= InpMaxDailyLosses)
   {
      m_day_stopped = true;
      return;
   }
   
   // Manage Open Positions
   ManagePositions();
   
   if(CountPositions() >= 1) return;
   
   // Session Filter (Trading Window)
   if(dt.hour < TradeStartHour || dt.hour >= TradeEndHour) return;
   if(dt.day_of_week == 5 && dt.hour >= 17) return; // Skip Friday evening
   
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double point = m_symInfo.Point();
   double spread_pips = (point > 0) ? (spread * point / 0.1) : spread;
   if(spread_pips > InpMaxSpreadPips) return;
   
   CalculateAsianRange();
   if(m_asian_high <= 0 || m_asian_low >= 999999.0) return;
   
   CheckSignal();
}

//+------------------------------------------------------------------+
//| Signal Logic: Asian Range Breakout + H1 Trend                    |
//+------------------------------------------------------------------+
void CheckSignal()
{
   double f[], s[], atr[];
   ArraySetAsSeries(f, true); ArraySetAsSeries(s, true); ArraySetAsSeries(atr, true);
   
   if(CopyBuffer(m_handle_h1_fast, 0, 0, 2, f) < 2) return;
   if(CopyBuffer(m_handle_h1_slow, 0, 0, 2, s) < 2) return;
   if(CopyBuffer(m_handle_m5_atr, 0, 0, 2, atr) < 2) return;
   
   double close_1 = iClose(_Symbol, PERIOD_M5, 1);
   double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
   
   bool h1_bull = (f[0] > s[0]);
   bool h1_bear = (f[0] < s[0]);
   
   bool buy_signal  = h1_bull && (close_1 > m_asian_high) && (close_1 > open_1);
   bool sell_signal = h1_bear && (close_1 < m_asian_low)  && (close_1 < open_1);
   
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
   if(sl_dist_pts > 400) sl_dist_pts = 400;
   
   double sl_price = (type == 1) ? (entry - sl_dist_pts * point) : (entry + sl_dist_pts * point);
   double tp_price = (type == 1) ? (entry + sl_dist_pts * InpTP2_RR * point) : (entry - sl_dist_pts * InpTP2_RR * point);
   
   sl_price = NormalizeDouble(sl_price, _Digits);
   tp_price = NormalizeDouble(tp_price, _Digits);
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amt = balance * (InitialRiskPercent / 100.0);
   double lot_size = CalculateLot(risk_amt, sl_dist_pts * point);
   
   if(type == 1)
   {
      if(m_trade.Buy(lot_size, _Symbol, entry, sl_price, tp_price, "Apex_v18_Buy"))
      {
         m_tp1_done = false;
         Print("v18 BUY Executed! Lot: ", lot_size, " SL: ", sl_price, " TP: ", tp_price);
      }
   }
   else
   {
      if(m_trade.Sell(lot_size, _Symbol, entry, sl_price, tp_price, "Apex_v18_Sell"))
      {
         m_tp1_done = false;
         Print("v18 SELL Executed! Lot: ", lot_size, " SL: ", sl_price, " TP: ", tp_price);
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

void OnTradeTransaction(const MqlTradeTransaction& trans, const MqlTradeRequest& request, const MqlTradeResult& result)
{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      ulong deal_ticket = trans.deal;
      if(HistoryDealSelect(deal_ticket))
      {
         long magic = HistoryDealGetInteger(deal_ticket, DEAL_MAGIC);
         long entry_type = HistoryDealGetInteger(deal_ticket, DEAL_ENTRY);
         if(magic == MagicNumber && entry_type == DEAL_ENTRY_OUT)
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
                     double close_vol = NormalizeDouble(vol * (InpTP1_Close_Pct / 100.0), 2);
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
                     double close_vol = NormalizeDouble(vol * (InpTP1_Close_Pct / 100.0), 2);
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

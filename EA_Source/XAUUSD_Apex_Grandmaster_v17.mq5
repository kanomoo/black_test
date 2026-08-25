//+------------------------------------------------------------------+
//|                             XAUUSD_Apex_Grandmaster_v17.mq5      |
//|               Copyright 2026, Apex Institutional Trading             |
//|               Triple-Timeframe Precision Engine (v17.0)          |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Apex Institutional Trading"
#property link      "https://www.mql5.com"
#property version   "17.00"
#property description "XAUUSD Apex Grandmaster v17 (3-Timeframe Confluence + Daily Hard Loss Guard)"
#property description "Engineered to eliminate monthly drawdown periods on 650 USC Cent Accounts"

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Inputs ---
input group "=== Risk & Protection ==="
input double   InitialRiskPercent   = 1.8;       // Risk % per Trade (1.8%)
input int      InpMaxDailyLosses    = 1;         // Max Losses Allowed Per Day (1 Loss -> Stop Day)
input double   InpMaxDailyDrawdown  = 2.0;       // Max Daily Equity Drawdown Limit (%)
input double   MaxAllowedPullback   = 12.0;      // Max Pullback % from Peak High-Water Mark
input ulong    MagicNumber          = 170001;    // Magic Number

input group "=== Triple-Timeframe Trend Confluence ==="
input int      InpH4_EMA            = 50;        // H4 EMA Filter
input int      InpH1_EMA            = 50;        // H1 EMA Filter
input int      InpM15_EMA           = 50;        // M15 EMA Filter
input int      InpRSI_Period        = 14;        // RSI Period
input double   InpRSI_Buy_Min       = 53.0;      // Buy RSI Min
input double   InpRSI_Buy_Max       = 67.0;      // Buy RSI Max
input double   InpRSI_Sell_Min      = 33.0;      // Sell RSI Min
input double   InpRSI_Sell_Max      = 47.0;      // Sell RSI Max
input int      InpMaxSpreadPips     = 22;        // Max Spread Pips

input group "=== Quick Profit Lock & Target ==="
input double   InpTargetRR          = 1.5;       // Target Risk-Reward Ratio (1:1.5)
input bool     InpUseBreakeven      = true;      // Enable Quick Breakeven
input double   InpBreakevenTrigger  = 0.5;       // Move SL to BE at 0.5R Profit
input bool     InpUsePartialClose   = true;      // Enable 50% Partial Close at 1.0R
input double   InpPartialTrigger    = 1.0;       // Partial Close Trigger Ratio (1.0R)
input bool     InpUseTrailing       = true;      // Enable ATR Trailing Stop
input double   InpTrailingStepATR   = 1.0;       // Trailing Step ATR Multiplier

input group "=== Trading Sessions (GMT+7) ==="
input bool     UseTimeFilter        = true;      // Enable Session Window
input int      StartHour            = 12;        // Session Start Hour (London)
input int      EndHour              = 21;        // Session End Hour (NY Active)
input bool     SkipFriday           = true;      // Skip All Friday Trading

//--- Global Objects ---
CTrade         m_trade;
CPositionInfo  m_posInfo;
CSymbolInfo    m_symInfo;

int            m_handle_h4_ema      = INVALID_HANDLE;
int            m_handle_h1_ema      = INVALID_HANDLE;
int            m_handle_m15_ema     = INVALID_HANDLE;
int            m_handle_m5_rsi      = INVALID_HANDLE;
int            m_handle_m5_atr      = INVALID_HANDLE;

double         m_high_water_mark    = 650.0;
int            m_last_day           = -1;
double         m_day_start_equity   = 0.0;
int            m_daily_loss_count   = 0;
bool           m_day_stopped        = false;
bool           m_partial_done       = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   m_trade.SetExpertMagicNumber(MagicNumber);
   m_trade.SetDeviationInPoints(10);
   
   if(!m_symInfo.Name(_Symbol)) return INIT_FAILED;
   m_symInfo.RefreshRates();
   
   m_handle_h4_ema  = iMA(_Symbol, PERIOD_H4, InpH4_EMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h1_ema  = iMA(_Symbol, PERIOD_H1, InpH1_EMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_m15_ema = iMA(_Symbol, PERIOD_M15, InpM15_EMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_m5_rsi  = iRSI(_Symbol, PERIOD_M5, InpRSI_Period, PRICE_CLOSE);
   m_handle_m5_atr  = iATR(_Symbol, PERIOD_M5, 14);
   
   if(m_handle_h4_ema == INVALID_HANDLE || m_handle_h1_ema == INVALID_HANDLE ||
      m_handle_m15_ema == INVALID_HANDLE || m_handle_m5_rsi == INVALID_HANDLE ||
      m_handle_m5_atr == INVALID_HANDLE)
   {
      Print("Error creating indicator handles in v17");
      return INIT_FAILED;
   }
   
   m_high_water_mark = AccountInfoDouble(ACCOUNT_BALANCE);
   if(m_high_water_mark <= 0) m_high_water_mark = 650.0;
   
   m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   Print("EA v17 Apex Grandmaster Initialized Successfully for ", _Symbol);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(m_handle_h4_ema);
   IndicatorRelease(m_handle_h1_ema);
   IndicatorRelease(m_handle_m15_ema);
   IndicatorRelease(m_handle_m5_rsi);
   IndicatorRelease(m_handle_m5_atr);
}

//+------------------------------------------------------------------+
//| Session Filter                                                   |
//+------------------------------------------------------------------+
bool IsTradingTimeAllowed()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   
   if(SkipFriday && dt.day_of_week == 5) return false;
   if(!UseTimeFilter) return true;
   
   return (dt.hour >= StartHour && dt.hour < EndHour);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   m_symInfo.RefreshRates();
   
   // High-Water Mark Update
   double current_balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(current_balance > m_high_water_mark)
   {
      m_high_water_mark = current_balance;
   }
   
   // Daily Reset & Hard Stop Check
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
   
   // Position Count Check
   if(CountPositions() >= 1) return;
   
   // Session & Spread Filters
   if(!IsTradingTimeAllowed()) return;
   
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double point = m_symInfo.Point();
   double spread_pips = (point > 0) ? (spread * point / 0.1) : spread;
   if(spread_pips > InpMaxSpreadPips) return;
   
   CheckSignal();
}

//+------------------------------------------------------------------+
//| Signal Logic: Triple-Timeframe Alignment                         |
//+------------------------------------------------------------------+
void CheckSignal()
{
   double h4_e[], h1_e[], m15_e[], rsi[], atr[];
   ArraySetAsSeries(h4_e, true); ArraySetAsSeries(h1_e, true);
   ArraySetAsSeries(m15_e, true); ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(atr, true);
   
   if(CopyBuffer(m_handle_h4_ema, 0, 0, 2, h4_e) < 2) return;
   if(CopyBuffer(m_handle_h1_ema, 0, 0, 2, h1_e) < 2) return;
   if(CopyBuffer(m_handle_m15_ema, 0, 0, 2, m15_e) < 2) return;
   if(CopyBuffer(m_handle_m5_rsi, 0, 0, 2, rsi) < 2) return;
   if(CopyBuffer(m_handle_m5_atr, 0, 0, 2, atr) < 2) return;
   
   double close_h4  = iClose(_Symbol, PERIOD_H4, 1);
   double close_h1  = iClose(_Symbol, PERIOD_H1, 1);
   double close_m15 = iClose(_Symbol, PERIOD_M15, 1);
   double close_m5  = iClose(_Symbol, PERIOD_M5, 1);
   double open_m5   = iOpen(_Symbol, PERIOD_M5, 1);
   
   // 3-Timeframe Confluence Alignment
   bool is_uptrend   = (close_h4 > h4_e[0]) && (close_h1 > h1_e[0]) && (close_m15 > m15_e[0]);
   bool is_downtrend = (close_h4 < h4_e[0]) && (close_h1 < h1_e[0]) && (close_m15 < m15_e[0]);
   
   if(!is_uptrend && !is_downtrend) return;
   
   bool buy_candle  = (close_m5 > open_m5);
   bool sell_candle = (close_m5 < open_m5);
   
   bool buy_signal  = is_uptrend && buy_candle && (rsi[0] >= InpRSI_Buy_Min && rsi[0] <= InpRSI_Buy_Max);
   bool sell_signal = is_downtrend && sell_candle && (rsi[0] >= InpRSI_Sell_Min && rsi[0] <= InpRSI_Sell_Max);
   
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
   double sl_dist_pts = (atr_val * 1.2) / point;
   if(sl_dist_pts < 200) sl_dist_pts = 200;
   if(sl_dist_pts > 400) sl_dist_pts = 400;
   
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
      if(m_trade.Buy(lot_size, _Symbol, entry, sl_price, tp_price, "Apex_v17_Buy"))
      {
         m_partial_done = false;
         Print("v17 BUY Executed! Lot: ", lot_size, " SL: ", sl_price, " TP: ", tp_price);
      }
   }
   else
   {
      if(m_trade.Sell(lot_size, _Symbol, entry, sl_price, tp_price, "Apex_v17_Sell"))
      {
         m_partial_done = false;
         Print("v17 SELL Executed! Lot: ", lot_size, " SL: ", sl_price, " TP: ", tp_price);
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
               Print("v17 Deal Loss registered: ", profit, ". Total Loss Count Today: ", m_daily_loss_count);
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
            double atr[];
            ArraySetAsSeries(atr, true);
            if(CopyBuffer(m_handle_m5_atr, 0, 0, 1, atr) < 1) continue;
            
            if(m_posInfo.PositionType() == POSITION_TYPE_BUY)
            {
               double risk_dist = entry - current_sl;
               if(risk_dist > 0)
               {
                  // Quick Breakeven at 0.5R
                  if(InpUseBreakeven && current_price >= (entry + risk_dist * InpBreakevenTrigger))
                  {
                     double new_sl = NormalizeDouble(entry + (10 * point), _Digits);
                     if(current_sl < new_sl)
                     {
                        m_trade.PositionModify(ticket, new_sl, current_tp);
                        Print("v17 BUY Moved to Breakeven: ", new_sl);
                     }
                  }
                  
                  // Partial Close 50% at 1.0R
                  if(InpUsePartialClose && !m_partial_done && current_price >= (entry + risk_dist * InpPartialTrigger))
                  {
                     double vol = m_posInfo.Volume();
                     double min_lot = m_symInfo.LotsMin();
                     double close_vol = NormalizeDouble(vol * 0.5, 2);
                     if(close_vol >= min_lot && close_vol < vol)
                     {
                        if(m_trade.PositionClosePartial(ticket, close_vol))
                        {
                           m_partial_done = true;
                           Print("v17 BUY Partial Closed 50%: ", close_vol);
                        }
                     }
                  }
               }
               
               // Trailing Stop
               if(InpUseTrailing && current_sl >= entry)
               {
                  double trail_dist = atr[0] * InpTrailingStepATR;
                  double new_sl = NormalizeDouble(current_price - trail_dist, _Digits);
                  if(new_sl > current_sl + (10 * point))
                  {
                     m_trade.PositionModify(ticket, new_sl, current_tp);
                  }
               }
            }
            else if(m_posInfo.PositionType() == POSITION_TYPE_SELL)
            {
               double risk_dist = current_sl - entry;
               if(risk_dist > 0)
               {
                  // Quick Breakeven at 0.5R
                  if(InpUseBreakeven && current_price <= (entry - risk_dist * InpBreakevenTrigger))
                  {
                     double new_sl = NormalizeDouble(entry - (10 * point), _Digits);
                     if(current_sl > new_sl || current_sl == 0)
                     {
                        m_trade.PositionModify(ticket, new_sl, current_tp);
                        Print("v17 SELL Moved to Breakeven: ", new_sl);
                     }
                  }
                  
                  // Partial Close 50% at 1.0R
                  if(InpUsePartialClose && !m_partial_done && current_price <= (entry - risk_dist * InpPartialTrigger))
                  {
                     double vol = m_posInfo.Volume();
                     double min_lot = m_symInfo.LotsMin();
                     double close_vol = NormalizeDouble(vol * 0.5, 2);
                     if(close_vol >= min_lot && close_vol < vol)
                     {
                        if(m_trade.PositionClosePartial(ticket, close_vol))
                        {
                           m_partial_done = true;
                           Print("v17 SELL Partial Closed 50%: ", close_vol);
                        }
                     }
                  }
               }
               
               // Trailing Stop
               if(InpUseTrailing && current_sl > 0 && current_sl <= entry)
               {
                  double trail_dist = atr[0] * InpTrailingStepATR;
                  double new_sl = NormalizeDouble(current_price + trail_dist, _Digits);
                  if(new_sl < current_sl - (10 * point))
                  {
                     m_trade.PositionModify(ticket, new_sl, current_tp);
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

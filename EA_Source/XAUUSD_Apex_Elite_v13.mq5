//+------------------------------------------------------------------+
//|                                    XAUUSD_Apex_Elite_v13.mq5     |
//|                    Copyright 2026, Apex Institutional Trading    |
//|                   Regime-Adaptive Volatility Engine v13.0        |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Apex Institutional Trading"
#property link      "https://www.mql5.com"
#property version   "13.00"
#property description "XAUUSD Apex Elite EA v13 (Hard Daily Loss Guard + ADX Regime Filter)"
#property description "Engineered for Cent Accounts (650 USC / $6.50 USD)"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\OrderInfo.mqh>

//--- Input Parameters ---
input group "=== Risk & Daily Protection ==="
input double   InpRiskPercent       = 1.5;       // Risk Percent per Trade (%)
input double   InpMaxDailyDrawdown  = 2.0;       // Hard Daily Drawdown Limit (%) -> Stop Day
input int      InpMaxDailyLossCount = 2;         // Max Losses per Day -> Stop Trading Day
input double   InpFixedLot          = 0.0;       // Fixed Lot Size (0.0 = Auto Risk)

input group "=== ADX & Trend Filters ==="
input int      InpADXPeriod         = 14;        // ADX Period (H1)
input double   InpMinADX            = 22.0;      // Minimum ADX Threshold (Filters Out Sideways Market)
input int      InpFastEMA           = 20;        // Fast EMA Period
input int      InpSlowEMA           = 50;        // Slow EMA Period
input int      InpRSI_Period        = 14;        // RSI Period
input double   InpRSI_Buy_Min       = 52.0;      // Buy RSI Min
input double   InpRSI_Buy_Max       = 68.0;      // Buy RSI Max
input double   InpRSI_Sell_Min      = 32.0;      // Sell RSI Min
input double   InpRSI_Sell_Max      = 48.0;      // Sell RSI Max
input int      InpMaxSpreadPips     = 25;        // Maximum Allowed Spread in Pips

input group "=== Dynamic Profit Lock & Trailing ==="
input double   InpATR_SL_Mult       = 1.2;       // ATR SL Multiplier (Tight Stop)
input double   InpTargetRR          = 2.0;       // Target Risk-Reward Ratio (1:2.0)
input bool     InpUseBreakeven      = true;      // Enable Quick Breakeven
input double   InpBreakevenTrigger  = 0.6;       // Breakeven Trigger Ratio (0.6x Risk)
input bool     InpUsePartialClose   = true;      // Enable 50% Partial Close
input double   InpPartialTrigger    = 1.2;       // Partial Close Trigger Ratio (1.2x Risk)
input bool     InpUseTrailing       = true;      // Enable ATR Trailing Stop
input double   InpTrailingStepATR   = 1.0;       // Trailing Step ATR Multiplier

input group "=== Session Filters (GMT+7) ==="
input bool     InpUseTimeFilter     = true;      // Enable Time Window
input int      InpStartHour         = 12;        // Session Start Hour (London/NY)
input int      InpEndHour           = 22;        // Session End Hour
input bool     InpSkipFridayEvening = true;      // Skip Friday Trading after 17:00

input group "=== System Identification ==="
input ulong    InpMagicNumber       = 130001;    // Magic Number
input string   InpTradeComment      = "Apex_v13"; // Order Comment

//--- Global Variables ---
CTrade         m_trade;
CPositionInfo  m_position;

int            m_handle_adx         = INVALID_HANDLE;
int            m_handle_h4_fast     = INVALID_HANDLE;
int            m_handle_h4_slow     = INVALID_HANDLE;
int            m_handle_h1_fast     = INVALID_HANDLE;
int            m_handle_h1_slow     = INVALID_HANDLE;
int            m_handle_atr         = INVALID_HANDLE;
int            m_handle_rsi         = INVALID_HANDLE;

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
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   
   m_handle_adx      = iADX(_Symbol, PERIOD_H1, InpADXPeriod);
   m_handle_h4_fast = iMA(_Symbol, PERIOD_H4, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h4_slow = iMA(_Symbol, PERIOD_H4, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h1_fast = iMA(_Symbol, PERIOD_H1, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h1_slow = iMA(_Symbol, PERIOD_H1, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_atr      = iATR(_Symbol, PERIOD_M5, 14);
   m_handle_rsi      = iRSI(_Symbol, PERIOD_M5, InpRSI_Period, PRICE_CLOSE);
   
   if(m_handle_adx == INVALID_HANDLE || m_handle_h4_fast == INVALID_HANDLE || 
      m_handle_h4_slow == INVALID_HANDLE || m_handle_h1_fast == INVALID_HANDLE ||
      m_handle_h1_slow == INVALID_HANDLE || m_handle_atr == INVALID_HANDLE || 
      m_handle_rsi == INVALID_HANDLE)
   {
      Print("Error initializing indicator handles in v13");
      return INIT_FAILED;
   }
   
   m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   Print("XAUUSD Apex Elite EA v13 Initialized Successfully.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(m_handle_adx);
   IndicatorRelease(m_handle_h4_fast);
   IndicatorRelease(m_handle_h4_slow);
   IndicatorRelease(m_handle_h1_fast);
   IndicatorRelease(m_handle_h1_slow);
   IndicatorRelease(m_handle_atr);
   IndicatorRelease(m_handle_rsi);
}

//+------------------------------------------------------------------+
//| Helper: Check Trading Time Window & Days                         |
//+------------------------------------------------------------------+
bool IsTradingTimeAllowed()
{
   MqlDateTime dt;
   TimeCurrent(dt);
   
   // Skip Friday evening after 17:00
   if(InpSkipFridayEvening && dt.day_of_week == 5 && dt.hour >= 17) return false;
   
   if(!InpUseTimeFilter) return true;
   
   return (dt.hour >= InpStartHour && dt.hour < InpEndHour);
}

//+------------------------------------------------------------------+
//| Helper: Dynamic Lot Calculation                                  |
//+------------------------------------------------------------------+
double CalculateLotSize(double sl_dist_price)
{
   if(InpFixedLot > 0.0) return InpFixedLot;
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amt = balance * (InpRiskPercent / 100.0);
   
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_val  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double point     = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   
   if(tick_size <= 0 || tick_val <= 0 || point <= 0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   
   double points_at_risk = sl_dist_price / point;
   double value_per_lot  = (points_at_risk / (tick_size / point)) * tick_val;
   
   if(value_per_lot <= 0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   
   double lot = risk_amt / value_per_lot;
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   lot = MathFloor(lot / lot_step) * lot_step;
   if(lot < min_lot) lot = min_lot;
   if(lot > max_lot) lot = max_lot;
   
   return lot;
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // 1. Daily Reset & Loss Protection
   MqlDateTime dt;
   TimeCurrent(dt);
   if(dt.day != m_last_day)
   {
      m_last_day = dt.day;
      m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_daily_loss_count = 0;
      m_day_stopped = false;
   }
   
   // Hard Stop if Daily Limit Hit
   if(m_day_stopped) return;
   
   double curr_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double daily_dd_pct = (m_day_start_equity > 0) ? ((m_day_start_equity - curr_equity) / m_day_start_equity) * 100.0 : 0.0;
   
   if(daily_dd_pct >= InpMaxDailyDrawdown || m_daily_loss_count >= InpMaxDailyLossCount)
   {
      m_day_stopped = true;
      Print("DAILY HARD STOP TRIGGERED! Daily DD: ", daily_dd_pct, "%, Daily Losses: ", m_daily_loss_count);
      return;
   }
   
   // 2. Manage Open Positions
   ManagePositions();
   
   // 3. Count Open Positions
   int open_positions = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_position.SelectByIndex(i))
      {
         if(m_position.Symbol() == _Symbol && m_position.Magic() == InpMagicNumber)
         {
            open_positions++;
         }
      }
   }
   if(open_positions > 0) return; // 1 position at a time
   
   // 4. Session & Spread Filter
   if(!IsTradingTimeAllowed()) return;
   
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double spread_pips = (point > 0) ? (spread * point / 0.1) : spread;
   if(spread_pips > InpMaxSpreadPips) return;
   
   // 5. Indicators & ADX Regime Check
   double adx[], h4_f[], h4_s[], h1_f[], h1_s[], atr[], rsi[];
   ArraySetAsSeries(adx, true);
   ArraySetAsSeries(h4_f, true); ArraySetAsSeries(h4_s, true);
   ArraySetAsSeries(h1_f, true); ArraySetAsSeries(h1_s, true);
   ArraySetAsSeries(atr, true); ArraySetAsSeries(rsi, true);
   
   if(CopyBuffer(m_handle_adx, 0, 0, 2, adx) < 2) return;
   if(CopyBuffer(m_handle_h4_fast, 0, 0, 2, h4_f) < 2) return;
   if(CopyBuffer(m_handle_h4_slow, 0, 0, 2, h4_s) < 2) return;
   if(CopyBuffer(m_handle_h1_fast, 0, 0, 2, h1_f) < 2) return;
   if(CopyBuffer(m_handle_h1_slow, 0, 0, 2, h1_s) < 2) return;
   if(CopyBuffer(m_handle_atr, 0, 0, 2, atr) < 2) return;
   if(CopyBuffer(m_handle_rsi, 0, 0, 2, rsi) < 2) return;
   
   // Skip Flat/Choppy Markets (ADX Regime Filter)
   if(adx[0] < InpMinADX) return;
   
   // Trend Alignment
   bool is_uptrend   = (h4_f[0] > h4_s[0]) && (h1_f[0] > h1_s[0]);
   bool is_downtrend = (h4_f[0] < h4_s[0]) && (h1_f[0] < h1_s[0]);
   
   // M5 Candle confirmation
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, _Period, 0, 3, rates) < 3) return;
   
   bool buy_candle = (rates[1].close > rates[1].open);
   bool sell_candle = (rates[1].close < rates[1].open);
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   // Dynamic ATR SL & TP
   double sl_distance = atr[0] * InpATR_SL_Mult;
   double min_sl_dist = 200 * point * 10;
   double max_sl_dist = 450 * point * 10;
   
   if(sl_distance < min_sl_dist) sl_distance = min_sl_dist;
   if(sl_distance > max_sl_dist) sl_distance = max_sl_dist;
   
   double tp_distance = sl_distance * InpTargetRR;
   
   // ENTRY EXECUTION
   if(is_uptrend && buy_candle && rsi[0] >= InpRSI_Buy_Min && rsi[0] <= InpRSI_Buy_Max)
   {
      double sl = NormalizeDouble(ask - sl_distance, _Digits);
      double tp = NormalizeDouble(ask + tp_distance, _Digits);
      double lot = CalculateLotSize(sl_distance);
      
      if(m_trade.Buy(lot, _Symbol, ask, sl, tp, InpTradeComment))
      {
         m_partial_done = false;
         Print("v13 BUY Executed! Lot: ", lot, " SL: ", sl, " TP: ", tp);
      }
   }
   else if(is_downtrend && sell_candle && rsi[0] >= InpRSI_Sell_Min && rsi[0] <= InpRSI_Sell_Max)
   {
      double sl = NormalizeDouble(bid + sl_distance, _Digits);
      double tp = NormalizeDouble(bid - tp_distance, _Digits);
      double lot = CalculateLotSize(sl_distance);
      
      if(m_trade.Sell(lot, _Symbol, bid, sl, tp, InpTradeComment))
      {
         m_partial_done = false;
         Print("v13 SELL Executed! Lot: ", lot, " SL: ", sl, " TP: ", tp);
      }
   }
}

//+------------------------------------------------------------------+
//| Trade Transaction Event to track Losses                          |
//+------------------------------------------------------------------+
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
               Print("Deal Closed with Loss: ", profit, ". Total Losses Today: ", m_daily_loss_count);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Position Management (Breakeven, Partial Close & Trailing)       |
//+------------------------------------------------------------------+
void ManagePositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_position.SelectByIndex(i))
      {
         if(m_position.Symbol() == _Symbol && m_position.Magic() == InpMagicNumber)
         {
            double open_price    = m_position.PriceOpen();
            double current_sl    = m_position.StopLoss();
            double current_tp    = m_position.TakeProfit();
            double current_price = m_position.PriceCurrent();
            ENUM_POSITION_TYPE pos_type = m_position.PositionType();
            
            double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
            double atr[];
            ArraySetAsSeries(atr, true);
            if(CopyBuffer(m_handle_atr, 0, 0, 1, atr) < 1) continue;
            
            if(pos_type == POSITION_TYPE_BUY)
            {
               double risk_dist = open_price - current_sl;
               if(risk_dist > 0)
               {
                  // 1. Quick Breakeven + Lock 0.2R
                  if(InpUseBreakeven && current_price >= (open_price + risk_dist * InpBreakevenTrigger))
                  {
                     double new_sl = NormalizeDouble(open_price + (risk_dist * 0.2), _Digits);
                     if(current_sl < new_sl)
                     {
                        m_trade.PositionModify(m_position.Ticket(), new_sl, current_tp);
                        Print("v13 BUY Moved to Breakeven+0.2R: ", new_sl);
                     }
                  }
                  
                  // 2. Partial Close 50%
                  if(InpUsePartialClose && !m_partial_done && current_price >= (open_price + risk_dist * InpPartialTrigger))
                  {
                     double vol = m_position.Volume();
                     double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
                     double close_vol = NormalizeDouble(vol * 0.5, 2);
                     if(close_vol >= min_lot && close_vol < vol)
                     {
                        if(m_trade.PositionClosePartial(m_position.Ticket(), close_vol))
                        {
                           m_partial_done = true;
                           Print("v13 BUY Partial Closed 50%: ", close_vol);
                        }
                     }
                  }
               }
               
               // 3. Trailing Stop
               if(InpUseTrailing && current_sl >= open_price)
               {
                  double trail_dist = atr[0] * InpTrailingStepATR;
                  double new_sl = NormalizeDouble(current_price - trail_dist, _Digits);
                  if(new_sl > current_sl + (10 * point))
                  {
                     m_trade.PositionModify(m_position.Ticket(), new_sl, current_tp);
                  }
               }
            }
            else if(pos_type == POSITION_TYPE_SELL)
            {
               double risk_dist = current_sl - open_price;
               if(risk_dist > 0)
               {
                  // 1. Quick Breakeven + Lock 0.2R
                  if(InpUseBreakeven && current_price <= (open_price - risk_dist * InpBreakevenTrigger))
                  {
                     double new_sl = NormalizeDouble(open_price - (risk_dist * 0.2), _Digits);
                     if(current_sl > new_sl || current_sl == 0)
                     {
                        m_trade.PositionModify(m_position.Ticket(), new_sl, current_tp);
                        Print("v13 SELL Moved to Breakeven+0.2R: ", new_sl);
                     }
                  }
                  
                  // 2. Partial Close 50%
                  if(InpUsePartialClose && !m_partial_done && current_price <= (open_price - risk_dist * InpPartialTrigger))
                  {
                     double vol = m_position.Volume();
                     double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
                     double close_vol = NormalizeDouble(vol * 0.5, 2);
                     if(close_vol >= min_lot && close_vol < vol)
                     {
                        if(m_trade.PositionClosePartial(m_position.Ticket(), close_vol))
                        {
                           m_partial_done = true;
                           Print("v13 SELL Partial Closed 50%: ", close_vol);
                        }
                     }
                  }
               }
               
               // 3. Trailing Stop
               if(InpUseTrailing && current_sl > 0 && current_sl <= open_price)
               {
                  double trail_dist = atr[0] * InpTrailingStepATR;
                  double new_sl = NormalizeDouble(current_price + trail_dist, _Digits);
                  if(new_sl < current_sl - (10 * point))
                  {
                     m_trade.PositionModify(m_position.Ticket(), new_sl, current_tp);
                  }
               }
            }
         }
      }
   }
}

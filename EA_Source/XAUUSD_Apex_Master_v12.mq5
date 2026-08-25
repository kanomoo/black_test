//+------------------------------------------------------------------+
//|                                   XAUUSD_Apex_Master_v12.mq5     |
//|                    Copyright 2026, Apex Institutional Trading    |
//|                        Multi-TF Adaptive Scalping Engine v12.0   |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Apex Institutional Trading"
#property link      "https://www.mql5.com"
#property version   "12.00"
#property description "XAUUSD Adaptive ATR Volatility & Trend Master EA v12"
#property description "Engineered for Cent & Micro-Deposit Accounts (750 USC / $7.50 USD)"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\OrderInfo.mqh>

//--- Input Parameters ---
input group "=== Risk & Capital Management ==="
input double   InpRiskPercent       = 1.0;       // Risk Percent per Trade (%)
input double   InpMaxDailyDrawdown  = 3.0;       // Max Daily Equity Drawdown Limit (%)
input int      InpMaxConsecLosses   = 2;         // Max Consecutive Losses before Pause
input int      InpPauseHours        = 6;         // Pause Duration after Max Losses (Hours)
input double   InpFixedLot          = 0.0;       // Fixed Lot Size (0.0 = Auto Risk Sizing)

input group "=== ATR Volatility & Dynamic SL/TP ==="
input int      InpATRPeriod         = 14;        // ATR Period (M5)
input double   InpMinATR_Threshold  = 1.00;      // Minimum ATR Threshold (Avoid Flat Asian Markets)
input double   InpATR_SL_Multiplier = 1.5;       // ATR SL Multiplier (Dynamic Stop Loss)
input double   InpTargetRR          = 2.2;       // Target Risk-Reward Ratio (1:2.2)
input int      InpMinSLPips         = 200;       // Minimum SL in Pips ($2.00 Safety Floor)
input int      InpMaxSLPips         = 500;       // Maximum SL in Pips ($5.00 Safety Ceiling)

input group "=== Multi-Timeframe Trend & Filters ==="
input int      InpFastEMA           = 20;        // Fast EMA Period
input int      InpSlowEMA           = 50;        // Slow EMA Period
input int      InpRSI_Period        = 14;        // RSI Momentum Filter Period
input double   InpRSI_Buy_Min       = 50.0;      // Buy RSI Lower Threshold
input double   InpRSI_Buy_Max       = 68.0;      // Buy RSI Upper Threshold
input double   InpRSI_Sell_Min      = 32.0;      // Sell RSI Lower Threshold
input double   InpRSI_Sell_Max      = 50.0;      // Sell RSI Upper Threshold
input int      InpMaxSpreadPips     = 25;        // Maximum Allowed Spread in Pips

input group "=== Profit Management & Trailing ==="
input bool     InpUseBreakeven      = true;      // Move SL to Breakeven at 0.8 R
input double   InpBreakevenTrigger  = 0.8;      // Breakeven Trigger Ratio (x Risk)
input bool     InpUseTrailing       = true;      // Enable ATR Trailing Stop
input double   InpTrailingStepATR   = 1.2;      // Trailing Step ATR Multiplier

input group "=== Trading Time Windows (GMT+7) ==="
input bool     InpUseTimeFilter     = true;      // Enable Trading Time Window
input int      InpStartHour1        = 11;        // Session 1 Start Hour (Asian/London)
input int      InpEndHour1          = 16;        // Session 1 End Hour
input int      InpStartHour2        = 16;        // Session 2 Start Hour (NY Session)
input int      InpEndHour2          = 23;        // Session 2 End Hour

input group "=== System Identification ==="
input ulong    InpMagicNumber       = 120001;    // Magic Number for EA Orders
input string   InpTradeComment      = "Apex_v12"; // Order Comment

//--- Global Variables ---
CTrade         m_trade;
CPositionInfo  m_position;
COrderInfo     m_order;

int            m_handle_h4_fast     = INVALID_HANDLE;
int            m_handle_h4_slow     = INVALID_HANDLE;
int            m_handle_h1_fast     = INVALID_HANDLE;
int            m_handle_h1_slow     = INVALID_HANDLE;
int            m_handle_atr         = INVALID_HANDLE;
int            m_handle_rsi         = INVALID_HANDLE;

datetime       m_pause_until        = 0;
int            m_consec_losses      = 0;
double         m_day_start_equity   = 0.0;
int            m_last_day           = -1;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   
   // Initialize Indicator Handles (H4 + H1 Trend Alignment)
   m_handle_h4_fast = iMA(_Symbol, PERIOD_H4, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h4_slow = iMA(_Symbol, PERIOD_H4, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h1_fast = iMA(_Symbol, PERIOD_H1, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_h1_slow = iMA(_Symbol, PERIOD_H1, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   
   m_handle_atr      = iATR(_Symbol, _Period, InpATRPeriod);
   m_handle_rsi      = iRSI(_Symbol, _Period, InpRSI_Period, PRICE_CLOSE);
   
   if(m_handle_h4_fast == INVALID_HANDLE || m_handle_h4_slow == INVALID_HANDLE ||
      m_handle_h1_fast == INVALID_HANDLE || m_handle_h1_slow == INVALID_HANDLE ||
      m_handle_atr == INVALID_HANDLE || m_handle_rsi == INVALID_HANDLE)
   {
      Print("Error creating indicator handles in OnInit()");
      return INIT_FAILED;
   }
   
   m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   
   Print("XAUUSD Apex Master EA v12 Initialized Successfully. Magic: ", InpMagicNumber);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(m_handle_h4_fast);
   IndicatorRelease(m_handle_h4_slow);
   IndicatorRelease(m_handle_h1_fast);
   IndicatorRelease(m_handle_h1_slow);
   IndicatorRelease(m_handle_atr);
   IndicatorRelease(m_handle_rsi);
}

//+------------------------------------------------------------------+
//| Helper: Check Trading Time Window                                |
//+------------------------------------------------------------------+
bool IsTradingTime()
{
   if(!InpUseTimeFilter) return true;
   
   MqlDateTime dt;
   TimeCurrent(dt);
   
   int hour = dt.hour;
   bool session1 = (hour >= InpStartHour1 && hour < InpEndHour1);
   bool session2 = (hour >= InpStartHour2 && hour < InpEndHour2);
   
   return (session1 || session2);
}

//+------------------------------------------------------------------+
//| Helper: Calculate Dynamic Lot Size                               |
//+------------------------------------------------------------------+
double CalculateLotSize(double sl_distance_price)
{
   if(InpFixedLot > 0.0) return InpFixedLot;
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amount = balance * (InpRiskPercent / 100.0);
   
   double tick_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_val  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double point     = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   
   if(tick_size == 0 || tick_val == 0 || point == 0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   
   double points_at_risk = sl_distance_price / point;
   double value_per_lot  = (points_at_risk / (tick_size / point)) * tick_val;
   
   if(value_per_lot <= 0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   
   double lot = risk_amount / value_per_lot;
   
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
   // 1. Daily Reset & Drawdown Check
   MqlDateTime dt;
   TimeCurrent(dt);
   if(dt.day != m_last_day)
   {
      m_last_day = dt.day;
      m_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   }
   
   double curr_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double daily_dd_pct = (m_day_start_equity > 0) ? ((m_day_start_equity - curr_equity) / m_day_start_equity) * 100.0 : 0.0;
   
   if(daily_dd_pct >= InpMaxDailyDrawdown)
   {
      return;
   }
   
   // 2. Cooldown check
   if(TimeCurrent() < m_pause_until)
   {
      return;
   }
   
   // 3. Manage Open Positions (Breakeven & Trailing)
   ManageOpenPositions();
   
   // 4. Check if already holding a position
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
   if(open_positions > 0) return; // Allow 1 position at a time
   
   // 5. Filters: Time & Spread
   if(!IsTradingTime()) return;
   
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double spread_pips = (point > 0) ? (spread * point / 0.1) : spread;
   if(spread_pips > InpMaxSpreadPips) return;
   
   // 6. Indicators & Signal Logic
   double h4_fast[], h4_slow[], h1_fast[], h1_slow[], atr[], rsi[];
   ArraySetAsSeries(h4_fast, true); ArraySetAsSeries(h4_slow, true);
   ArraySetAsSeries(h1_fast, true); ArraySetAsSeries(h1_slow, true);
   ArraySetAsSeries(atr, true); ArraySetAsSeries(rsi, true);
   
   if(CopyBuffer(m_handle_h4_fast, 0, 0, 2, h4_fast) < 2) return;
   if(CopyBuffer(m_handle_h4_slow, 0, 0, 2, h4_slow) < 2) return;
   if(CopyBuffer(m_handle_h1_fast, 0, 0, 2, h1_fast) < 2) return;
   if(CopyBuffer(m_handle_h1_slow, 0, 0, 2, h1_slow) < 2) return;
   if(CopyBuffer(m_handle_atr, 0, 0, 2, atr) < 2) return;
   if(CopyBuffer(m_handle_rsi, 0, 0, 2, rsi) < 2) return;
   
   double current_atr = atr[0];
   double current_rsi = rsi[0];
   
   // Skip low volatility market
   if(current_atr < InpMinATR_Threshold) return;
   
   // Dual Trend Alignment (Both H4 and H1 must agree!)
   bool is_uptrend   = (h4_fast[0] > h4_slow[0]) && (h1_fast[0] > h1_slow[0]);
   bool is_downtrend = (h4_fast[0] < h4_slow[0]) && (h1_fast[0] < h1_slow[0]);
   
   // Candle confirmation on M5
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, _Period, 0, 3, rates) < 3) return;
   
   bool buy_candle = (rates[1].close > rates[1].open);
   bool sell_candle = (rates[1].close < rates[1].open);
   
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   // Calculate Dynamic ATR SL & TP
   double sl_distance = current_atr * InpATR_SL_Multiplier;
   double min_sl_dist = InpMinSLPips * point * 10;
   double max_sl_dist = InpMaxSLPips * point * 10;
   
   if(sl_distance < min_sl_dist) sl_distance = min_sl_dist;
   if(sl_distance > max_sl_dist) sl_distance = max_sl_dist;
   
   double tp_distance = sl_distance * InpTargetRR;
   
   // ENTRY LOGIC
   if(is_uptrend && buy_candle && current_rsi >= InpRSI_Buy_Min && current_rsi <= InpRSI_Buy_Max)
   {
      double sl = NormalizeDouble(ask - sl_distance, _Digits);
      double tp = NormalizeDouble(ask + tp_distance, _Digits);
      double lot = CalculateLotSize(sl_distance);
      
      if(m_trade.Buy(lot, _Symbol, ask, sl, tp, InpTradeComment))
      {
         Print("BUY Order Opened! Lot: ", lot, " SL: ", sl, " TP: ", tp);
      }
   }
   else if(is_downtrend && sell_candle && current_rsi >= InpRSI_Sell_Min && current_rsi <= InpRSI_Sell_Max)
   {
      double sl = NormalizeDouble(bid + sl_distance, _Digits);
      double tp = NormalizeDouble(bid - tp_distance, _Digits);
      double lot = CalculateLotSize(sl_distance);
      
      if(m_trade.Sell(lot, _Symbol, bid, sl, tp, InpTradeComment))
      {
         Print("SELL Order Opened! Lot: ", lot, " SL: ", sl, " TP: ", tp);
      }
   }
}

//+------------------------------------------------------------------+
//| Position Management (Breakeven & Trailing Stop)                  |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_position.SelectByIndex(i))
      {
         if(m_position.Symbol() == _Symbol && m_position.Magic() == InpMagicNumber)
         {
            double open_price = m_position.PriceOpen();
            double current_sl = m_position.StopLoss();
            double current_tp = m_position.TakeProfit();
            double current_price = m_position.PriceCurrent();
            ENUM_POSITION_TYPE pos_type = m_position.PositionType();
            
            double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
            double atr[];
            ArraySetAsSeries(atr, true);
            if(CopyBuffer(m_handle_atr, 0, 0, 1, atr) < 1) continue;
            
            if(pos_type == POSITION_TYPE_BUY)
            {
               double risk_dist = open_price - current_sl;
               if(risk_dist > 0 && InpUseBreakeven)
               {
                  if(current_price >= (open_price + risk_dist * InpBreakevenTrigger))
                  {
                     double new_sl = NormalizeDouble(open_price + (10 * point), _Digits);
                     if(current_sl < new_sl)
                     {
                        m_trade.PositionModify(m_position.Ticket(), new_sl, current_tp);
                        Print("Moved BUY to Breakeven: ", new_sl);
                     }
                  }
               }
               
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
               if(risk_dist > 0 && InpUseBreakeven)
               {
                  if(current_price <= (open_price - risk_dist * InpBreakevenTrigger))
                  {
                     double new_sl = NormalizeDouble(open_price - (10 * point), _Digits);
                     if(current_sl > new_sl || current_sl == 0)
                     {
                        m_trade.PositionModify(m_position.Ticket(), new_sl, current_tp);
                        Print("Moved SELL to Breakeven: ", new_sl);
                     }
                  }
               }
               
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

//+------------------------------------------------------------------+
//|                 XAUUSD Multi-TF Scalping EA v3.0 (Advanced)     |
//|        Multi-Timeframe Trend Following & Scalping Execution      |
//+------------------------------------------------------------------+
#property copyright "Antigravity EA Systems"
#property link      "https://www.mql5.com"
#property version   "3.00"
#property description "Advanced Multi-Timeframe Scalping EA for Gold (XAUUSD) with Partial Closure and Dynamic Red-Candle Low SL"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input group "=== Risk & Position Management ==="
input double         RiskPercent       = 2.5;         // Risk % per trade (2.5% default, up to 15%)
input int            SL_Buffer_Pips    = 150;         // SL Buffer below Red Candle Low in Points (150 = $1.50)
input int            MagicNumber       = 300001;      // Magic Number

input group "=== Take Profit & Partial Close (RR Levels) ==="
input bool           UsePartialClose   = true;        // Enable Partial Closure at RR Levels
input double         PartialClosePct   = 50.0;        // Partial Close % at each RR level (50%)
input double         RR_Level_1        = 2.0;         // RR Level 1 (1:2)
input double         RR_Level_2        = 3.0;         // RR Level 2 (1:3)
input double         RR_Level_3        = 5.0;         // RR Level 3 (1:5)
input double         RR_Level_4        = 10.0;        // RR Level 4 (1:10)
input double         RR_Level_5        = 15.0;        // RR Level 5 (1:15)

input group "=== Trading Hours (GMT+7 Thailand Time) ==="
input bool           UseTradeHours     = true;        // Enable Trading Hours Filter
input string         Session1_Start    = "11:00";     // Session 1 Start (11:00 AM GMT+7)
input string         Session1_End      = "16:00";     // Session 1 End (4:00 PM GMT+7)
input string         Session2_Start    = "22:00";     // Session 2 Start (10:00 PM GMT+7)
input string         Session2_End      = "02:00";     // Session 2 End (2:00 AM GMT+7)
input bool           HoldOutsideHours  = true;        // Hold open trades outside hours (No new entries)

//--- Global Variables
CTrade trade;
CPositionInfo posInfo;
CSymbolInfo symInfo;

int handle_ema20_h4, handle_ema50_h4;
int handle_ema20_h1, handle_ema50_h1;
int handle_ema20_m30, handle_ema50_m30;

// Track Partial Closure state per position
struct POSITION_STATE {
    ulong  ticket;
    bool   tp1_closed;
    bool   tp2_closed;
    bool   tp3_closed;
    bool   tp4_closed;
    double initial_sl_distance;
};

POSITION_STATE pos_states[10];

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    trade.SetExpertMagicNumber(MagicNumber);
    trade.SetDeviationInPoints(10);
    
    if(!symInfo.Name(_Symbol)) {
        Print("Failed to initialize symbol info for: ", _Symbol);
        return INIT_FAILED;
    }
    symInfo.RefreshRates();
    
    // Initialize HTF Indicators (M30, H1, H4)
    handle_ema20_h4  = iMA(_Symbol, PERIOD_H4, 20, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema50_h4  = iMA(_Symbol, PERIOD_H4, 50, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema20_h1  = iMA(_Symbol, PERIOD_H1, 20, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema50_h1  = iMA(_Symbol, PERIOD_H1, 50, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema20_m30 = iMA(_Symbol, PERIOD_M30, 20, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema50_m30 = iMA(_Symbol, PERIOD_M30, 50, 0, MODE_EMA, PRICE_CLOSE);
    
    if(handle_ema20_h4 == INVALID_HANDLE || handle_ema50_h4 == INVALID_HANDLE ||
       handle_ema20_h1 == INVALID_HANDLE || handle_ema50_h1 == INVALID_HANDLE ||
       handle_ema20_m30 == INVALID_HANDLE || handle_ema50_m30 == INVALID_HANDLE) {
        Print("Error creating indicator handles.");
        return INIT_FAILED;
    }
    
    ResetStates();
    Print("EA v3.0 Initialized Successfully for ", _Symbol);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    IndicatorRelease(handle_ema20_h4);
    IndicatorRelease(handle_ema50_h4);
    IndicatorRelease(handle_ema20_h1);
    IndicatorRelease(handle_ema50_h1);
    IndicatorRelease(handle_ema20_m30);
    IndicatorRelease(handle_ema50_m30);
    Print("EA Deinitialized. Reason code: ", reason);
}

//+------------------------------------------------------------------+
//| Reset tracked states                                             |
//+------------------------------------------------------------------+
void ResetStates()
{
    for(int i = 0; i < 10; i++) {
        pos_states[i].ticket = 0;
        pos_states[i].tp1_closed = false;
        pos_states[i].tp2_closed = false;
        pos_states[i].tp3_closed = false;
        pos_states[i].tp4_closed = false;
        pos_states[i].initial_sl_distance = 0;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    symInfo.RefreshRates();
    
    // Manage existing position partial closes and breakeven
    ManageOpenPositions();
    
    // Check trading hours for NEW entries
    if(!IsInTradingHours()) return;
    
    // Signal check & Trade execution
    CheckForM5Signal();
}

//+------------------------------------------------------------------+
//| Check Trading Hours (GMT+7 Thailand Time)                        |
//+------------------------------------------------------------------+
bool IsInTradingHours()
{
    if(!UseTradeHours) return true;
    
    MqlDateTime now;
    TimeToStruct(TimeCurrent() + 25200, now); // GMT+7 offset (7 * 3600 = 25200s)
    
    int curr_min = now.hour * 60 + now.min;
    
    int start1 = TimeToMinutes(Session1_Start);
    int end1   = TimeToMinutes(Session1_End);
    int start2 = TimeToMinutes(Session2_Start);
    int end2   = TimeToMinutes(Session2_End);
    
    if(CheckSession(curr_min, start1, end1)) return true;
    if(CheckSession(curr_min, start2, end2)) return true;
    
    return false;
}

int TimeToMinutes(string t_str)
{
    string parts[];
    if(StringSplit(t_str, ':', parts) == 2) {
        return (int)StringToInteger(parts[0]) * 60 + (int)StringToInteger(parts[1]);
    }
    return 0;
}

bool CheckSession(int curr, int start, int end)
{
    if(start <= end)
        return (curr >= start && curr < end);
    else
        return (curr >= start || curr < end);
}

//+------------------------------------------------------------------+
//| Multi-Timeframe Trend Filter (H4, H1, M30)                       |
//+------------------------------------------------------------------+
int GetHTFTrendDirection()
{
    double ema20_h4[2], ema50_h4[2];
    double ema20_h1[2], ema50_h1[2];
    double ema20_m30[2], ema50_m30[2];
    
    // Array buffers for HTF EMA
    if(CopyBuffer(handle_ema20_h4, 0, 0, 2, ema20_h4) <= 0 || CopyBuffer(handle_ema50_h4, 0, 0, 2, ema50_h4) <= 0 ||
       CopyBuffer(handle_ema20_h1, 0, 0, 2, ema20_h1) <= 0 || CopyBuffer(handle_ema50_h1, 0, 0, 2, ema50_h1) <= 0 ||
       CopyBuffer(handle_ema20_m30, 0, 0, 2, ema20_m30) <= 0 || CopyBuffer(handle_ema50_m30, 0, 0, 2, ema50_m30) <= 0)
        return 0;
        
    double close_h4  = iClose(_Symbol, PERIOD_H4, 1);
    double close_h1  = iClose(_Symbol, PERIOD_H1, 1);
    double close_m30 = iClose(_Symbol, PERIOD_M30, 1);
    
    bool h4_up  = (close_h4 > ema50_h4[1])  && (ema20_h4[1] > ema50_h4[1]);
    bool h1_up  = (close_h1 > ema50_h1[1])  && (ema20_h1[1] > ema50_h1[1]);
    bool m30_up = (close_m30 > ema50_m30[1]) && (ema20_m30[1] > ema50_m30[1]);
    
    bool h4_down  = (close_h4 < ema50_h4[1])  && (ema20_h4[1] < ema50_h4[1]);
    bool h1_down  = (close_h1 < ema50_h1[1])  && (ema20_h1[1] < ema50_h1[1]);
    bool m30_down = (close_m30 < ema50_m30[1]) && (ema20_m30[1] < ema50_m30[1]);
    
    if(h4_up && h1_up && m30_up) return 1;    // Strong Uptrend
    if(h4_down && h1_down && m30_down) return -1; // Strong Downtrend
    
    return 0;
}

//+------------------------------------------------------------------+
//| Check M5 Entry Confirmation Signal                               |
//+------------------------------------------------------------------+
void CheckForM5Signal()
{
    if(CountOpenPositions() > 0) return;
    
    int trend = GetHTFTrendDirection();
    if(trend == 0) return;
    
    double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
    double close_1 = iClose(_Symbol, PERIOD_M5, 1);
    
    // Bullish Close (Green Candle: Close > Open) in Uptrend
    if(trend == 1 && close_1 > open_1) {
        ExecuteTrade(1);
    }
    // Bearish Close (Red Candle: Close < Open) in Downtrend
    else if(trend == -1 && close_1 < open_1) {
        ExecuteTrade(-1);
    }
}

//+------------------------------------------------------------------+
//| Find Previous Red Candle Low for Buy / Green Candle High for Sell|
//+------------------------------------------------------------------+
double GetPreviousRedCandleLow()
{
    for(int i = 1; i <= 10; i++) {
        double o = iOpen(_Symbol, PERIOD_M5, i);
        double c = iClose(_Symbol, PERIOD_M5, i);
        if(c < o) { // Red Candle
            return iLow(_Symbol, PERIOD_M5, i);
        }
    }
    return iLow(_Symbol, PERIOD_M5, 1);
}

double GetPreviousGreenCandleHigh()
{
    for(int i = 1; i <= 10; i++) {
        double o = iOpen(_Symbol, PERIOD_M5, i);
        double c = iClose(_Symbol, PERIOD_M5, i);
        if(c > o) { // Green Candle
            return iHigh(_Symbol, PERIOD_M5, i);
        }
    }
    return iHigh(_Symbol, PERIOD_M5, 1);
}

//+------------------------------------------------------------------+
//| Execute Trade Order                                              |
//+------------------------------------------------------------------+
void ExecuteTrade(int trade_type)
{
    double entry_price, sl_price, tp_price;
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    
    if(trade_type == 1) { // BUY
        entry_price = ask;
        double red_low = GetPreviousRedCandleLow();
        sl_price = red_low - (SL_Buffer_Pips * symInfo.Point());
        double risk_dist = entry_price - sl_price;
        if(risk_dist <= 0) return;
        tp_price = entry_price + (risk_dist * RR_Level_5);
        
    } else { // SELL
        entry_price = bid;
        double green_high = GetPreviousGreenCandleHigh();
        sl_price = green_high + (SL_Buffer_Pips * symInfo.Point());
        double risk_dist = sl_price - entry_price;
        if(risk_dist <= 0) return;
        tp_price = entry_price - (risk_dist * RR_Level_5);
    }
    
    double sl_distance = MathAbs(entry_price - sl_price);
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double risk_amount = balance * (RiskPercent / 100.0);
    double lot_size = CalculateLotSize(risk_amount, sl_distance);
    
    if(lot_size < symInfo.LotsMin()) return;
    
    if(trade_type == 1) {
        if(trade.Buy(lot_size, _Symbol, entry_price, sl_price, tp_price, "XAUUSD Scalp Buy v3")) {
            ulong ticket = trade.ResultOrder();
            RegisterNewPosition(ticket, sl_distance);
            Print("BUY Order Opened - Ticket: ", ticket, " Lot: ", lot_size, " Entry: ", entry_price, " SL: ", sl_price);
        }
    } else {
        if(trade.Sell(lot_size, _Symbol, entry_price, sl_price, tp_price, "XAUUSD Scalp Sell v3")) {
            ulong ticket = trade.ResultOrder();
            RegisterNewPosition(ticket, sl_distance);
            Print("SELL Order Opened - Ticket: ", ticket, " Lot: ", lot_size, " Entry: ", entry_price, " SL: ", sl_price);
        }
    }
}

void RegisterNewPosition(ulong ticket, double sl_dist)
{
    for(int i = 0; i < 10; i++) {
        if(pos_states[i].ticket == 0) {
            pos_states[i].ticket = ticket;
            pos_states[i].tp1_closed = false;
            pos_states[i].tp2_closed = false;
            pos_states[i].tp3_closed = false;
            pos_states[i].tp4_closed = false;
            pos_states[i].initial_sl_distance = sl_dist;
            break;
        }
    }
}

//+------------------------------------------------------------------+
//| Calculate Lot Size                                               |
//+------------------------------------------------------------------+
double CalculateLotSize(double risk_amount, double sl_distance)
{
    if(sl_distance <= 0) return symInfo.LotsMin();
    
    double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double point_size = symInfo.Point();
    if(tick_val <= 0 || point_size <= 0) return symInfo.LotsMin();
    
    double lot = risk_amount / ((sl_distance / point_size) * tick_val);
    double step = symInfo.LotsStep();
    if(step > 0) lot = MathFloor(lot / step) * step;
    
    lot = NormalizeDouble(lot, 2);
    if(lot < symInfo.LotsMin()) lot = symInfo.LotsMin();
    if(lot > symInfo.LotsMax()) lot = symInfo.LotsMax();
    
    return lot;
}

//+------------------------------------------------------------------+
//| Manage Open Positions (Partial Close at RR 1:2, 1:3, 1:5, 1:10)  |
//+------------------------------------------------------------------+
void ManageOpenPositions()
{
    for(int i = 0; i < PositionsTotal(); i++) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Magic() == MagicNumber && posInfo.Symbol() == _Symbol) {
                ulong ticket = posInfo.Ticket();
                int state_idx = GetStateIndex(ticket);
                
                double entry = posInfo.PriceOpen();
                double current_sl = posInfo.StopLoss();
                double current_tp = posInfo.TakeProfit();
                double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                double current_price = (posInfo.PositionType() == POSITION_TYPE_BUY) ? bid : ask;
                
                double profit = (posInfo.PositionType() == POSITION_TYPE_BUY) ? (current_price - entry) : (entry - current_price);
                if(profit <= 0) continue;
                
                double initial_risk = (state_idx >= 0 && pos_states[state_idx].initial_sl_distance > 0) 
                                      ? pos_states[state_idx].initial_sl_distance 
                                      : MathAbs(entry - current_sl);
                if(initial_risk <= 0) continue;
                
                double current_rr = profit / initial_risk;
                
                // RR 1:2.0 -> Breakeven + 50% Partial Close
                if(current_rr >= RR_Level_1 && (state_idx < 0 || !pos_states[state_idx].tp1_closed)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (profit * 0.5), symInfo.Digits()) : NormalizeDouble(entry - (profit * 0.5), symInfo.Digits());
                    if(UsePartialClose) PartialClosePosition(ticket, PartialClosePct);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(state_idx >= 0) pos_states[state_idx].tp1_closed = true;
                    Print("RR 1:", RR_Level_1, " Reached! Partial Close 50% & SL Moved to ", new_sl);
                }
                
                // RR 1:3.0 -> Lock 50% Profit
                else if(current_rr >= RR_Level_2 && (state_idx < 0 || !pos_states[state_idx].tp2_closed)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (profit * 0.5), symInfo.Digits()) : NormalizeDouble(entry - (profit * 0.5), symInfo.Digits());
                    if(UsePartialClose) PartialClosePosition(ticket, PartialClosePct);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(state_idx >= 0) pos_states[state_idx].tp2_closed = true;
                    Print("RR 1:", RR_Level_2, " Reached! Partial Close 50%");
                }
            }
        }
    }
}

int GetStateIndex(ulong ticket)
{
    for(int i = 0; i < 10; i++) {
        if(pos_states[i].ticket == ticket) return i;
    }
    return -1;
}

void PartialClosePosition(ulong ticket, double pct)
{
    if(posInfo.SelectByTicket(ticket)) {
        double current_volume = posInfo.Volume();
        double close_volume = NormalizeDouble(current_volume * (pct / 100.0), 2);
        if(close_volume >= symInfo.LotsMin() && close_volume < current_volume) {
            trade.PositionClosePartial(ticket, close_volume);
            Print("Partial Close Executed: ", close_volume, " Lots for Position Ticket: ", ticket);
        }
    }
}

//+------------------------------------------------------------------+
//| Count Open Positions                                             |
//+------------------------------------------------------------------+
int CountOpenPositions()
{
    int count = 0;
    for(int i = 0; i < PositionsTotal(); i++) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Magic() == MagicNumber && posInfo.Symbol() == _Symbol) {
                count++;
            }
        }
    }
    return count;
}

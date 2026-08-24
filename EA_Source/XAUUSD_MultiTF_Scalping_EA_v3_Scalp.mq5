//+------------------------------------------------------------------+
//|             XAUUSD Multi-TF Scalping EA v3.0 (Scalp Edition)     |
//|    Optimized for HFM Cent Account (XAUUSDc) & Standard Accounts  |
//+------------------------------------------------------------------+
#property copyright "Antigravity EA Systems"
#property link      "https://www.mql5.com"
#property version   "3.20"
#property description "Optimized Short-Term Scalper for Gold (XAUUSD / XAUUSDc) with Dynamic HFM Cent Lot Sizing"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input group "=== Scalper Risk & Position Management ==="
input double         RiskPercent       = 2.5;         // Risk % per trade (2.5% safe, 5.0% max)
input int            SL_Buffer_Pips    = 100;         // Tight Scalp SL Buffer in Points (100 = $1.00)
input int            MagicNumber       = 300002;      // Magic Number

input group "=== Scalper Take Profit & Partial Close ==="
input bool           UsePartialClose   = true;        // Enable Partial Closure at RR Levels
input double         RR_Level_1        = 1.5;         // Scalp RR 1 (1:1.5) -> Lock BE + Close 30%
input double         RR_Level_2        = 3.0;         // Scalp RR 2 (1:3.0) -> Lock 1.0 RR + Close 40%
input double         RR_Level_3        = 5.0;         // Scalp RR 3 (1:5.0) -> Target Runner Close 30%

input group "=== Peak Scalping Hours (GMT+7 Thailand Time) ==="
input bool           UseTradeHours     = true;        // Enable Peak Scalping Hours Filter
input string         Session1_Start    = "11:00";     // Session 1 (London Open: 11:00 AM GMT+7)
input string         Session1_End      = "16:00";     // Session 1 End (4:00 PM GMT+7)
input string         Session2_Start    = "20:00";     // Session 2 (US Overlap: 8:00 PM GMT+7)
input string         Session2_End      = "02:00";     // Session 2 End (2:00 AM GMT+7)

//--- Global Variables
CTrade trade;
CPositionInfo posInfo;
CSymbolInfo symInfo;

int handle_ema5_m5, handle_ema20_m5, handle_ema50_m5;

struct SCALP_STATE {
    ulong  ticket;
    bool   tp1_closed;
    bool   tp2_closed;
    double initial_sl_distance;
};

SCALP_STATE scalp_states[20];

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
    
    // Fast Momentum EMA Handles on M5 for _Symbol (Auto-detects XAUUSDc)
    handle_ema5_m5  = iMA(_Symbol, PERIOD_M5, 5, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema20_m5 = iMA(_Symbol, PERIOD_M5, 20, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema50_m5 = iMA(_Symbol, PERIOD_M5, 50, 0, MODE_EMA, PRICE_CLOSE);
    
    if(handle_ema5_m5 == INVALID_HANDLE || handle_ema20_m5 == INVALID_HANDLE || handle_ema50_m5 == INVALID_HANDLE) {
        Print("Error creating indicator handles for ", _Symbol);
        return INIT_FAILED;
    }
    
    ResetStates();
    Print("EA v3.0 Scalp Edition (HFM Cent Ready) Initialized Successfully for ", _Symbol);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    IndicatorRelease(handle_ema5_m5);
    IndicatorRelease(handle_ema20_m5);
    IndicatorRelease(handle_ema50_m5);
    Print("EA Scalp Edition Deinitialized. Reason: ", reason);
}

void ResetStates()
{
    for(int i = 0; i < 20; i++) {
        scalp_states[i].ticket = 0;
        scalp_states[i].tp1_closed = false;
        scalp_states[i].tp2_closed = false;
        scalp_states[i].initial_sl_distance = 0;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    symInfo.RefreshRates();
    
    // Manage Scalper partial close and breakeven
    ManageScalpPositions();
    
    // Check peak scalping hours
    if(!IsInTradingHours()) return;
    
    // Check fast momentum entry
    CheckForScalpSignal();
}

//+------------------------------------------------------------------+
//| Check Scalping Hours (GMT+7 Thailand Time)                      |
//+------------------------------------------------------------------+
bool IsInTradingHours()
{
    if(!UseTradeHours) return true;
    
    MqlDateTime now;
    TimeToStruct(TimeCurrent() + 25200, now); // GMT+7
    int curr_min = now.hour * 60 + now.min;
    
    int start1 = TimeToMin(Session1_Start);
    int end1   = TimeToMin(Session1_End);
    int start2 = TimeToMin(Session2_Start);
    int end2   = TimeToMin(Session2_End);
    
    if(CheckSession(curr_min, start1, end1)) return true;
    if(CheckSession(curr_min, start2, end2)) return true;
    
    return false;
}

int TimeToMin(string t_str)
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
//| Check M5 Fast Scalp Signal                                       |
//+------------------------------------------------------------------+
void CheckForScalpSignal()
{
    if(CountOpenPositions() > 0) return;
    
    double ema5[], ema20[], ema50[];
    if(CopyBuffer(handle_ema5_m5, 0, 0, 2, ema5) <= 0 ||
       CopyBuffer(handle_ema20_m5, 0, 0, 2, ema20) <= 0 ||
       CopyBuffer(handle_ema50_m5, 0, 0, 2, ema50) <= 0)
        return;
        
    double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
    double close_1 = iClose(_Symbol, PERIOD_M5, 1);
    double prev_h  = iHigh(_Symbol, PERIOD_M5, 2);
    double prev_l  = iLow(_Symbol, PERIOD_M5, 2);
    
    // Bullish Momentum: Close > EMA50 && EMA5 > EMA20 && Green Candle Close > Prev High
    bool buy_signal = (close_1 > ema50[0]) && (ema5[0] > ema20[0]) && (close_1 > open_1) && (close_1 > prev_h);
    
    // Bearish Momentum: Close < EMA50 && EMA5 < EMA20 && Red Candle Close < Prev Low
    bool sell_signal = (close_1 < ema50[0]) && (ema5[0] < ema20[0]) && (close_1 < open_1) && (close_1 < prev_l);
    
    if(buy_signal) {
        ExecuteScalpTrade(1);
    } else if(sell_signal) {
        ExecuteScalpTrade(-1);
    }
}

//+------------------------------------------------------------------+
//| Get Red Candle Low for Buy / Green Candle High for Sell          |
//+------------------------------------------------------------------+
double GetRedLow()
{
    for(int i = 1; i <= 5; i++) {
        if(iClose(_Symbol, PERIOD_M5, i) < iOpen(_Symbol, PERIOD_M5, i)) {
            return iLow(_Symbol, PERIOD_M5, i);
        }
    }
    return iLow(_Symbol, PERIOD_M5, 1);
}

double GetGreenHigh()
{
    for(int i = 1; i <= 5; i++) {
        if(iClose(_Symbol, PERIOD_M5, i) > iOpen(_Symbol, PERIOD_M5, i)) {
            return iHigh(_Symbol, PERIOD_M5, i);
        }
    }
    return iHigh(_Symbol, PERIOD_M5, 1);
}

//+------------------------------------------------------------------+
//| Execute Scalp Trade                                              |
//+------------------------------------------------------------------+
void ExecuteScalpTrade(int trade_type)
{
    double entry_price, sl_price, tp_price;
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    
    if(trade_type == 1) { // BUY
        entry_price = ask;
        double red_low = GetRedLow();
        sl_price = red_low - (SL_Buffer_Pips * symInfo.Point());
        double risk_dist = entry_price - sl_price;
        if(risk_dist <= 0) return;
        tp_price = entry_price + (risk_dist * RR_Level_3);
        
    } else { // SELL
        entry_price = bid;
        double green_high = GetGreenHigh();
        sl_price = green_high + (SL_Buffer_Pips * symInfo.Point());
        double risk_dist = sl_price - entry_price;
        if(risk_dist <= 0) return;
        tp_price = entry_price - (risk_dist * RR_Level_3);
    }
    
    double sl_distance = MathAbs(entry_price - sl_price);
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double risk_amount = balance * (RiskPercent / 100.0);
    double lot_size = CalculateLotSize(risk_amount, sl_distance);
    
    if(lot_size < symInfo.LotsMin()) lot_size = symInfo.LotsMin();
    
    if(trade_type == 1) {
        if(trade.Buy(lot_size, _Symbol, entry_price, sl_price, tp_price, "XAUUSD Scalp Buy v3 Scalp")) {
            ulong ticket = trade.ResultOrder();
            RegisterScalpState(ticket, sl_distance);
            Print("SCALP BUY Opened on ", _Symbol, " - Ticket: ", ticket, " Lot: ", lot_size, " Entry: ", entry_price, " SL: ", sl_price);
        }
    } else {
        if(trade.Sell(lot_size, _Symbol, entry_price, sl_price, tp_price, "XAUUSD Scalp Sell v3 Scalp")) {
            ulong ticket = trade.ResultOrder();
            RegisterScalpState(ticket, sl_distance);
            Print("SCALP SELL Opened on ", _Symbol, " - Ticket: ", ticket, " Lot: ", lot_size, " Entry: ", entry_price, " SL: ", sl_price);
        }
    }
}

void RegisterScalpState(ulong ticket, double sl_dist)
{
    for(int i = 0; i < 20; i++) {
        if(scalp_states[i].ticket == 0) {
            scalp_states[i].ticket = ticket;
            scalp_states[i].tp1_closed = false;
            scalp_states[i].tp2_closed = false;
            scalp_states[i].initial_sl_distance = sl_dist;
            break;
        }
    }
}

//+------------------------------------------------------------------+
//| Calculate Lot Size supporting HFM Cent Account (XAUUSDc)         |
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
    
    double min_lot = symInfo.LotsMin();
    double max_lot = symInfo.LotsMax();
    
    if(lot < min_lot) lot = min_lot;
    if(lot > max_lot) lot = max_lot;
    
    return NormalizeDouble(lot, (min_lot < 0.01) ? 4 : 2);
}

//+------------------------------------------------------------------+
//| Manage Scalp Positions (3-Tier Scalper Partial Close)            |
//+------------------------------------------------------------------+
void ManageScalpPositions()
{
    for(int i = 0; i < PositionsTotal(); i++) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Magic() == MagicNumber && posInfo.Symbol() == _Symbol) {
                ulong ticket = posInfo.Ticket();
                int idx = GetScalpStateIndex(ticket);
                
                double entry = posInfo.PriceOpen();
                double current_sl = posInfo.StopLoss();
                double current_tp = posInfo.TakeProfit();
                double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                double current_price = (posInfo.PositionType() == POSITION_TYPE_BUY) ? bid : ask;
                
                double profit = (posInfo.PositionType() == POSITION_TYPE_BUY) ? (current_price - entry) : (entry - current_price);
                if(profit <= 0) continue;
                
                double initial_risk = (idx >= 0 && scalp_states[idx].initial_sl_distance > 0) 
                                      ? scalp_states[idx].initial_sl_distance 
                                      : MathAbs(entry - current_sl);
                if(initial_risk <= 0) continue;
                
                double current_rr = profit / initial_risk;
                
                // Tier 1: RR 1:1.5 -> Lock Breakeven + Partial Close 30%
                if(current_rr >= RR_Level_1 && (idx < 0 || !scalp_states[idx].tp1_closed)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 0.2), symInfo.Digits()) : NormalizeDouble(entry - (initial_risk * 0.2), symInfo.Digits());
                    if(UsePartialClose) PartialClosePosition(ticket, 30.0);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) scalp_states[idx].tp1_closed = true;
                    Print("Scalp RR 1:", RR_Level_1, " Reached! Partial Close 30% & SL Moved to BE+");
                }
                
                // Tier 2: RR 1:3.0 -> Lock 1.0 RR + Partial Close 40%
                else if(current_rr >= RR_Level_2 && (idx < 0 || !scalp_states[idx].tp2_closed)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 1.0), symInfo.Digits()) : NormalizeDouble(entry - (initial_risk * 1.0), symInfo.Digits());
                    if(UsePartialClose) PartialClosePosition(ticket, 40.0);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) scalp_states[idx].tp2_closed = true;
                    Print("Scalp RR 1:", RR_Level_2, " Reached! Partial Close 40% & SL Moved to RR 1.0");
                }
            }
        }
    }
}

int GetScalpStateIndex(ulong ticket)
{
    for(int i = 0; i < 20; i++) {
        if(scalp_states[i].ticket == ticket) return i;
    }
    return -1;
}

void PartialClosePosition(ulong ticket, double pct)
{
    if(posInfo.SelectByTicket(ticket)) {
        double current_volume = posInfo.Volume();
        double min_lot = symInfo.LotsMin();
        double close_volume = NormalizeDouble(current_volume * (pct / 100.0), (min_lot < 0.01) ? 4 : 2);
        if(close_volume >= min_lot && close_volume < current_volume) {
            trade.PositionClosePartial(ticket, close_volume);
            Print("Scalp Partial Close: ", close_volume, " Lots for Ticket: ", ticket);
        }
    }
}

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

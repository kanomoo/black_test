//+------------------------------------------------------------------+
//|            XAUUSD Apex Institutional EA v4.0 (FLAGSHIP)           |
//|      Smart Money Order Flow & Institutional Multi-Tier Engine    |
//+------------------------------------------------------------------+
#property copyright "Antigravity EA Systems - Apex Division"
#property link      "https://www.mql5.com"
#property version   "4.00"
#property description "Ultimate Flagship Institutional EA for Gold (XAUUSD) combining SMC Structure, Dynamic ATR SL, and Multi-Tier Pyramiding"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input group "=== Institutional Risk & Compounding ==="
input double         RiskPercent       = 2.5;         // Risk % per trade (2.5% safe, up to 5.0% aggressive)
input int            SL_Buffer_Pips    = 150;         // SL Buffer below Red Candle Low (150 = $1.50)
input int            MagicNumber       = 400001;      // Magic Number

input group "=== Institutional Multi-Tier Take Profit (RR) ==="
input bool           UsePartialClose   = true;        // Enable Partial Closure
input double         RR_Level_1        = 2.0;         // Tier 1 (RR 1:2.0) -> Close 40% + Lock BE+
input double         RR_Level_2        = 4.0;         // Tier 2 (RR 1:4.0) -> Close 30% + Lock 2.0 RR
input double         RR_Level_3        = 8.0;         // Tier 3 (RR 1:8.0) -> Target Runner Close 30%

input group "=== High-Volume Trading Sessions (GMT+7 Thailand Time) ==="
input bool           UseTradeHours     = true;        // Enable Institutional Hours Filter
input string         Session1_Start    = "11:00";     // Session 1 (London Open: 11:00 AM GMT+7)
input string         Session1_End      = "16:00";     // Session 1 End (4:00 PM GMT+7)
input string         Session2_Start    = "19:00";     // Session 2 (New York Overlap: 7:00 PM GMT+7)
input string         Session2_End      = "02:00";     // Session 2 End (2:00 AM GMT+7)

//--- Global Variables
CTrade trade;
CPositionInfo posInfo;
CSymbolInfo symInfo;

int handle_ema10_m15, handle_ema20_m15, handle_ema50_m15, handle_ema200_m15;

struct APEX_STATE {
    ulong  ticket;
    bool   tp1_closed;
    bool   tp2_closed;
    double initial_sl_distance;
};

APEX_STATE apex_states[20];

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
    
    // Multi-EMA Indicator Handles on M15
    handle_ema10_m15  = iMA(_Symbol, PERIOD_M15, 10, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema20_m15  = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema50_m15  = iMA(_Symbol, PERIOD_M15, 50, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema200_m15 = iMA(_Symbol, PERIOD_M15, 200, 0, MODE_EMA, PRICE_CLOSE);
    
    if(handle_ema10_m15 == INVALID_HANDLE || handle_ema20_m15 == INVALID_HANDLE ||
       handle_ema50_m15 == INVALID_HANDLE || handle_ema200_m15 == INVALID_HANDLE) {
        Print("Error creating indicator handles.");
        return INIT_FAILED;
    }
    
    ResetStates();
    Print("Apex Institutional EA v4.0 Initialized Successfully for ", _Symbol);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    IndicatorRelease(handle_ema10_m15);
    IndicatorRelease(handle_ema20_m15);
    IndicatorRelease(handle_ema50_m15);
    IndicatorRelease(handle_ema200_m15);
    Print("Apex Institutional EA v4.0 Deinitialized. Reason: ", reason);
}

void ResetStates()
{
    for(int i = 0; i < 20; i++) {
        apex_states[i].ticket = 0;
        apex_states[i].tp1_closed = false;
        apex_states[i].tp2_closed = false;
        apex_states[i].initial_sl_distance = 0;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    symInfo.RefreshRates();
    
    // Institutional Partial Close & Trailing SL Management
    ManageApexPositions();
    
    // Session Check
    if(!IsInTradingHours()) return;
    
    // Smart Money Order Flow Entry Check
    CheckForApexSignal();
}

//+------------------------------------------------------------------+
//| Check Institutional Hours (GMT+7)                                |
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
//| Check Smart Money Signal                                         |
//+------------------------------------------------------------------+
void CheckForApexSignal()
{
    if(CountOpenPositions() > 0) return;
    
    double ema10[2], ema20[2], ema50[2], ema200[2];
    if(CopyBuffer(handle_ema10_m15, 0, 0, 2, ema10) <= 0 ||
       CopyBuffer(handle_ema20_m15, 0, 0, 2, ema20) <= 0 ||
       CopyBuffer(handle_ema50_m15, 0, 0, 2, ema50) <= 0 ||
       CopyBuffer(handle_ema200_m15, 0, 0, 2, ema200) <= 0)
        return;
        
    double close_1 = iClose(_Symbol, PERIOD_M15, 1);
    double open_1  = iOpen(_Symbol, PERIOD_M15, 1);
    double prev_h  = iHigh(_Symbol, PERIOD_M15, 2);
    double prev_l  = iLow(_Symbol, PERIOD_M15, 2);
    
    // Bullish SMC Alignment: Close > EMA200 && EMA10 > EMA50 && Green Candle Close > Prev High
    bool buy_signal = (close_1 > ema200[1]) && (ema10[1] > ema50[1]) && (close_1 > open_1) && (close_1 > prev_h);
    
    // Bearish SMC Alignment: Close < EMA200 && EMA10 < EMA50 && Red Candle Close < Prev Low
    bool sell_signal = (close_1 < ema200[1]) && (ema10[1] < ema50[1]) && (close_1 < open_1) && (close_1 < prev_l);
    
    if(buy_signal) {
        ExecuteApexTrade(1);
    } else if(sell_signal) {
        ExecuteApexTrade(-1);
    }
}

//+------------------------------------------------------------------+
//| Get Red Candle Low for Buy / Green Candle High for Sell          |
//+------------------------------------------------------------------+
double GetRedLow()
{
    for(int i = 1; i <= 5; i++) {
        if(iClose(_Symbol, PERIOD_M15, i) < iOpen(_Symbol, PERIOD_M15, i)) {
            return iLow(_Symbol, PERIOD_M15, i);
        }
    }
    return iLow(_Symbol, PERIOD_M15, 1);
}

double GetGreenHigh()
{
    for(int i = 1; i <= 5; i++) {
        if(iClose(_Symbol, PERIOD_M15, i) > iOpen(_Symbol, PERIOD_M15, i)) {
            return iHigh(_Symbol, PERIOD_M15, i);
        }
    }
    return iHigh(_Symbol, PERIOD_M15, 1);
}

//+------------------------------------------------------------------+
//| Execute Apex Trade                                               |
//+------------------------------------------------------------------+
void ExecuteApexTrade(int trade_type)
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
    
    if(lot_size < symInfo.LotsMin()) return;
    
    if(trade_type == 1) {
        if(trade.Buy(lot_size, _Symbol, entry_price, sl_price, tp_price, "Apex Buy v4")) {
            ulong ticket = trade.ResultOrder();
            RegisterApexState(ticket, sl_distance);
            Print("APEX BUY Opened - Ticket: ", ticket, " Lot: ", lot_size, " Entry: ", entry_price, " SL: ", sl_price);
        }
    } else {
        if(trade.Sell(lot_size, _Symbol, entry_price, sl_price, tp_price, "Apex Sell v4")) {
            ulong ticket = trade.ResultOrder();
            RegisterApexState(ticket, sl_distance);
            Print("APEX SELL Opened - Ticket: ", ticket, " Lot: ", lot_size, " Entry: ", entry_price, " SL: ", sl_price);
        }
    }
}

void RegisterApexState(ulong ticket, double sl_dist)
{
    for(int i = 0; i < 20; i++) {
        if(apex_states[i].ticket == 0) {
            apex_states[i].ticket = ticket;
            apex_states[i].tp1_closed = false;
            apex_states[i].tp2_closed = false;
            apex_states[i].initial_sl_distance = sl_dist;
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
//| Manage Apex Positions (Multi-Tier Institutional Partial Close)   |
//+------------------------------------------------------------------+
void ManageApexPositions()
{
    for(int i = 0; i < PositionsTotal(); i++) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Magic() == MagicNumber && posInfo.Symbol() == _Symbol) {
                ulong ticket = posInfo.Ticket();
                int idx = GetApexStateIndex(ticket);
                
                double entry = posInfo.PriceOpen();
                double current_sl = posInfo.StopLoss();
                double current_tp = posInfo.TakeProfit();
                double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                double current_price = (posInfo.PositionType() == POSITION_TYPE_BUY) ? bid : ask;
                
                double profit = (posInfo.PositionType() == POSITION_TYPE_BUY) ? (current_price - entry) : (entry - current_price);
                if(profit <= 0) continue;
                
                double initial_risk = (idx >= 0 && apex_states[idx].initial_sl_distance > 0) 
                                      ? apex_states[idx].initial_sl_distance 
                                      : MathAbs(entry - current_sl);
                if(initial_risk <= 0) continue;
                
                double current_rr = profit / initial_risk;
                
                // Tier 1: RR 1:2.0 -> Lock BE+ & Partial Close 40%
                if(current_rr >= RR_Level_1 && (idx < 0 || !apex_states[idx].tp1_closed)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 0.2), symInfo.Digits()) : NormalizeDouble(entry - (initial_risk * 0.2), symInfo.Digits());
                    if(UsePartialClose) PartialClosePosition(ticket, 40.0);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) apex_states[idx].tp1_closed = true;
                    Print("Apex Tier 1 RR 1:", RR_Level_1, " Reached! Partial Close 40% & SL Moved to BE+");
                }
                
                // Tier 2: RR 1:4.0 -> Lock 2.0 RR & Partial Close 30%
                else if(current_rr >= RR_Level_2 && (idx < 0 || !apex_states[idx].tp2_closed)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 2.0), symInfo.Digits()) : NormalizeDouble(entry - (initial_risk * 2.0), symInfo.Digits());
                    if(UsePartialClose) PartialClosePosition(ticket, 30.0);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) apex_states[idx].tp2_closed = true;
                    Print("Apex Tier 2 RR 1:", RR_Level_2, " Reached! Partial Close 30% & SL Moved to RR 2.0");
                }
            }
        }
    }
}

int GetApexStateIndex(ulong ticket)
{
    for(int i = 0; i < 20; i++) {
        if(apex_states[i].ticket == ticket) return i;
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
            Print("Apex Partial Close: ", close_volume, " Lots for Ticket: ", ticket);
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

//+------------------------------------------------------------------+
//|                   XAUUSD Multi-TF Scalping EA v2.0 (MAX PROFIT) |
//|                  Multi-Timeframe + Cascade TP System              |
//+------------------------------------------------------------------+
#property copyright "MT5 Scalping System"
#property link      "https://www.mql5.com"
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input double         RiskPercent = 2.5;               // Risk % per trade (Recommended: 2.0% - 5.0%)
input int            SL_Buffer = 250;                 // SL buffer in points (200-300 points)
input double         TargetRR = 2.5;                  // Target Risk-Reward ratio (1:2.5)
input int            MagicNumber = 100001;            // Magic Number
input bool           UseTradeHours = true;            // Enable trading hours filter
input string         TradeHours1_Start = "11:00";     // Session 1 Start (GMT+7)
input string         TradeHours1_End = "16:00";       // Session 1 End (GMT+7)
input string         TradeHours2_Start = "16:00";     // Session 2 Start (GMT+7)
input string         TradeHours2_End = "02:00";       // Session 2 End (GMT+7)
input bool           AllowNewOrders = true;           // Allow new orders during hours

//--- Global Variables
CTrade trade;
CPositionInfo posInfo;
CSymbolInfo symInfo;

struct TP_LEVEL {
    double RR;              // Risk-Reward ratio
    bool   Closed;          // Already closed this level
};

TP_LEVEL tp_levels[4] = {
    {1.5, false},           // RR 1:1.5 -> Lock Breakeven + 20%
    {2.0, false},           // RR 1:2.0
    {2.5, false},           // RR 1:2.5
    {3.0, false}            // RR 1:3.0
};

double g_initial_risk = 0;
int handle_ema10, handle_ema20, handle_ema50;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    trade.SetExpertMagicNumber(MagicNumber);
    trade.SetDeviationInPoints(10);
    
    if(!symInfo.Name(_Symbol)) {
        Print("Failed to get symbol info for: ", _Symbol);
        return INIT_FAILED;
    }
    symInfo.RefreshRates();
    
    handle_ema10 = iMA(_Symbol, PERIOD_M15, 10, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema20 = iMA(_Symbol, PERIOD_M15, 20, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema50 = iMA(_Symbol, PERIOD_M15, 50, 0, MODE_EMA, PRICE_CLOSE);
    
    if(handle_ema10 == INVALID_HANDLE || handle_ema20 == INVALID_HANDLE || handle_ema50 == INVALID_HANDLE) {
        Print("Failed to create indicator handles");
        return INIT_FAILED;
    }
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    IndicatorRelease(handle_ema10);
    IndicatorRelease(handle_ema20);
    IndicatorRelease(handle_ema50);
    Print("EA Stopped - Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Reset TP Levels helper                                           |
//+------------------------------------------------------------------+
void ResetTPLevels()
{
    for(int i = 0; i < 4; i++) {
        tp_levels[i].Closed = false;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    symInfo.RefreshRates();
    
    int open_count = CountOpenPositions();
    if(open_count == 0) {
        g_initial_risk = 0;
        ResetTPLevels();
    }
    
    bool in_trade_hours = IsInTradingHours();
    
    UpdateOpenPositions();
    
    if(in_trade_hours && AllowNewOrders) {
        CheckForSignal();
    }
}

//+------------------------------------------------------------------+
//| Check session helper                                             |
//+------------------------------------------------------------------+
bool IsTimeInSession(int current, int start, int end)
{
    if(start <= end)
        return (current >= start && current < end);
    else
        return (current >= start || current < end);
}

//+------------------------------------------------------------------+
//| Check Trading Hours                                              |
//+------------------------------------------------------------------+
bool IsInTradingHours()
{
    if(!UseTradeHours) return true;
    
    MqlDateTime now;
    TimeToStruct(TimeCurrent() + 25200, now);  // GMT+7 (25200 = 7*3600)
    
    int current_time = now.hour * 60 + now.min;
    
    int start1 = StringToTime1(TradeHours1_Start) / 60;
    int end1   = StringToTime1(TradeHours1_End) / 60;
    int start2 = StringToTime1(TradeHours2_Start) / 60;
    int end2   = StringToTime1(TradeHours2_End) / 60;
    
    if(IsTimeInSession(current_time, start1, end1)) return true;
    if(IsTimeInSession(current_time, start2, end2)) return true;
    
    return false;
}

//+------------------------------------------------------------------+
//| Parse time string "HH:MM" into seconds                           |
//+------------------------------------------------------------------+
int StringToTime1(string time_str)
{
    string parts[];
    int count = StringSplit(time_str, ':', parts);
    if(count != 2) return 0;
    
    int hour = (int)StringToInteger(parts[0]);
    int min  = (int)StringToInteger(parts[1]);
    return (hour * 3600 + min * 60);
}

//+------------------------------------------------------------------+
//| Check for Entry Signal                                           |
//+------------------------------------------------------------------+
void CheckForSignal()
{
    if(CountOpenPositions() > 0) return;
    
    int trend = GetTrendDirection();
    if(trend == 0) return;
    
    bool signal = false;
    int signal_type = 0;
    
    signal = GetM15ConfirmationSignal(signal_type);
    if(!signal) return;
    
    if((trend == 1 && signal_type != 1) || (trend == -1 && signal_type != -1)) return;
    
    ExecuteTrade(signal_type);
}

//+------------------------------------------------------------------+
//| Get Trend Direction with Max Profit EMA 10/20/50 Filter           |
//+------------------------------------------------------------------+
int GetTrendDirection()
{
    double ema10[], ema20[], ema50[];
    ArraySetAsSeries(ema10, true);
    ArraySetAsSeries(ema20, true);
    ArraySetAsSeries(ema50, true);
    
    if(CopyBuffer(handle_ema10, 0, 0, 2, ema10) <= 0 ||
       CopyBuffer(handle_ema20, 0, 0, 2, ema20) <= 0 ||
       CopyBuffer(handle_ema50, 0, 0, 2, ema50) <= 0)
        return 0;
        
    double close_1 = iClose(_Symbol, PERIOD_M15, 1);
    
    // Bullish Trend: Close > EMA50 && EMA10 > EMA20
    if(close_1 > ema50[1] && ema10[1] > ema20[1]) return 1;
    
    // Bearish Trend: Close < EMA50 && EMA10 < EMA20
    if(close_1 < ema50[1] && ema10[1] < ema20[1]) return -1;
    
    return 0;
}

//+------------------------------------------------------------------+
//| Get M15 Confirmation Signal                                      |
//+------------------------------------------------------------------+
bool GetM15ConfirmationSignal(int &signal_type)
{
    double open_1  = iOpen(_Symbol, PERIOD_M15, 1);
    double close_1 = iClose(_Symbol, PERIOD_M15, 1);
    
    if(close_1 > open_1) {
        signal_type = 1;  // Buy
        return true;
    }
    
    if(close_1 < open_1) {
        signal_type = -1; // Sell
        return true;
    }
    
    return false;
}

//+------------------------------------------------------------------+
//| Execute Trade                                                    |
//+------------------------------------------------------------------+
void ExecuteTrade(int trade_type)
{
    double entry_price, sl_price, tp_price;
    
    double prev_low  = iLow(_Symbol, PERIOD_M15, 1);
    double prev_high = iHigh(_Symbol, PERIOD_M15, 1);
    
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    
    if(trade_type == 1) {  // BUY
        entry_price = ask;
        sl_price = prev_low - (SL_Buffer * symInfo.Point());
        
        double risk = entry_price - sl_price;
        tp_price = entry_price + (risk * TargetRR);
        
    } else {  // SELL
        entry_price = bid;
        sl_price = prev_high + (SL_Buffer * symInfo.Point());
        
        double risk = sl_price - entry_price;
        tp_price = entry_price - (risk * TargetRR);
    }
    
    g_initial_risk = MathAbs(entry_price - sl_price);
    
    double account_balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double risk_amount = account_balance * (RiskPercent / 100.0);
    double lot_size = CalculateLotSize(risk_amount, g_initial_risk);
    
    if(lot_size < symInfo.LotsMin()) {
        Print("Lot size too small: ", lot_size, " Min Lot: ", symInfo.LotsMin());
        return;
    }
    
    ResetTPLevels();
    
    if(trade_type == 1) {
        if(trade.Buy(lot_size, _Symbol, entry_price, sl_price, tp_price, "XAUUSD Scalp Buy")) {
            Print("BUY Trade Opened - Entry: ", entry_price, " SL: ", sl_price, " TP: ", tp_price, " Lot: ", lot_size);
        } else {
            Print("Error opening BUY trade: ", trade.ResultRetcodeDescription());
        }
    } else {
        if(trade.Sell(lot_size, _Symbol, entry_price, sl_price, tp_price, "XAUUSD Scalp Sell")) {
            Print("SELL Trade Opened - Entry: ", entry_price, " SL: ", sl_price, " TP: ", tp_price, " Lot: ", lot_size);
        } else {
            Print("Error opening SELL trade: ", trade.ResultRetcodeDescription());
        }
    }
}

//+------------------------------------------------------------------+
//| Calculate Lot Size                                               |
//+------------------------------------------------------------------+
double CalculateLotSize(double risk_amount, double sl_distance)
{
    if(sl_distance <= 0) return symInfo.LotsMin();
    
    double point_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double point_size  = symInfo.Point();
    if(point_value <= 0 || point_size <= 0) return symInfo.LotsMin();
    
    double lot_size = risk_amount / ((sl_distance / point_size) * point_value);
    
    double lot_step = symInfo.LotsStep();
    if(lot_step > 0) {
        lot_size = MathFloor(lot_size / lot_step) * lot_step;
    }
    lot_size = NormalizeDouble(lot_size, 2);
    
    if(lot_size < symInfo.LotsMin()) lot_size = symInfo.LotsMin();
    if(lot_size > symInfo.LotsMax()) lot_size = symInfo.LotsMax();
    
    return lot_size;
}

//+------------------------------------------------------------------+
//| Update Open Positions                                            |
//+------------------------------------------------------------------+
void UpdateOpenPositions()
{
    for(int i = 0; i < PositionsTotal(); i++) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Magic() == MagicNumber && posInfo.Symbol() == _Symbol) {
                UpdatePositionTP_SL(posInfo.Ticket());
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Update Position TP and SL                                        |
//+------------------------------------------------------------------+
void UpdatePositionTP_SL(ulong ticket)
{
    if(!posInfo.SelectByTicket(ticket)) return;
    
    double entry_price = posInfo.PriceOpen();
    double current_sl  = posInfo.StopLoss();
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double current_price = (posInfo.PositionType() == POSITION_TYPE_BUY) ? bid : ask;
    
    double profit = 0;
    if(posInfo.PositionType() == POSITION_TYPE_BUY) {
        profit = current_price - entry_price;
    } else {
        profit = entry_price - current_price;
    }
    
    if(profit <= 0) return;
    
    double risk = (g_initial_risk > 0) ? g_initial_risk : MathAbs(entry_price - current_sl);
    if(risk <= 0) return;
    
    for(int i = 0; i < 4; i++) {
        double current_rr = profit / risk;
        
        if(current_rr >= tp_levels[i].RR && !tp_levels[i].Closed) {
            double new_sl = 0;
            if(posInfo.PositionType() == POSITION_TYPE_BUY) {
                new_sl = NormalizeDouble(entry_price + (profit * 0.5), symInfo.Digits());
                if(current_sl == 0 || new_sl > current_sl) {
                    if(trade.PositionModify(ticket, new_sl, posInfo.TakeProfit())) {
                        tp_levels[i].Closed = true;
                        Print("TP Level ", i+1, " (RR 1:", tp_levels[i].RR, ") - SL moved to ", new_sl);
                    }
                }
            } else {
                new_sl = NormalizeDouble(entry_price - (profit * 0.5), symInfo.Digits());
                if(current_sl == 0 || new_sl < current_sl) {
                    if(trade.PositionModify(ticket, new_sl, posInfo.TakeProfit())) {
                        tp_levels[i].Closed = true;
                        Print("TP Level ", i+1, " (RR 1:", tp_levels[i].RR, ") - SL moved to ", new_sl);
                    }
                }
            }
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

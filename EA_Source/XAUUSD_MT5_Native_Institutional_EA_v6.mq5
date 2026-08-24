//+------------------------------------------------------------------+
//|       XAUUSD MT5 Native Institutional EA v6.0 (Built for MT5)    |
//|      H1 Multi-TF Trend Filter + M5 ATR Breakout + 2:1 R:R System  |
//+------------------------------------------------------------------+
#property copyright "Antigravity EA Systems"
#property link      "https://www.mql5.com"
#property version   "6.00"
#property description "Native MT5 Strategy Tester Optimized EA for XAUUSD / XAUUSDc"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input group "=== Institutional Risk Management ==="
input double         RiskPercent       = 1.5;         // Risk % per trade (1.5% safe)
input int            MinSL_Points      = 250;         // Minimum SL Points ($2.50)
input int            MaxSL_Points      = 450;         // Maximum SL Points ($4.50)
input double         ATR_SL_Multiplier = 1.5;         // ATR Multiplier for Stop Loss
input int            MagicNumber       = 600001;      // Magic Number

input group "=== Take Profit & Partial Close ==="
input bool           UsePartialClose   = true;        // Enable Partial Close
input double         PartialClosePct   = 50.0;        // Partial Close % at TP1 (50%)
input double         RR_TP1            = 1.5;         // TP1 Risk:Reward (1:1.5)
input double         RR_TP2            = 3.0;         // TP2 Risk:Reward (1:3.0)

input group "=== Filter Settings ==="
input bool           UseH1TrendFilter  = true;        // Enable H1 Higher Timeframe Trend Filter
input int            H1_EMA_Fast       = 50;          // H1 Fast EMA
input int            H1_EMA_Slow       = 100;         // H1 Slow EMA
input int            M5_BreakoutBars   = 15;          // M5 Donchian Breakout Period
input int            RSI_Period        = 14;          // RSI Period

//--- Global Handles & Objects
CTrade trade;
CPositionInfo posInfo;
CSymbolInfo symInfo;

int handle_h1_ema_fast, handle_h1_ema_slow;
int handle_m5_rsi, handle_m5_atr;

struct POS_STATE {
    ulong  ticket;
    bool   tp1_closed;
    double initial_sl_dist;
};

POS_STATE pos_states[30];

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
    
    // Initialize Handles
    handle_h1_ema_fast = iMA(_Symbol, PERIOD_H1, H1_EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
    handle_h1_ema_slow = iMA(_Symbol, PERIOD_H1, H1_EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
    handle_m5_rsi      = iRSI(_Symbol, PERIOD_M5, RSI_Period, PRICE_CLOSE);
    handle_m5_atr      = iATR(_Symbol, PERIOD_M5, 14);
    
    if(handle_h1_ema_fast == INVALID_HANDLE || handle_h1_ema_slow == INVALID_HANDLE ||
       handle_m5_rsi == INVALID_HANDLE || handle_m5_atr == INVALID_HANDLE) {
        Print("Error creating indicator handles");
        return INIT_FAILED;
    }
    
    ResetStates();
    Print("EA v6.0 MT5 Native Institutional Initialized Successfully for ", _Symbol);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    IndicatorRelease(handle_h1_ema_fast);
    IndicatorRelease(handle_h1_ema_slow);
    IndicatorRelease(handle_m5_rsi);
    IndicatorRelease(handle_m5_atr);
    Print("EA v6.0 Deinitialized. Reason: ", reason);
}

void ResetStates()
{
    for(int i = 0; i < 30; i++) {
        pos_states[i].ticket = 0;
        pos_states[i].tp1_closed = false;
        pos_states[i].initial_sl_dist = 0;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    symInfo.RefreshRates();
    
    // Manage active positions
    ManagePositions();
    
    // Check new entry signal
    CheckEntrySignal();
}

//+------------------------------------------------------------------+
//| Check H1 Trend + M5 Breakout Entry Signal                         |
//+------------------------------------------------------------------+
void CheckEntrySignal()
{
    if(CountOpenPositions() > 0) return;
    
    // 1. Check H1 Trend Filter
    int h1_trend = GetH1Trend();
    if(UseH1TrendFilter && h1_trend == 0) return;
    
    // 2. Read M5 Indicators
    double rsi[], atr[];
    if(CopyBuffer(handle_m5_rsi, 0, 1, 1, rsi) <= 0 ||
       CopyBuffer(handle_m5_atr, 0, 1, 1, atr) <= 0) return;
       
    double close_1 = iClose(_Symbol, PERIOD_M5, 1);
    double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
    
    // Calculate Donchian Channel High/Low
    double highest_h = GetHighestHigh(M5_BreakoutBars, 2);
    double lowest_l  = GetLowestLow(M5_BreakoutBars, 2);
    
    bool buy_signal  = (h1_trend >= 0) && (close_1 > highest_h) && (close_1 > open_1) && (rsi[0] > 52.0 && rsi[0] < 72.0);
    bool sell_signal = (h1_trend <= 0) && (close_1 < lowest_l)  && (close_1 < open_1) && (rsi[0] < 48.0 && rsi[0] > 28.0);
    
    if(buy_signal) {
        ExecuteOrder(1, atr[0]);
    } else if(sell_signal) {
        ExecuteOrder(-1, atr[0]);
    }
}

int GetH1Trend()
{
    double h1_fast[], h1_slow[], h1_close[];
    if(CopyBuffer(handle_h1_ema_fast, 0, 1, 1, h1_fast) <= 0 ||
       CopyBuffer(handle_h1_ema_slow, 0, 1, 1, h1_slow) <= 0) return 0;
       
    double close_h1 = iClose(_Symbol, PERIOD_H1, 1);
    
    if(close_h1 > h1_slow[0] && h1_fast[0] > h1_slow[0]) return 1;   // Bullish Trend
    if(close_h1 < h1_slow[0] && h1_fast[0] < h1_slow[0]) return -1;  // Bearish Trend
    return 0;
}

double GetHighestHigh(int count, int start_bar)
{
    double highest = 0;
    for(int i = start_bar; i < start_bar + count; i++) {
        double h = iHigh(_Symbol, PERIOD_M5, i);
        if(h > highest) highest = h;
    }
    return highest;
}

double GetLowestLow(int count, int start_bar)
{
    double lowest = 999999;
    for(int i = start_bar; i < start_bar + count; i++) {
        double l = iLow(_Symbol, PERIOD_M5, i);
        if(l < lowest) lowest = l;
    }
    return lowest;
}

//+------------------------------------------------------------------+
//| Execute Trade Order                                              |
//+------------------------------------------------------------------+
void ExecuteOrder(int type, double atr_val)
{
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double entry = (type == 1) ? ask : bid;
    
    // Calculate ATR-based Stop Loss
    double sl_dist_points = (atr_val * ATR_SL_Multiplier) / symInfo.Point();
    if(sl_dist_points < MinSL_Points) sl_dist_points = MinSL_Points;
    if(sl_dist_points > MaxSL_Points) sl_dist_points = MaxSL_Points;
    
    double sl_price = (type == 1) ? (entry - sl_dist_points * symInfo.Point()) : (entry + sl_dist_points * symInfo.Point());
    double tp_price = (type == 1) ? (entry + sl_dist_points * RR_TP2 * symInfo.Point()) : (entry - sl_dist_points * RR_TP2 * symInfo.Point());
    
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double risk_amt = balance * (RiskPercent / 100.0);
    double lot_size = CalculateLotSize(risk_amt, sl_dist_points * symInfo.Point());
    
    if(type == 1) {
        if(trade.Buy(lot_size, _Symbol, entry, sl_price, tp_price, "XAUUSD v6 Native Institutional")) {
            ulong ticket = trade.ResultOrder();
            RegisterState(ticket, sl_dist_points * symInfo.Point());
        }
    } else {
        if(trade.Sell(lot_size, _Symbol, entry, sl_price, tp_price, "XAUUSD v6 Native Institutional")) {
            ulong ticket = trade.ResultOrder();
            RegisterState(ticket, sl_dist_points * symInfo.Point());
        }
    }
}

void RegisterState(ulong ticket, double sl_dist)
{
    for(int i = 0; i < 30; i++) {
        if(pos_states[i].ticket == 0) {
            pos_states[i].ticket = ticket;
            pos_states[i].tp1_closed = false;
            pos_states[i].initial_sl_dist = sl_dist;
            break;
        }
    }
}

double CalculateLotSize(double risk_amt, double sl_dist)
{
    if(sl_dist <= 0) return symInfo.LotsMin();
    
    double tick_val = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double point_sz = symInfo.Point();
    if(tick_val <= 0 || point_sz <= 0) return symInfo.LotsMin();
    
    double lot = risk_amt / ((sl_dist / point_sz) * tick_val);
    double step = symInfo.LotsStep();
    if(step > 0) lot = MathFloor(lot / step) * step;
    
    double min_lot = symInfo.LotsMin();
    double max_lot = symInfo.LotsMax();
    
    if(lot < min_lot) lot = min_lot;
    if(lot > max_lot) lot = max_lot;
    
    return NormalizeDouble(lot, (min_lot < 0.01) ? 4 : 2);
}

void ManagePositions()
{
    for(int i = 0; i < PositionsTotal(); i++) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Symbol() == _Symbol && posInfo.Magic() == MagicNumber) {
                ulong ticket = posInfo.Ticket();
                int idx = GetStateIndex(ticket);
                
                double entry = posInfo.PriceOpen();
                double current_sl = posInfo.StopLoss();
                double current_tp = posInfo.TakeProfit();
                double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                double current_price = (posInfo.PositionType() == POSITION_TYPE_BUY) ? bid : ask;
                
                double profit = (posInfo.PositionType() == POSITION_TYPE_BUY) ? (current_price - entry) : (entry - current_price);
                if(profit <= 0) continue;
                
                double initial_risk = (idx >= 0 && pos_states[idx].initial_sl_dist > 0) ? pos_states[idx].initial_sl_dist : MathAbs(entry - current_sl);
                if(initial_risk <= 0) continue;
                
                double current_rr = profit / initial_risk;
                
                // TP1 Partial Close at 1.5 R:R
                if(current_rr >= RR_TP1 && (idx < 0 || !pos_states[idx].tp1_closed)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 0.3), symInfo.Digits()) : NormalizeDouble(entry - (initial_risk * 0.3), symInfo.Digits());
                    if(UsePartialClose) PartialClose(ticket, PartialClosePct);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) pos_states[idx].tp1_closed = true;
                }
            }
        }
    }
}

int GetStateIndex(ulong ticket)
{
    for(int i = 0; i < 30; i++) {
        if(pos_states[i].ticket == ticket) return i;
    }
    return -1;
}

void PartialClose(ulong ticket, double pct)
{
    if(posInfo.SelectByTicket(ticket)) {
        double current_vol = posInfo.Volume();
        double min_lot = symInfo.LotsMin();
        double close_vol = NormalizeDouble(current_vol * (pct / 100.0), (min_lot < 0.01) ? 4 : 2);
        if(close_vol >= min_lot && close_vol < current_vol) {
            trade.PositionClosePartial(ticket, close_vol);
        }
    }
}

int CountOpenPositions()
{
    int count = 0;
    for(int i = 0; i < PositionsTotal(); i++) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Symbol() == _Symbol && posInfo.Magic() == MagicNumber) {
                count++;
            }
        }
    }
    return count;
}

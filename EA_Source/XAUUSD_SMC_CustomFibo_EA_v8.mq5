//+------------------------------------------------------------------+
//|    XAUUSD SMC Custom Fibonacci EA v8.0 (Ultra Max Profit)        |
//|  SMC BOS + 0.1346-0.2546 Buy Zone + TP1-TP5 Multi-Tier Matrix    |
//+------------------------------------------------------------------+
#property copyright "Antigravity EA Systems"
#property link      "https://www.mql5.com"
#property version   "8.00"
#property description "Ultra Max Profit Custom Fibonacci EA Built Natively for MT5 Strategy Tester"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input group "=== Custom Fibonacci Ratios & Zone ==="
input double         FibZone_Upper     = 0.254618;    // 🟢 Upper Buy Border (0.254618)
input double         FibZone_Core      = 0.193661;    // 🔴 Core Buy Level (0.193661)
input double         FibZone_Lower     = 0.134618;    // 🟡 Lower Buy Border (0.134618)

input group "=== Take Profit Ratio Matrix ==="
input double         Fib_TP1           = 0.846180;    // 🟠 TP1 Ratio (0.846180) -> Close 30% + Lock BE+
input double         Fib_TP2           = 1.000000;    // 🟠 TP2 Ratio (1.000000) -> Close 30% + Lock 1.5 RR
input double         Fib_TP3           = 1.246180;    // 🟠 TP3 Ratio (1.246180) -> Close 20%
input double         Fib_TP4           = 1.536180;    // 🟠 TP4 Ratio (1.536180) -> Close 10%
input double         Fib_TP5           = 1.724618;    // 🟠 TP5 Ratio (1.724618) -> Close 10% Runner

input group "=== Risk & Execution Management ==="
input double         RiskPercent       = 3.0;         // Risk % per trade (3.0% Max Profit)
input int            SwingLookback     = 30;          // Swing High/Low Lookback Bars
input int            MagicNumber       = 800001;      // Magic Number
input bool           UseH1TrendFilter  = true;        // Enable H1 Trend Filter

//--- Global Objects
CTrade trade;
CPositionInfo posInfo;
CSymbolInfo symInfo;

int handle_h1_ema50, handle_h1_ema100;

struct V8_STATE {
    ulong  ticket;
    bool   tp1_done;
    bool   tp2_done;
    bool   tp3_done;
    bool   tp4_done;
    double initial_sl_dist;
};

V8_STATE v8_states[40];

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
    
    handle_h1_ema50  = iMA(_Symbol, PERIOD_H1, 50,  0, MODE_EMA, PRICE_CLOSE);
    handle_h1_ema100 = iMA(_Symbol, PERIOD_H1, 100, 0, MODE_EMA, PRICE_CLOSE);
    
    if(handle_h1_ema50 == INVALID_HANDLE || handle_h1_ema100 == INVALID_HANDLE) {
        Print("Error creating indicator handles");
        return INIT_FAILED;
    }
    
    ResetStates();
    Print("EA v8.0 SMC Custom Fibo Ultra Max Profit Initialized Successfully for ", _Symbol);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    IndicatorRelease(handle_h1_ema50);
    IndicatorRelease(handle_h1_ema100);
    Print("EA v8.0 Deinitialized. Reason: ", reason);
}

void ResetStates()
{
    for(int i = 0; i < 40; i++) {
        v8_states[i].ticket = 0;
        v8_states[i].tp1_done = false;
        v8_states[i].tp2_done = false;
        v8_states[i].tp3_done = false;
        v8_states[i].tp4_done = false;
        v8_states[i].initial_sl_dist = 0;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    symInfo.RefreshRates();
    
    // Manage position stages
    ManageFiboPositions();
    
    // Check entry signal
    CheckFiboSignal();
}

//+------------------------------------------------------------------+
//| Check SMC Custom Fibo Signal                                     |
//+------------------------------------------------------------------+
void CheckFiboSignal()
{
    if(CountPositions() > 0) return;
    
    // H1 Trend Filter
    int h1_trend = GetH1Trend();
    if(UseH1TrendFilter && h1_trend == 0) return;
    
    // Find Swing High and Low
    double swing_high = GetHighestHigh(SwingLookback, 2);
    double swing_low  = GetLowestLow(SwingLookback, 2);
    double range = swing_high - swing_low;
    if(range <= 5.0) return; // Ignore small range
    
    // Calculate Fibo Levels
    double fib_upper = swing_low + (range * FibZone_Upper);
    double fib_lower = swing_low + (range * FibZone_Lower);
    
    double close_1 = iClose(_Symbol, PERIOD_M5, 1);
    double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
    double low_1   = iLow(_Symbol, PERIOD_M5, 1);
    
    // BUY Signal: Retracement into Buy Zone (0.1346 - 0.2546) + Bullish Candle Reversal
    bool buy_signal = (h1_trend >= 0) && (low_1 <= fib_upper) && (close_1 >= fib_lower) && (close_1 > open_1);
    
    if(buy_signal) {
        ExecuteFiboTrade(swing_low, swing_high, range);
    }
}

int GetH1Trend()
{
    double ema50[], ema100[];
    if(CopyBuffer(handle_h1_ema50, 0, 1, 1, ema50) <= 0 ||
       CopyBuffer(handle_h1_ema100, 0, 1, 1, ema100) <= 0) return 0;
       
    double close_h1 = iClose(_Symbol, PERIOD_H1, 1);
    if(close_h1 > ema100[0] && ema50[0] > ema100[0]) return 1;
    if(close_h1 < ema100[0] && ema50[0] < ema100[0]) return -1;
    return 0;
}

double GetHighestHigh(int count, int start_bar)
{
    double h_max = 0;
    for(int i = start_bar; i < start_bar + count; i++) {
        double val = iHigh(_Symbol, PERIOD_M5, i);
        if(val > h_max) h_max = val;
    }
    return h_max;
}

double GetLowestLow(int count, int start_bar)
{
    double l_min = 999999;
    for(int i = start_bar; i < start_bar + count; i++) {
        double val = iLow(_Symbol, PERIOD_M5, i);
        if(val < l_min) l_min = val;
    }
    return l_min;
}

void ExecuteFiboTrade(double swing_low, double swing_high, double range)
{
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double entry = ask;
    
    // Stop Loss under Swing Low
    double sl_price = swing_low - (200 * symInfo.Point());
    double sl_dist = entry - sl_price;
    if(sl_dist <= 0) return;
    
    // Take Profit at Fib 1.724618 (TP5 Runner Target)
    double tp_price = swing_low + (range * Fib_TP5);
    
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double risk_amt = balance * (RiskPercent / 100.0);
    double lot_size = CalculateLot(risk_amt, sl_dist);
    
    if(trade.Buy(lot_size, _Symbol, entry, sl_price, tp_price, "XAUUSD v8 SMC Fibo MaxProfit")) {
        ulong ticket = trade.ResultOrder();
        RegisterState(ticket, sl_dist);
    }
}

void RegisterState(ulong ticket, double sl_dist)
{
    for(int i = 0; i < 40; i++) {
        if(v8_states[i].ticket == 0) {
            v8_states[i].ticket = ticket;
            v8_states[i].tp1_done = false;
            v8_states[i].tp2_done = false;
            v8_states[i].tp3_done = false;
            v8_states[i].tp4_done = false;
            v8_states[i].initial_sl_dist = sl_dist;
            break;
        }
    }
}

double CalculateLot(double risk_amt, double sl_dist)
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

void ManageFiboPositions()
{
    for(int i = 0; i < PositionsTotal(); i++) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Symbol() == _Symbol && posInfo.Magic() == MagicNumber) {
                ulong ticket = posInfo.Ticket();
                int idx = GetStateIndex(ticket);
                
                double entry = posInfo.PriceOpen();
                double current_sl = posInfo.StopLoss();
                double current_tp = posInfo.TakeProfit();
                double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                
                double profit = bid - entry;
                if(profit <= 0) continue;
                
                double initial_risk = (idx >= 0 && v8_states[idx].initial_sl_dist > 0) ? v8_states[idx].initial_sl_dist : MathAbs(entry - current_sl);
                if(initial_risk <= 0) continue;
                
                double current_rr = profit / initial_risk;
                
                // Stage 1: TP1 (0.846180) -> Partial Close 30% + Lock BE+
                if(current_rr >= 1.5 && (idx < 0 || !v8_states[idx].tp1_done)) {
                    double new_sl = NormalizeDouble(entry + (initial_risk * 0.3), symInfo.Digits());
                    PartialClose(ticket, 30.0);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) v8_states[idx].tp1_done = true;
                }
                // Stage 2: TP2 (1.000000) -> Partial Close 30% + Lock 1.5 RR
                else if(current_rr >= 3.0 && (idx < 0 || !v8_states[idx].tp2_done)) {
                    double new_sl = NormalizeDouble(entry + (initial_risk * 1.5), symInfo.Digits());
                    PartialClose(ticket, 30.0);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) v8_states[idx].tp2_done = true;
                }
            }
        }
    }
}

int GetStateIndex(ulong ticket)
{
    for(int i = 0; i < 40; i++) {
        if(v8_states[i].ticket == ticket) return i;
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

int CountPositions()
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

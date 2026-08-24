//+------------------------------------------------------------------+
//|    XAUUSD Apex Champion EA v11.0 (Peak Profit Lock Champion)    |
//| Trailing High-Water Mark Guard + Compounding Tier Risk Scaling  |
//+------------------------------------------------------------------+
#property copyright "Antigravity EA Systems"
#property link      "https://www.mql5.com"
#property version   "11.00"
#property description "Peak Profit Lock Edition ($70k+ Peak Locking Protection)"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input group "=== Peak Profit Lock & Risk Sizing ==="
input double         InitialRiskPercent = 3.0;         // Initial Risk % ($10k-$30k phase)
input double         MaxAllowedPullback = 15.0;        // Max Allowed Pullback % from Peak (15%)
input double         MaxLotLimit        = 8.0;         // Max Lot Cap (Prevents Lot Explosion)
input int            MagicNumber        = 1100001;     // Magic Number

input group "=== Multi-Tier Profit Targets ==="
input bool           UsePartialClose    = true;        // Enable Partial Closure
input double         TP1_Close_Pct      = 30.0;        // TP1 Close % (30%)
input double         TP2_Close_Pct      = 40.0;        // TP2 Close % (40%)
input double         RR_Level_1         = 1.8;         // TP1 RR (1:1.8) -> Lock BE+
input double         RR_Level_2         = 3.5;         // TP2 RR (1:3.5) -> Lock 1.5 RR
input double         RR_Level_3         = 8.0;         // TP3 RR (1:8.0) -> Ultimate Runner

input group "=== Multi-Timeframe Filters ==="
input bool           UseH1TrendFilter   = true;        // Enable H1 Trend Filter
input int            H1_EMA_Fast        = 20;          // H1 Fast EMA
input int            H1_EMA_Mid         = 50;          // H1 Mid EMA
input int            H1_EMA_Slow        = 100;         // H1 Slow EMA
input int            M5_BreakoutPeriod  = 15;          // M5 Donchian Breakout Period
input int            RSI_Period         = 14;          // RSI Period

//--- Global Objects & Handles
CTrade trade;
CPositionInfo posInfo;
CSymbolInfo symInfo;

int handle_h1_fast, handle_h1_mid, handle_h1_slow;
int handle_m5_rsi, handle_m5_atr;

double high_water_mark = 10000.0;

struct V11_STATE {
    ulong  ticket;
    bool   tp1_done;
    bool   tp2_done;
    double initial_sl_dist;
};

V11_STATE v11_states[40];

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
    
    handle_h1_fast = iMA(_Symbol, PERIOD_H1, H1_EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
    handle_h1_mid  = iMA(_Symbol, PERIOD_H1, H1_EMA_Mid,  0, MODE_EMA, PRICE_CLOSE);
    handle_h1_slow = iMA(_Symbol, PERIOD_H1, H1_EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
    handle_m5_rsi  = iRSI(_Symbol, PERIOD_M5, RSI_Period, PRICE_CLOSE);
    handle_m5_atr  = iATR(_Symbol, PERIOD_M5, 14);
    
    if(handle_h1_fast == INVALID_HANDLE || handle_h1_mid == INVALID_HANDLE || handle_h1_slow == INVALID_HANDLE ||
       handle_m5_rsi == INVALID_HANDLE || handle_m5_atr == INVALID_HANDLE) {
        Print("Error creating indicator handles");
        return INIT_FAILED;
    }
    
    high_water_mark = AccountInfoDouble(ACCOUNT_BALANCE);
    if(high_water_mark <= 0) high_water_mark = 10000.0;
    
    ResetStates();
    Print("EA v11.0 Peak Profit Lock Initialized Successfully for ", _Symbol);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    IndicatorRelease(handle_h1_fast);
    IndicatorRelease(handle_h1_mid);
    IndicatorRelease(handle_h1_slow);
    IndicatorRelease(handle_m5_rsi);
    IndicatorRelease(handle_m5_atr);
    Print("EA v11.0 Deinitialized. Reason: ", reason);
}

void ResetStates()
{
    for(int i = 0; i < 40; i++) {
        v11_states[i].ticket = 0;
        v11_states[i].tp1_done = false;
        v11_states[i].tp2_done = false;
        v11_states[i].initial_sl_dist = 0;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    symInfo.RefreshRates();
    
    // Update High-Water Mark Peak
    double current_balance = AccountInfoDouble(ACCOUNT_BALANCE);
    if(current_balance > high_water_mark) {
        high_water_mark = current_balance;
    }
    
    // Manage position stages
    ManagePositions();
    
    // Check entry signal
    CheckSignal();
}

//+------------------------------------------------------------------+
//| Check Entry Signal                                               |
//+------------------------------------------------------------------+
void CheckSignal()
{
    if(CountPositions() > 0) return;
    
    int h1_trend = GetH1Trend();
    if(UseH1TrendFilter && h1_trend == 0) return;
    
    double rsi[], atr[];
    if(CopyBuffer(handle_m5_rsi, 0, 1, 1, rsi) <= 0 ||
       CopyBuffer(handle_m5_atr, 0, 1, 1, atr) <= 0) return;
       
    double close_1 = iClose(_Symbol, PERIOD_M5, 1);
    double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
    
    double highest_h = GetHighestHigh(M5_BreakoutPeriod, 2);
    double lowest_l  = GetLowestLow(M5_BreakoutPeriod, 2);
    
    bool buy_signal  = (h1_trend >= 0) && (close_1 > highest_h) && (close_1 > open_1) && (rsi[0] > 54.0 && rsi[0] < 74.0);
    bool sell_signal = (h1_trend <= 0) && (close_1 < lowest_l)  && (close_1 < open_1) && (rsi[0] < 46.0 && rsi[0] > 26.0);
    
    if(buy_signal) {
        ExecuteOrder(1, atr[0]);
    } else if(sell_signal) {
        ExecuteOrder(-1, atr[0]);
    }
}

int GetH1Trend()
{
    double f[], m[], s[];
    if(CopyBuffer(handle_h1_fast, 0, 1, 1, f) <= 0 ||
       CopyBuffer(handle_h1_mid,  0, 1, 1, m) <= 0 ||
       CopyBuffer(handle_h1_slow, 0, 1, 1, s) <= 0) return 0;
       
    double close_h1 = iClose(_Symbol, PERIOD_H1, 1);
    
    if(close_h1 > s[0] && f[0] > m[0] && m[0] > s[0]) return 1;
    if(close_h1 < s[0] && f[0] < m[0] && m[0] < s[0]) return -1;
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

void ExecuteOrder(int type, double atr_val)
{
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double entry = (type == 1) ? ask : bid;
    
    double sl_dist_pts = (atr_val * 1.5) / symInfo.Point();
    if(sl_dist_pts < 250) sl_dist_pts = 250;
    if(sl_dist_pts > 450) sl_dist_pts = 450;
    
    double sl_price = (type == 1) ? (entry - sl_dist_pts * symInfo.Point()) : (entry + sl_dist_pts * symInfo.Point());
    double tp_price = (type == 1) ? (entry + sl_dist_pts * RR_Level_3 * symInfo.Point()) : (entry - sl_dist_pts * RR_Level_3 * symInfo.Point());
    
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    
    // Compounding Tier Risk Scaling + High-Water Mark Protection Guard
    double dynamic_risk = InitialRiskPercent;
    
    if(balance >= 50000.0) {
        dynamic_risk = 1.2; // Capital Protection Phase
    } else if(balance >= 30000.0) {
        dynamic_risk = 2.0; // Balanced Phase
    }
    
    // Check if balance pulled back from All-Time High Peak
    double pullback_pct = 0;
    if(high_water_mark > 0) {
        pullback_pct = ((high_water_mark - balance) / high_water_mark) * 100.0;
    }
    
    if(pullback_pct >= MaxAllowedPullback) {
        dynamic_risk = 1.0; // Halve risk to 1% to lock in peak profits!
    }
    
    double risk_amt = balance * (dynamic_risk / 100.0);
    double lot_size = CalculateLot(risk_amt, sl_dist_pts * symInfo.Point());
    
    if(type == 1) {
        if(trade.Buy(lot_size, _Symbol, entry, sl_price, tp_price, "XAUUSD v11 Peak Lock")) {
            ulong ticket = trade.ResultOrder();
            RegisterState(ticket, sl_dist_pts * symInfo.Point());
        }
    } else {
        if(trade.Sell(lot_size, _Symbol, entry, sl_price, tp_price, "XAUUSD v11 Peak Lock")) {
            ulong ticket = trade.ResultOrder();
            RegisterState(ticket, sl_dist_pts * symInfo.Point());
        }
    }
}

void RegisterState(ulong ticket, double sl_dist)
{
    for(int i = 0; i < 40; i++) {
        if(v11_states[i].ticket == 0) {
            v11_states[i].ticket = ticket;
            v11_states[i].tp1_done = false;
            v11_states[i].tp2_done = false;
            v11_states[i].initial_sl_dist = sl_dist;
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
    if(lot < min_lot) lot = min_lot;
    if(lot > MaxLotLimit) lot = MaxLotLimit;
    
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
                
                double initial_risk = (idx >= 0 && v11_states[idx].initial_sl_dist > 0) ? v11_states[idx].initial_sl_dist : MathAbs(entry - current_sl);
                if(initial_risk <= 0) continue;
                
                double current_rr = profit / initial_risk;
                
                // TP1 Stage (Lock BE+)
                if(current_rr >= RR_Level_1 && (idx < 0 || !v11_states[idx].tp1_done)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 0.4), symInfo.Digits()) : NormalizeDouble(entry - (initial_risk * 0.4), symInfo.Digits());
                    if(UsePartialClose) PartialClose(ticket, TP1_Close_Pct);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) v11_states[idx].tp1_done = true;
                }
                // TP2 Stage (Lock 1.5 RR)
                else if(current_rr >= RR_Level_2 && (idx < 0 || !v11_states[idx].tp2_done)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 1.5), symInfo.Digits()) : NormalizeDouble(entry - (initial_risk * 1.5), symInfo.Digits());
                    if(UsePartialClose) PartialClose(ticket, TP2_Close_Pct);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) v11_states[idx].tp2_done = true;
                }
            }
        }
    }
}

int GetStateIndex(ulong ticket)
{
    for(int i = 0; i < 40; i++) {
        if(v11_states[i].ticket == ticket) return i;
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

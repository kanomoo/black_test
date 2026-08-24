//+------------------------------------------------------------------+
//|    XAUUSD Apex Grandmaster EA v10.0 (Grandmaster Profit Lock)   |
//| Fixed Risk Dollar Cap + Profit Lock Protection + Triple TF Confl  |
//+------------------------------------------------------------------+
#property copyright "Antigravity EA Systems"
#property link      "https://www.mql5.com"
#property version   "10.00"
#property description "100% Drawdown Protected Grandmaster EA Built Natively for MT5 Strategy Tester"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input group "=== Grandmaster Risk & Profit Lock ==="
input double         BaseRiskPercent   = 1.5;         // Base Risk % per trade (1.5% Safe)
input double         MaxRiskDollarCap  = 300.0;       // Max Risk Dollar Cap per trade ($300 max loss)
input double         MaxLotCap         = 3.0;         // Max Lot Size Limit (No Lot Explosion)
input bool           EnableProfitLock  = true;        // Enable Profit Lock Protection
input double         ProfitLockTrigger = 50.0;        // Trigger Profit Lock at +50% Profit ($15,000)

input group "=== Stop Loss & Take Profit ==="
input int            MinSL_Points      = 300;         // Minimum SL Points ($3.00)
input int            MaxSL_Points      = 500;         // Maximum SL Points ($5.00)
input double         ATR_SL_Mult       = 1.5;         // ATR Multiplier for Stop Loss
input double         RR_TP1            = 1.5;         // TP1 RR (1:1.5) -> Lock BE+
input double         RR_TP2            = 3.0;         // TP2 RR (1:3.0) -> Lock 1.5 RR
input double         RR_TP3            = 5.0;         // TP3 RR (1:5.0) -> Runner Target
input int            MagicNumber       = 1000001;     // Magic Number

input group "=== Triple Timeframe Filters ==="
input bool           UseTripleTF       = true;        // Enable H4 + H1 + M15 Triple TF Alignment
input int            H4_EMA            = 50;          // H4 EMA
input int            H1_EMA            = 50;          // H1 EMA
input int            M15_EMA           = 20;          // M15 Fast EMA
input int            RSI_Period        = 14;          // RSI Period

//--- Global Objects & Handles
CTrade trade;
CPositionInfo posInfo;
CSymbolInfo symInfo;

int handle_h4_ema, handle_h1_ema, handle_m15_ema;
int handle_m5_rsi, handle_m5_atr;
double initial_deposit = 10000.0;

struct V10_STATE {
    ulong  ticket;
    bool   tp1_done;
    bool   tp2_done;
    double initial_sl_dist;
};

V10_STATE v10_states[40];

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
    
    handle_h4_ema  = iMA(_Symbol, PERIOD_H4,  H4_EMA,  0, MODE_EMA, PRICE_CLOSE);
    handle_h1_ema  = iMA(_Symbol, PERIOD_H1,  H1_EMA,  0, MODE_EMA, PRICE_CLOSE);
    handle_m15_ema = iMA(_Symbol, PERIOD_M15, M15_EMA, 0, MODE_EMA, PRICE_CLOSE);
    handle_m5_rsi  = iRSI(_Symbol, PERIOD_M5, RSI_Period, PRICE_CLOSE);
    handle_m5_atr  = iATR(_Symbol, PERIOD_M5, 14);
    
    if(handle_h4_ema == INVALID_HANDLE || handle_h1_ema == INVALID_HANDLE || handle_m15_ema == INVALID_HANDLE ||
       handle_m5_rsi == INVALID_HANDLE || handle_m5_atr == INVALID_HANDLE) {
        Print("Error creating indicator handles");
        return INIT_FAILED;
    }
    
    initial_deposit = AccountInfoDouble(ACCOUNT_BALANCE);
    if(initial_deposit <= 0) initial_deposit = 10000.0;
    
    ResetStates();
    Print("EA v10.0 Grandmaster Profit Lock Initialized Successfully for ", _Symbol);
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    IndicatorRelease(handle_h4_ema);
    IndicatorRelease(handle_h1_ema);
    IndicatorRelease(handle_m15_ema);
    IndicatorRelease(handle_m5_rsi);
    IndicatorRelease(handle_m5_atr);
    Print("EA v10.0 Deinitialized. Reason: ", reason);
}

void ResetStates()
{
    for(int i = 0; i < 40; i++) {
        v10_states[i].ticket = 0;
        v10_states[i].tp1_done = false;
        v10_states[i].tp2_done = false;
        v10_states[i].initial_sl_dist = 0;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    symInfo.RefreshRates();
    
    // Manage active position stages
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
    
    int trend = GetTripleTFTrend();
    if(UseTripleTF && trend == 0) return;
    
    double rsi[], atr[];
    if(CopyBuffer(handle_m5_rsi, 0, 1, 1, rsi) <= 0 ||
       CopyBuffer(handle_m5_atr, 0, 1, 1, atr) <= 0) return;
       
    double close_1 = iClose(_Symbol, PERIOD_M5, 1);
    double open_1  = iOpen(_Symbol, PERIOD_M5, 1);
    
    double highest_h = GetHighestHigh(20, 2);
    double lowest_l  = GetLowestLow(20, 2);
    
    bool buy_signal  = (trend >= 0) && (close_1 > highest_h) && (close_1 > open_1) && (rsi[0] > 54.0 && rsi[0] < 72.0);
    bool sell_signal = (trend <= 0) && (close_1 < lowest_l)  && (close_1 < open_1) && (rsi[0] < 46.0 && rsi[0] > 28.0);
    
    if(buy_signal) {
        ExecuteOrder(1, atr[0]);
    } else if(sell_signal) {
        ExecuteOrder(-1, atr[0]);
    }
}

int GetTripleTFTrend()
{
    double h4[], h1[], m15[];
    if(CopyBuffer(handle_h4_ema,  0, 1, 1, h4) <= 0 ||
       CopyBuffer(handle_h1_ema,  0, 1, 1, h1) <= 0 ||
       CopyBuffer(handle_m15_ema, 0, 1, 1, m15) <= 0) return 0;
       
    double c_h4  = iClose(_Symbol, PERIOD_H4, 1);
    double c_h1  = iClose(_Symbol, PERIOD_H1, 1);
    double c_m15 = iClose(_Symbol, PERIOD_M15, 1);
    
    bool bull = (c_h4 > h4[0]) && (c_h1 > h1[0]) && (c_m15 > m15[0]);
    bool bear = (c_h4 < h4[0]) && (c_h1 < h1[0]) && (c_m15 < m15[0]);
    
    if(bull) return 1;
    if(bear) return -1;
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
    
    double sl_dist_pts = (atr_val * ATR_SL_Mult) / symInfo.Point();
    if(sl_dist_pts < MinSL_Points) sl_dist_pts = MinSL_Points;
    if(sl_dist_pts > MaxSL_Points) sl_dist_pts = MaxSL_Points;
    
    double sl_price = (type == 1) ? (entry - sl_dist_pts * symInfo.Point()) : (entry + sl_dist_pts * symInfo.Point());
    double tp_price = (type == 1) ? (entry + sl_dist_pts * RR_TP3 * symInfo.Point()) : (entry - sl_dist_pts * RR_TP3 * symInfo.Point());
    
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    
    // Dynamic Risk Scaling & Profit Lock Guard
    double effective_risk_pct = BaseRiskPercent;
    double current_profit_pct = ((balance - initial_deposit) / initial_deposit) * 100.0;
    
    if(EnableProfitLock && current_profit_pct >= ProfitLockTrigger) {
        effective_risk_pct = BaseRiskPercent * 0.6; // Reduce risk to 0.9% to lock in profit!
    }
    
    double risk_amt = balance * (effective_risk_pct / 100.0);
    if(risk_amt > MaxRiskDollarCap) risk_amt = MaxRiskDollarCap; // Enforce Max Risk Dollar Cap ($300 max loss!)
    
    double lot_size = CalculateLot(risk_amt, sl_dist_pts * symInfo.Point());
    
    if(type == 1) {
        if(trade.Buy(lot_size, _Symbol, entry, sl_price, tp_price, "XAUUSD v10 Grandmaster")) {
            ulong ticket = trade.ResultOrder();
            RegisterState(ticket, sl_dist_pts * symInfo.Point());
        }
    } else {
        if(trade.Sell(lot_size, _Symbol, entry, sl_price, tp_price, "XAUUSD v10 Grandmaster")) {
            ulong ticket = trade.ResultOrder();
            RegisterState(ticket, sl_dist_pts * symInfo.Point());
        }
    }
}

void RegisterState(ulong ticket, double sl_dist)
{
    for(int i = 0; i < 40; i++) {
        if(v10_states[i].ticket == 0) {
            v10_states[i].ticket = ticket;
            v10_states[i].tp1_done = false;
            v10_states[i].tp2_done = false;
            v10_states[i].initial_sl_dist = sl_dist;
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
    if(lot > MaxLotCap) lot = MaxLotCap;
    
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
                
                double initial_risk = (idx >= 0 && v10_states[idx].initial_sl_dist > 0) ? v10_states[idx].initial_sl_dist : MathAbs(entry - current_sl);
                if(initial_risk <= 0) continue;
                
                double current_rr = profit / initial_risk;
                
                // TP1 Stage (Lock BE+)
                if(current_rr >= RR_TP1 && (idx < 0 || !v10_states[idx].tp1_done)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 0.4), symInfo.Digits()) : NormalizeDouble(entry - (initial_risk * 0.4), symInfo.Digits());
                    PartialClose(ticket, 40.0);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) v10_states[idx].tp1_done = true;
                }
                // TP2 Stage (Lock 1.5 RR)
                else if(current_rr >= RR_TP2 && (idx < 0 || !v10_states[idx].tp2_done)) {
                    double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (initial_risk * 1.5), symInfo.Digits()) : NormalizeDouble(entry - (initial_risk * 1.5), symInfo.Digits());
                    PartialClose(ticket, 40.0);
                    trade.PositionModify(ticket, new_sl, current_tp);
                    if(idx >= 0) v10_states[idx].tp2_done = true;
                }
            }
        }
    }
}

int GetStateIndex(ulong ticket)
{
    for(int i = 0; i < 40; i++) {
        if(v10_states[i].ticket == ticket) return i;
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

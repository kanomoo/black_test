//+------------------------------------------------------------------+
//|         XAUUSD SMC + Custom Fibonacci Retracement EA v5.0         |
//|    Smart Money Concepts (SMC) & Custom Fib Entry/TP Matrix       |
//+------------------------------------------------------------------+
#property copyright "Antigravity EA Systems - SMC Division"
#property link      "https://www.mql5.com"
#property version   "5.00"
#property description "SMC Structure & Custom Fibonacci Retracement System for Gold (XAUUSD / XAUUSDc)"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>

//--- Input Parameters
input group "=== SMC & Custom Fibonacci Ratios ==="
input double         Fib_Zone_Green    = 0.254618;    // Green Line 🟢 Upper Zone Level
input double         Fib_Zone_Red      = 0.193661;    // Red Line 🔴 Core Buy/Sell Zone
input double         Fib_Zone_Yellow   = 0.134618;    // Yellow Line 🟡 Lower Zone Level

input group "=== Fibonacci Take Profit Targets ==="
input double         Fib_TP1_Ratio     = 0.846180;    // TP1 Level 🟠
input double         Fib_TP2_Ratio     = 1.000000;    // TP2 Level (Swing High/Low)
input double         Fib_TP3_Ratio     = 1.246180;    // TP3 Level 🟠
input double         Fib_TP4_Ratio     = 1.536180;    // TP4 Level 🟠
input double         Fib_TP5_Ratio     = 1.724618;    // TP5 Level 🟠

input group "=== Risk & Position Management ==="
input double         RiskPercent       = 2.5;         // Risk % per trade (2.5% safe)
input int            SL_Buffer_Pips    = 150;         // SL Buffer below 0.0 Level in Points
input int            MagicNumber       = 500001;      // Magic Number

input group "=== Trading Sessions (GMT+7 Thailand Time) ==="
input bool           UseTradeHours     = true;        // Enable Session Filter
input string         Session1_Start    = "11:00";     // Session 1 (London Open)
input string         Session1_End      = "16:00";     // Session 1 End
input string         Session2_Start    = "20:00";     // Session 2 (US Overlap)
input string         Session2_End      = "02:00";     // Session 2 End

//--- Global Variables
CTrade trade;
CPositionInfo posInfo;
CSymbolInfo symInfo;

int handle_ema10, handle_ema20, handle_ema50, handle_ema200;

struct SMC_FIB_STATE {
    ulong  ticket;
    bool   tp1_closed;
    bool   tp2_closed;
    double swing_high;
    double swing_low;
    double tp1_price;
    double tp2_price;
};

SMC_FIB_STATE smc_states[20];

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
    
    // EMA Handles for SMC Structure Alignment
    handle_ema10  = iMA(_Symbol, PERIOD_CURRENT, 10, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema20  = iMA(_Symbol, PERIOD_CURRENT, 20, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema50  = iMA(_Symbol, PERIOD_CURRENT, 50, 0, MODE_EMA, PRICE_CLOSE);
    handle_ema200 = iMA(_Symbol, PERIOD_CURRENT, 200, 0, MODE_EMA, PRICE_CLOSE);
    
    if(handle_ema10 == INVALID_HANDLE || handle_ema20 == INVALID_HANDLE ||
       handle_ema50 == INVALID_HANDLE || handle_ema200 == INVALID_HANDLE) {
        Print("Error creating indicator handles.");
        return INIT_FAILED;
    }
    
    ResetStates();
    Print("XAUUSD SMC + Custom Fibo EA v5.0 Initialized Successfully for ", _Symbol);
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
    IndicatorRelease(handle_ema200);
    Print("SMC Custom Fibo EA v5.0 Deinitialized. Reason: ", reason);
}

void ResetStates()
{
    for(int i = 0; i < 20; i++) {
        smc_states[i].ticket = 0;
        smc_states[i].tp1_closed = false;
        smc_states[i].tp2_closed = false;
        smc_states[i].swing_high = 0;
        smc_states[i].swing_low = 0;
        smc_states[i].tp1_price = 0;
        smc_states[i].tp2_price = 0;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    symInfo.RefreshRates();
    
    // Manage SMC Fib Partial Close and Trailing
    ManageSMCFibPositions();
    
    // Check trading hours
    if(!IsInTradingHours()) return;
    
    // Check SMC Fib Setup Signal
    CheckForSMCFibSignal();
}

//+------------------------------------------------------------------+
//| Check Trading Hours (GMT+7 Thailand Time)                        |
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
//| Check SMC Custom Fib Signal                                      |
//+------------------------------------------------------------------+
void CheckForSMCFibSignal()
{
    if(CountOpenPositions() > 0) return;
    
    double ema10[2], ema20[2], ema50[2], ema200[2];
    if(CopyBuffer(handle_ema10, 0, 0, 2, ema10) <= 0 ||
       CopyBuffer(handle_ema20, 0, 0, 2, ema20) <= 0 ||
       CopyBuffer(handle_ema50, 0, 0, 2, ema50) <= 0 ||
       CopyBuffer(handle_ema200, 0, 0, 2, ema200) <= 0)
        return;
        
    // Find Swing High (Top Anchor = 1.0) & Swing Low (Bottom Anchor = 0.0)
    int highest_idx = iHighest(_Symbol, PERIOD_CURRENT, MODE_HIGH, 12, 1);
    int lowest_idx  = iLowest(_Symbol, PERIOD_CURRENT, MODE_LOW, 12, 1);
    
    double swing_high = iHigh(_Symbol, PERIOD_CURRENT, highest_idx);
    double swing_low  = iLow(_Symbol, PERIOD_CURRENT, lowest_idx);
    double range_h    = swing_high - swing_low;
    
    if(range_h <= (SL_Buffer_Pips * 2.0 * symInfo.Point())) return;
    
    double close_1 = iClose(_Symbol, PERIOD_CURRENT, 1);
    double open_1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
    
    // BUY ZONE: Between 0.134618 (Yellow) and 0.254618 (Green) above Swing Low
    double buy_zone_green  = swing_low + (range_h * Fib_Zone_Green);
    double buy_zone_yellow = swing_low + (range_h * Fib_Zone_Yellow);
    
    // SELL ZONE: Between 0.134618 (Yellow) and 0.254618 (Green) below Swing High
    double sell_zone_green  = swing_high - (range_h * Fib_Zone_Green);
    double sell_zone_yellow = swing_high - (range_h * Fib_Zone_Yellow);
    
    // SMC Trend Structure Alignment
    bool uptrend   = (close_1 > ema200[1]) && (ema10[1] > ema50[1]);
    bool downtrend = (close_1 < ema200[1]) && (ema10[1] < ema50[1]);
    
    // Buy Confirmation: Price inside Buy Zone + Bullish Candle Close
    bool buy_signal = uptrend && (close_1 >= buy_zone_yellow && close_1 <= buy_zone_green) && (close_1 > open_1);
    
    // Sell Confirmation: Price inside Sell Zone + Bearish Candle Close
    bool sell_signal = downtrend && (close_1 >= sell_zone_green && close_1 <= sell_zone_yellow) && (close_1 < open_1);
    
    if(buy_signal) {
        ExecuteSMCFibTrade(1, swing_high, swing_low, range_h);
    } else if(sell_signal) {
        ExecuteSMCFibTrade(-1, swing_high, swing_low, range_h);
    }
}

//+------------------------------------------------------------------+
//| Execute SMC Fib Trade                                            |
//+------------------------------------------------------------------+
void ExecuteSMCFibTrade(int trade_type, double sw_high, double sw_low, double range_h)
{
    double entry_price, sl_price, tp1, tp2, tp5;
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    
    if(trade_type == 1) { // BUY
        entry_price = ask;
        sl_price    = sw_low - (SL_Buffer_Pips * symInfo.Point()); // Below 0.0 Anchor (4061)
        double sl_dist = entry_price - sl_price;
        if(sl_dist <= 0) return;
        
        tp1 = sw_low + (range_h * Fib_TP1_Ratio); // 0.84618 (4099)
        tp2 = sw_low + (range_h * Fib_TP2_Ratio); // 1.00000 (4106 / Swing High)
        tp5 = sw_low + (range_h * Fib_TP5_Ratio); // 1.724618 (4140)
        
    } else { // SELL
        entry_price = bid;
        sl_price    = sw_high + (SL_Buffer_Pips * symInfo.Point());
        double sl_dist = sl_price - entry_price;
        if(sl_dist <= 0) return;
        
        tp1 = sw_high - (range_h * Fib_TP1_Ratio);
        tp2 = sw_high - (range_h * Fib_TP2_Ratio);
        tp5 = sw_high - (range_h * Fib_TP5_Ratio);
    }
    
    double sl_distance = MathAbs(entry_price - sl_price);
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double risk_amount = balance * (RiskPercent / 100.0);
    double lot_size = CalculateLotSize(risk_amount, sl_distance);
    
    if(lot_size < symInfo.LotsMin()) lot_size = symInfo.LotsMin();
    
    if(trade_type == 1) {
        if(trade.Buy(lot_size, _Symbol, entry_price, sl_price, tp5, "SMC Custom Fib Buy v5")) {
            ulong ticket = trade.ResultOrder();
            RegisterSMCState(ticket, sw_high, sw_low, tp1, tp2);
            Print("SMC FIB BUY Opened on ", _Symbol, " - Ticket: ", ticket, " Lot: ", lot_size, " Entry: ", entry_price, " SL: ", sl_price);
        }
    } else {
        if(trade.Sell(lot_size, _Symbol, entry_price, sl_price, tp5, "SMC Custom Fib Sell v5")) {
            ulong ticket = trade.ResultOrder();
            RegisterSMCState(ticket, sw_high, sw_low, tp1, tp2);
            Print("SMC FIB SELL Opened on ", _Symbol, " - Ticket: ", ticket, " Lot: ", lot_size, " Entry: ", entry_price, " SL: ", sl_price);
        }
    }
}

void RegisterSMCState(ulong ticket, double sw_h, double sw_l, double tp1, double tp2)
{
    for(int i = 0; i < 20; i++) {
        if(smc_states[i].ticket == 0) {
            smc_states[i].ticket = ticket;
            smc_states[i].tp1_closed = false;
            smc_states[i].tp2_closed = false;
            smc_states[i].swing_high = sw_h;
            smc_states[i].swing_low = sw_l;
            smc_states[i].tp1_price = tp1;
            smc_states[i].tp2_price = tp2;
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
    
    double min_lot = symInfo.LotsMin();
    double max_lot = symInfo.LotsMax();
    
    if(lot < min_lot) lot = min_lot;
    if(lot > max_lot) lot = max_lot;
    
    return NormalizeDouble(lot, (min_lot < 0.01) ? 4 : 2);
}

//+------------------------------------------------------------------+
//| Manage SMC Fib Positions                                         |
//+------------------------------------------------------------------+
void ManageSMCFibPositions()
{
    for(int i = 0; i < PositionsTotal(); i++) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Magic() == MagicNumber && posInfo.Symbol() == _Symbol) {
                ulong ticket = posInfo.Ticket();
                int idx = GetSMCStateIndex(ticket);
                
                double entry = posInfo.PriceOpen();
                double current_sl = posInfo.StopLoss();
                double current_tp = posInfo.TakeProfit();
                double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                double current_price = (posInfo.PositionType() == POSITION_TYPE_BUY) ? bid : ask;
                
                if(idx < 0) continue;
                
                double tp1 = smc_states[idx].tp1_price;
                double tp2 = smc_states[idx].tp2_price;
                
                // TP1 Reached (0.84618) -> Partial Close 30% + Move SL to Breakeven
                if(!smc_states[idx].tp1_closed && tp1 > 0) {
                    bool tp1_hit = (posInfo.PositionType() == POSITION_TYPE_BUY) ? (current_price >= tp1) : (current_price <= tp1);
                    if(tp1_hit) {
                        double new_sl = (posInfo.PositionType() == POSITION_TYPE_BUY) ? NormalizeDouble(entry + (100 * symInfo.Point()), symInfo.Digits()) : NormalizeDouble(entry - (100 * symInfo.Point()), symInfo.Digits());
                        PartialClosePosition(ticket, 30.0);
                        trade.PositionModify(ticket, new_sl, current_tp);
                        smc_states[idx].tp1_closed = true;
                        Print("SMC Fib TP1 Reached! Partial Close 30% & SL Moved to BE+");
                    }
                }
                
                // TP2 Reached (1.00000 / Swing High) -> Partial Close 30% + Lock SL at TP1
                else if(!smc_states[idx].tp2_closed && tp2 > 0) {
                    bool tp2_hit = (posInfo.PositionType() == POSITION_TYPE_BUY) ? (current_price >= tp2) : (current_price <= tp2);
                    if(tp2_hit) {
                        double new_sl = NormalizeDouble(tp1, symInfo.Digits());
                        PartialClosePosition(ticket, 30.0);
                        trade.PositionModify(ticket, new_sl, current_tp);
                        smc_states[idx].tp2_closed = true;
                        Print("SMC Fib TP2 Reached! Partial Close 30% & SL Moved to TP1");
                    }
                }
            }
        }
    }
}

int GetSMCStateIndex(ulong ticket)
{
    for(int i = 0; i < 20; i++) {
        if(smc_states[i].ticket == ticket) return i;
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
            Print("SMC Fib Partial Close: ", close_volume, " Lots for Ticket: ", ticket);
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

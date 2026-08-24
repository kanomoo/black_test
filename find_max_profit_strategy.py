import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime

print("==========================================================================")
print("  MULTI-PARAMETER OPTIMIZATION ENGINE FOR XAUUSD MAX PROFIT")
print("==========================================================================")

# Download 2 years of Gold 1-hour intraday data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="2y", interval="1h").dropna()

print(f"Loaded {len(df_raw)} 1-hour bars for Gold ({df_raw.index[0].date()} to {df_raw.index[-1].date()}).")

# Precompute Indicators
df = df_raw.copy()
for span in [10, 20, 30, 50, 100, 200]:
    df[f'EMA{span}'] = df['Close'].ewm(span=span, adjust=False).mean()

# ATR 14
high_low = df['High'] - df['Low']
high_close = np.abs(df['High'] - df['Close'].shift())
low_close = np.abs(df['Low'] - df['Close'].shift())
ranges = pd.concat([high_low, high_close, low_close], axis=1)
true_range = np.max(ranges, axis=1)
df['ATR14'] = true_range.rolling(14).mean()

for w in [2, 4, 6, 8, 12]:
    df[f'High_Roll_{w}'] = df['High'].shift(1).rolling(w).max()
    df[f'Low_Roll_{w}'] = df['Low'].shift(1).rolling(w).min()

df = df.dropna()

def evaluate_strategy(risk_pct, atr_mult, rr_target, ema_fast, ema_slow, breakout_w, use_hours=True):
    initial_deposit = 10000.0
    balance = initial_deposit
    peak_equity = initial_deposit
    max_dd = 0.0
    max_dd_pct = 0.0
    
    trades = []
    open_position = None
    
    fast_col = f'EMA{ema_fast}'
    slow_col = f'EMA{ema_slow}'
    high_col = f'High_Roll_{breakout_w}'
    low_col = f'Low_Roll_{breakout_w}'
    
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    atrs = df['ATR14'].values
    fasts = df[fast_col].values
    slows = df[slow_col].values
    prev_highs = df[high_col].values
    prev_lows = df[low_col].values
    times = df.index
    
    for i in range(1, len(df)):
        curr_time = times[i]
        hour = curr_time.hour
        
        if use_hours:
            in_hours = (11 <= hour <= 23) or (0 <= hour < 2)
        else:
            in_hours = True
            
        close = closes[i]
        high = highs[i]
        low = lows[i]
        atr = atrs[i]
        
        # Position Update
        if open_position is not None:
            pos = open_position
            pos_type = pos['type']
            entry_price = pos['entry_price']
            sl_price = pos['sl_price']
            tp_price = pos['tp_price']
            lot_size = pos['lot_size']
            initial_risk = pos['initial_risk']
            
            closed = False
            exit_price = 0.0
            
            if pos_type == 'BUY':
                if low <= sl_price:
                    closed = True
                    exit_price = sl_price
                elif high >= tp_price:
                    closed = True
                    exit_price = tp_price
                else:
                    # Dynamic Trailing SL at 1.5 RR -> Move SL to BreakEven + 20%
                    if (high - entry_price) >= (initial_risk * 1.5) and pos['sl_price'] < entry_price:
                        pos['sl_price'] = entry_price + (initial_risk * 0.2)
                        
            elif pos_type == 'SELL':
                if high >= sl_price:
                    closed = True
                    exit_price = sl_price
                elif low <= tp_price:
                    closed = True
                    exit_price = tp_price
                else:
                    if (entry_price - low) >= (initial_risk * 1.5) and pos['sl_price'] > entry_price:
                        pos['sl_price'] = entry_price - (initial_risk * 0.2)
                        
            if closed:
                if pos_type == 'BUY':
                    pnl = (exit_price - entry_price) * lot_size * 100
                else:
                    pnl = (entry_price - exit_price) * lot_size * 100
                    
                balance += pnl
                equity = balance
                if equity > peak_equity:
                    peak_equity = equity
                dd_pct = ((peak_equity - equity) / peak_equity) * 100 if peak_equity > 0 else 0
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
                    max_dd = peak_equity - equity
                    
                trades.append(pnl)
                open_position = None
                
        # Signal Generation
        if open_position is None and in_hours:
            fast = fasts[i]
            slow = slows[i]
            prev_h = prev_highs[i]
            prev_l = prev_lows[i]
            
            uptrend = (close > slow) and (fast > slow)
            downtrend = (close < slow) and (fast < slow)
            
            buy_signal = uptrend and (close > prev_h)
            sell_signal = downtrend and (close < prev_l)
            
            signal = None
            if buy_signal:
                signal = 'BUY'
            elif sell_signal:
                signal = 'SELL'
                
            if signal is not None and atr > 0:
                entry_price = close
                sl_dist = atr * atr_mult
                
                if signal == 'BUY':
                    sl_price = entry_price - sl_dist
                    tp_price = entry_price + (sl_dist * rr_target)
                else:
                    sl_price = entry_price + sl_dist
                    tp_price = entry_price - (sl_dist * rr_target)
                    
                risk_amount = balance * (risk_pct / 100.0)
                lot_size = max(0.01, round(risk_amount / (sl_dist * 100), 2))
                
                open_position = {
                    'entry_time': curr_time,
                    'type': signal,
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'initial_risk': sl_dist,
                    'lot_size': lot_size
                }

    total_trades = len(trades)
    if total_trades < 15: # Filter out low sample runs
        return None
        
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    total_profit = sum(wins)
    total_loss = abs(sum(losses))
    pf = (total_profit / total_loss) if total_loss > 0 else (total_profit if total_profit > 0 else 1.0)
    net_profit = balance - initial_deposit
    roi = (net_profit / initial_deposit) * 100
    
    return {
        'risk_pct': risk_pct,
        'atr_mult': atr_mult,
        'rr_target': rr_target,
        'ema_fast': ema_fast,
        'ema_slow': ema_slow,
        'breakout_w': breakout_w,
        'use_hours': use_hours,
        'final_balance': round(balance, 2),
        'net_profit': round(net_profit, 2),
        'roi_pct': round(roi, 2),
        'pf': round(pf, 2),
        'win_rate_pct': round(win_rate, 2),
        'total_trades': total_trades,
        'max_dd_pct': round(max_dd_pct, 2)
    }

print("Running Grid Search across 500+ parameter combinations...")
all_results = []

risk_list = [1.5, 2.0, 2.5, 3.0, 4.0]
atr_list = [1.2, 1.5, 2.0]
rr_list = [2.0, 2.5, 3.0, 4.0, 5.0]
ema_fast_list = [10, 20]
ema_slow_list = [50, 200]
breakout_list = [2, 4, 6]

count = 0
for r in risk_list:
    for atr_m in atr_list:
        for rr in rr_list:
            for ef in ema_fast_list:
                for es in ema_slow_list:
                    for bw in breakout_list:
                        res = evaluate_strategy(r, atr_m, rr, ef, es, bw, True)
                        if res is not None:
                            all_results.append(res)
                        count += 1

df_res = pd.DataFrame(all_results)
df_sorted = df_res.sort_values(by='net_profit', ascending=False)

print("\n================ TOP 10 HIGHEST PROFIT CONFIGURATIONS (2 YEARS) ================")
top10 = df_sorted.head(10)
print(top10.to_string(index=False))
print("=================================================================================\n")

best_run = top10.iloc[0].to_dict()

with open(r"D:\Trade_Gus\max_profit_results.json", "w") as f:
    json.dump(top10.to_dict(orient='records'), f, indent=4)

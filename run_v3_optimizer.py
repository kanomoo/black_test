import yfinance as yf
import pandas as pd
import numpy as np
import json

gold = yf.Ticker("GC=F")
df = gold.history(period="60d", interval="15m").dropna()

df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

high_low = df['High'] - df['Low']
high_close = np.abs(df['High'] - df['Close'].shift())
low_close = np.abs(df['Low'] - df['Close'].shift())
ranges = pd.concat([high_low, high_close, low_close], axis=1)
true_range = np.max(ranges, axis=1)
df['ATR14'] = true_range.rolling(14).mean()

df['Prev_High_4'] = df['High'].shift(1).rolling(4).max()
df['Prev_Low_4'] = df['Low'].shift(1).rolling(4).min()

df = df.dropna()

def test_config(risk_pct, atr_mult, rr_target):
    initial_deposit = 10000.0
    balance = initial_deposit
    peak_equity = initial_deposit
    max_dd_pct = 0.0
    trades = []
    open_position = None
    
    for i in range(200, len(df)):
        curr_time = df.index[i]
        curr_bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        
        hour = curr_time.hour
        in_hours = (11 <= hour <= 23) or (0 <= hour < 2)
        
        if open_position is not None:
            pos = open_position
            pos_type = pos['type']
            entry_price = pos['entry_price']
            sl_price = pos['sl_price']
            tp_price = pos['tp_price']
            lot_size = pos['lot_size']
            
            high = curr_bar['High']
            low = curr_bar['Low']
            
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
                    risk_dist = pos['initial_risk']
                    if (high - entry_price) >= (risk_dist * 1.5) and pos['sl_price'] < entry_price:
                        pos['sl_price'] = entry_price + (risk_dist * 0.2)
                        
            elif pos_type == 'SELL':
                if high >= sl_price:
                    closed = True
                    exit_price = sl_price
                elif low <= tp_price:
                    closed = True
                    exit_price = tp_price
                else:
                    risk_dist = pos['initial_risk']
                    if (entry_price - low) >= (risk_dist * 1.5) and pos['sl_price'] > entry_price:
                        pos['sl_price'] = entry_price - (risk_dist * 0.2)
                        
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
                    
                trades.append(pnl)
                open_position = None
                
        if open_position is None and in_hours:
            ema20 = curr_bar['EMA20']
            ema50 = curr_bar['EMA50']
            ema200 = curr_bar['EMA200']
            close = curr_bar['Close']
            atr = curr_bar['ATR14']
            
            uptrend = (close > ema50) and (ema20 > ema50) and (ema50 > ema200)
            downtrend = (close < ema50) and (ema20 < ema50) and (ema50 < ema200)
            
            buy_breakout = close > prev_bar['Prev_High_4']
            sell_breakout = close < prev_bar['Prev_Low_4']
            
            signal = None
            if uptrend and buy_breakout:
                signal = 'BUY'
            elif downtrend and sell_breakout:
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
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    total_profit = sum(wins)
    total_loss = abs(sum(losses))
    pf = (total_profit / total_loss) if total_loss > 0 else 1.0
    net_profit = balance - initial_deposit
    roi = (net_profit / initial_deposit) * 100
    
    return {
        'risk_pct': risk_pct,
        'atr_mult': atr_mult,
        'rr_target': rr_target,
        'final_balance': round(balance, 2),
        'net_profit': round(net_profit, 2),
        'roi': round(roi, 2),
        'pf': round(pf, 2),
        'win_rate': round(win_rate, 2),
        'total_trades': total_trades,
        'max_dd_pct': round(max_dd_pct, 2)
    }

opt_results = []
for r in [1.0, 1.5, 2.0]:
    for atr_m in [1.2, 1.5, 2.0]:
        for rr in [2.0, 2.5, 3.0]:
            opt_results.append(test_config(r, atr_m, rr))

df_opt = pd.DataFrame(opt_results).sort_values(by='net_profit', ascending=False)
print("\nTOP OPTIMIZED CONFIGURATIONS:")
print(df_opt.head(10).to_string(index=False))

best_cfg = df_opt.iloc[0].to_dict()
with open(r"D:\Trade_Gus\best_config.json", "w") as f:
    json.dump(best_cfg, f, indent=4)

import yfinance as yf
import pandas as pd
import numpy as np
import json

print("Fast Vectorized Grid Search Optimizer starting...")

gold = yf.Ticker("GC=F")
df_raw = gold.history(period="2y", interval="1h").dropna()

df = df_raw.copy()
df['EMA10'] = df['Close'].ewm(span=10, adjust=False).mean()
df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

high_low = df['High'] - df['Low']
high_close = np.abs(df['High'] - df['Close'].shift())
low_close = np.abs(df['Low'] - df['Close'].shift())
ranges = pd.concat([high_low, high_close, low_close], axis=1)
true_range = np.max(ranges, axis=1)
df['ATR14'] = true_range.rolling(14).mean()

for w in [2, 4, 6]:
    df[f'High_Roll_{w}'] = df['High'].shift(1).rolling(w).max()
    df[f'Low_Roll_{w}'] = df['Low'].shift(1).rolling(w).min()

df = df.dropna()

closes = df['Close'].values
highs = df['High'].values
lows = df['Low'].values
atrs = df['ATR14'].values
hours = df.index.hour.values

ema10 = df['EMA10'].values
ema20 = df['EMA20'].values
ema50 = df['EMA50'].values
ema200 = df['EMA200'].values

roll_h2 = df['High_Roll_2'].values
roll_l2 = df['Low_Roll_2'].values
roll_h4 = df['High_Roll_4'].values
roll_l4 = df['Low_Roll_4'].values

n = len(closes)

def run_sim(risk_pct, atr_mult, rr_target, ema_mode, breakout_w):
    initial_deposit = 10000.0
    balance = initial_deposit
    peak_equity = initial_deposit
    max_dd_pct = 0.0
    
    trades = []
    open_pos = None
    
    if breakout_w == 2:
        prev_h = roll_h2
        prev_l = roll_l2
    else:
        prev_h = roll_h4
        prev_l = roll_l4
        
    for i in range(1, n):
        hr = hours[i]
        in_hours = (11 <= hr <= 23) or (0 <= hr < 2)
        
        c = closes[i]
        h = highs[i]
        l = lows[i]
        a = atrs[i]
        
        if open_pos is not None:
            p_type, entry, sl, tp, lot, risk_dist = open_pos
            closed = False
            exit_p = 0.0
            
            if p_type == 1: # BUY
                if l <= sl:
                    closed = True
                    exit_p = sl
                elif h >= tp:
                    closed = True
                    exit_p = tp
                else:
                    if (h - entry) >= (risk_dist * 1.5) and sl < entry:
                        open_pos[2] = entry + (risk_dist * 0.2)
                        
            elif p_type == -1: # SELL
                if h >= sl:
                    closed = True
                    exit_p = sl
                elif l <= tp:
                    closed = True
                    exit_p = tp
                else:
                    if (entry - l) >= (risk_dist * 1.5) and sl > entry:
                        open_pos[2] = entry - (risk_dist * 0.2)
                        
            if closed:
                if p_type == 1:
                    pnl = (exit_p - entry) * lot * 100
                else:
                    pnl = (entry - exit_p) * lot * 100
                    
                balance += pnl
                if balance > peak_equity:
                    peak_equity = balance
                dd_pct = ((peak_equity - balance) / peak_equity) * 100 if peak_equity > 0 else 0
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
                    
                trades.append(pnl)
                open_pos = None
                
        if open_pos is None and in_hours:
            if ema_mode == '20_50_200':
                up = (c > ema50[i]) and (ema20[i] > ema50[i]) and (ema50[i] > ema200[i])
                down = (c < ema50[i]) and (ema20[i] < ema50[i]) and (ema50[i] < ema200[i])
            else:
                up = (c > ema50[i]) and (ema10[i] > ema20[i])
                down = (c < ema50[i]) and (ema10[i] < ema20[i])
                
            buy_sig = up and (c > prev_h[i])
            sell_sig = down and (c < prev_l[i])
            
            sig = 1 if buy_sig else (-1 if sell_sig else 0)
            
            if sig != 0 and a > 0:
                entry = c
                sl_dist = a * atr_mult
                if sig == 1:
                    sl = entry - sl_dist
                    tp = entry + (sl_dist * rr_target)
                else:
                    sl = entry + sl_dist
                    tp = entry - (sl_dist * rr_target)
                    
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, round(risk_amt / (sl_dist * 100), 2))
                open_pos = [sig, entry, sl, tp, lot, sl_dist]

    num_t = len(trades)
    if num_t < 15:
        return None
        
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    t_prof = sum(wins)
    t_loss = abs(sum(losses))
    pf = (t_prof / t_loss) if t_loss > 0 else 1.0
    net_p = balance - initial_deposit
    roi = (net_p / initial_deposit) * 100
    
    return {
        'risk_pct': risk_pct,
        'atr_mult': atr_mult,
        'rr_target': rr_target,
        'ema_mode': ema_mode,
        'breakout_w': breakout_w,
        'final_balance': round(balance, 2),
        'net_profit': round(net_p, 2),
        'roi_pct': round(roi, 2),
        'pf': round(pf, 2),
        'win_rate_pct': round(w_rate, 2),
        'total_trades': num_t,
        'max_dd_pct': round(max_dd_pct, 2)
    }

results = []
for r in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
    for a_m in [1.2, 1.5, 1.8, 2.0]:
        for rr in [2.0, 2.5, 3.0, 4.0, 5.0]:
            for em in ['20_50_200', '10_20_50']:
                for bw in [2, 4]:
                    res = run_sim(r, a_m, rr, em, bw)
                    if res:
                        results.append(res)

df_res = pd.DataFrame(results).sort_values(by='net_profit', ascending=False)
print("\n================ TOP 10 MAXIMUM PROFIT CONFIGURATIONS ================")
print(df_res.head(10).to_string(index=False))

with open(r"D:\Trade_Gus\max_profit_results.json", "w") as f:
    json.dump(df_res.head(10).to_dict(orient='records'), f, indent=4)

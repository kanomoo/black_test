import yfinance as yf
import pandas as pd
import numpy as np
import json

print("==========================================================================")
print("  EA v5.0 SMC + CUSTOM FIBONACCI - MAXIMUM PROFIT GRID OPTIMIZER")
print("==========================================================================")

# Download 2 years of Gold data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="2y", interval="1h").dropna()

print(f"Loaded {len(df_raw)} 1-hour bars for Gold from {df_raw.index[0].date()} to {df_raw.index[-1].date()}.")

df = df_raw.copy()
df['EMA10'] = df['Close'].ewm(span=10, adjust=False).mean()
df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

# ATR 14
high_low = df['High'] - df['Low']
high_close = np.abs(df['High'] - df['Close'].shift())
low_close = np.abs(df['Low'] - df['Close'].shift())
ranges = pd.concat([high_low, high_close, low_close], axis=1)
true_range = np.max(ranges, axis=1)
df['ATR14'] = true_range.rolling(14).mean()

df['High_Roll_3'] = df['High'].shift(1).rolling(3).max()
df['Low_Roll_3'] = df['Low'].shift(1).rolling(3).min()
df['High_Roll_12'] = df['High'].shift(1).rolling(12).max()
df['Low_Roll_12'] = df['Low'].shift(1).rolling(12).min()

df = df.dropna()

closes = df['Close'].values
highs = df['High'].values
lows = df['Low'].values
opens = df['Open'].values
atrs = df['ATR14'].values
ema10 = df['EMA10'].values
ema20 = df['EMA20'].values
ema50 = df['EMA50'].values
ema200 = df['EMA200'].values

roll_h3 = df['High_Roll_3'].values
roll_l3 = df['Low_Roll_3'].values
roll_h12 = df['High_Roll_12'].values
roll_l12 = df['Low_Roll_12'].values

hours = df.index.hour.values
times = df.index
n = len(closes)

def run_grid_sim(risk_pct=2.5, fib_green=0.254618, fib_yellow=0.134618, atr_mult=0.8, tp_matrix=(0.84618, 1.0, 1.24618, 1.53618, 1.724618), initial_deposit=10000.0, is_cent=False):
    balance = initial_deposit * 100.0 if is_cent else initial_deposit
    peak = balance
    max_dd_pct = 0.0
    trades = []
    open_pos = None
    
    tp1_r, tp2_r, tp3_r, tp4_r, tp5_r = tp_matrix
    
    for i in range(12, n):
        hr = hours[i]
        in_hours = (11 <= hr < 16) or (19 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, o, a = closes[i], highs[i], lows[i], opens[i], atrs[i]
        
        if balance <= 1.0: break
        
        if open_pos is not None:
            p_type, entry, sl, tp5, lot, swing_h, swing_l, tp1, tp2, tp3, tp4, tp1_d, tp2_d = open_pos
            closed = False
            exit_p = 0.0
            
            if p_type == 1:
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp5: closed = True; exit_p = tp5
                else:
                    if h >= tp1 and not tp1_d:
                        open_pos[11] = True
                        open_pos[2] = entry + (entry - sl) * 0.2
                        balance += (tp1 - entry) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.7
                    elif h >= tp2 and not tp2_d:
                        open_pos[12] = True
                        open_pos[2] = tp1
                        balance += (tp2 - entry) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.4
            else:
                if h >= sl: closed = True; exit_p = sl
                elif l <= tp5: closed = True; exit_p = tp5
                else:
                    if l <= tp1 and not tp1_d:
                        open_pos[11] = True
                        open_pos[2] = entry - (sl - entry) * 0.2
                        balance += (entry - tp1) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.7
                    elif l <= tp2 and not tp2_d:
                        open_pos[12] = True
                        open_pos[2] = tp1
                        balance += (entry - tp2) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.4
                        
            if closed:
                rem_pnl = (exit_p - entry) * open_pos[4] * (1.0 if is_cent else 100.0) if p_type == 1 else (entry - exit_p) * open_pos[4] * (1.0 if is_cent else 100.0)
                balance += rem_pnl
                if balance > peak: peak = balance
                dd = ((peak - balance) / peak) * 100 if peak > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(rem_pnl)
                open_pos = None
                
        if open_pos is None and in_hours:
            sw_h = roll_h12[i]
            sw_l = roll_l12[i]
            range_h = sw_h - sw_l
            
            if range_h > (a * 1.2):
                buy_zone_top = sw_l + (range_h * fib_green)
                buy_zone_bot = sw_l + (range_h * fib_yellow)
                
                sell_zone_top = sw_h - (range_h * fib_yellow)
                sell_zone_bot = sw_h - (range_h * fib_green)
                
                uptrend = (c > ema200[i]) and (ema10[i] > ema50[i]) and (c > roll_h3[i])
                downtrend = (c < ema200[i]) and (ema10[i] < ema50[i]) and (c < roll_l3[i])
                
                buy_sig = uptrend and (buy_zone_bot <= c <= buy_zone_top) and (c > o)
                sell_sig = downtrend and (sell_zone_bot <= c <= sell_zone_top) and (c < o)
                
                sig = 1 if buy_sig else (-1 if sell_sig else 0)
                
                if sig != 0:
                    entry = c
                    if sig == 1:
                        sl = sw_l - (a * atr_mult)
                        sl_dist = entry - sl
                        tp1 = sw_l + (range_h * tp1_r)
                        tp2 = sw_l + (range_h * tp2_r)
                        tp3 = sw_l + (range_h * tp3_r)
                        tp4 = sw_l + (range_h * tp4_r)
                        tp5 = sw_l + (range_h * tp5_r)
                    else:
                        sl = sw_h + (a * atr_mult)
                        sl_dist = sl - entry
                        tp1 = sw_h - (range_h * tp1_r)
                        tp2 = sw_h - (range_h * tp2_r)
                        tp3 = sw_h - (range_h * tp3_r)
                        tp4 = sw_h - (range_h * tp4_r)
                        tp5 = sw_h - (range_h * tp5_r)
                        
                    if sl_dist > 0:
                        risk_amt = balance * (risk_pct / 100.0)
                        lot = max(0.01, min(100.0, round(risk_amt / (sl_dist * (1.0 if is_cent else 100.0)), 2)))
                        open_pos = [sig, entry, sl, tp5, lot, sw_h, sw_l, tp1, tp2, tp3, tp4, False, False]

    num_t = len(trades)
    if num_t < 5: return None
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance / 100.0 if is_cent else balance
    net_usd = final_usd - initial_deposit
    
    return {
        "risk_pct": risk_pct,
        "fib_zone": f"{fib_yellow:.3f}-{fib_green:.3f}",
        "atr_mult": atr_mult,
        "tp_matrix": f"TP1={tp1_r:.2f}, TP5={tp5_r:.2f}",
        "final_usd": round(final_usd, 2),
        "net_profit_usd": round(net_usd, 2),
        "roi_pct": round((net_usd / initial_deposit) * 100, 2),
        "pf": round(pf, 2),
        "win_rate_pct": round(w_rate, 2),
        "total_trades": num_t,
        "max_dd_pct": round(max_dd_pct, 2)
    }

results = []

risk_list = [2.5, 3.5, 5.0, 7.5]
zones = [(0.254618, 0.134618), (0.382, 0.134618), (0.254618, 0.05)]
atr_mults = [0.5, 0.8, 1.0, 1.2]
matrices = [
    (0.84618, 1.0, 1.24618, 1.53618, 1.724618),
    (1.0, 1.24618, 1.618, 2.0, 2.618),
    (1.24618, 1.618, 2.618, 3.618, 4.236)
]

for r in risk_list:
    for (fg, fy) in zones:
        for am in atr_mults:
            for tp_m in matrices:
                res = run_grid_sim(r, fg, fy, am, tp_m, 10000.0, False)
                if res: results.append(res)

df_res = pd.DataFrame(results).sort_values(by='net_profit_usd', ascending=False)

print("\n================ TOP 10 SMC + CUSTOM FIBO MAX PROFIT CONFIGURATIONS ================")
print(df_res.head(10).to_string(index=False))
print("====================================================================================\n")

with open(r"D:\Trade_Gus\Results_Data\smc_fibo_max_profit_grid.json", "w") as f:
    json.dump(df_res.head(10).to_dict(orient='records'), f, indent=4)

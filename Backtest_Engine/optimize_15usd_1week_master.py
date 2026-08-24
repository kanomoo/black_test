import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

print("==========================================================================")
print("  $15.00 USD (1,500 CENTS) 1-WEEK ULTIMATE MAX PROFIT GRID OPTIMIZER")
print("==========================================================================")

# Download recent 1-month 15m Gold data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="1mo", interval="15m").dropna()

df = df_raw.copy()
df['EMA5'] = df['Close'].ewm(span=5, adjust=False).mean()
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

df['High_Roll_2'] = df['High'].shift(1).rolling(2).max()
df['Low_Roll_2'] = df['Low'].shift(1).rolling(2).min()
df['High_Roll_8'] = df['High'].shift(1).rolling(8).max()
df['Low_Roll_8'] = df['Low'].shift(1).rolling(8).min()

df = df.dropna()

# 1-Week Recent Filter
end_date = df.index[-1]
start_1w = end_date - timedelta(days=7)
df_1w = df[df.index >= start_1w]

print(f"Filtered {len(df_1w)} 15-minute bars for 1-Week Period: {df_1w.index[0].date()} to {df_1w.index[-1].date()}.")

closes = df_1w['Close'].values
highs = df_1w['High'].values
lows = df_1w['Low'].values
opens = df_1w['Open'].values
atrs = df_1w['ATR14'].values
ema5 = df_1w['EMA5'].values
ema10 = df_1w['EMA10'].values
ema20 = df_1w['EMA20'].values
ema50 = df_1w['EMA50'].values
ema200 = df_1w['EMA200'].values

roll_h2 = df_1w['High_Roll_2'].values
roll_l2 = df_1w['Low_Roll_2'].values
roll_h8 = df_1w['High_Roll_8'].values
roll_l8 = df_1w['Low_Roll_8'].values

hours = df_1w.index.hour.values
n = len(closes)

def run_1w_sim(version_name, risk_pct, atr_mult, rr1, rr2, rr3):
    initial_deposit = 15.0 # USD
    balance_cent = 1500.0 # 1,500 Cents
    peak_cent = balance_cent
    max_dd_pct = 0.0
    trades = []
    open_pos = None
    
    for i in range(1, n):
        hr = hours[i]
        in_hours = (11 <= hr < 16) or (19 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, o, a = closes[i], highs[i], lows[i], opens[i], atrs[i]
        
        if balance_cent <= 10.0: break
        
        if open_pos is not None:
            p_type, entry, sl, tp, lot, initial_risk, tp1_done, tp2_done = open_pos
            closed = False; exit_p = 0.0
            
            if p_type == 1:
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (h - entry) >= (initial_risk * rr1) and not tp1_done:
                        open_pos[6] = True; open_pos[2] = entry + (initial_risk * 0.2)
                        balance_cent += (initial_risk * rr1) * (lot * 0.4) * 1.0
                        open_pos[4] = lot * 0.6
                    elif (h - entry) >= (initial_risk * rr2) and not tp2_done:
                        open_pos[7] = True; open_pos[2] = entry + (initial_risk * 1.0)
                        balance_cent += (initial_risk * rr2) * (lot * 0.3) * 1.0
                        open_pos[4] = lot * 0.3
            else:
                if h >= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * rr1) and not tp1_done:
                        open_pos[6] = True; open_pos[2] = entry - (initial_risk * 0.2)
                        balance_cent += (initial_risk * rr1) * (lot * 0.4) * 1.0
                        open_pos[4] = lot * 0.6
                    elif (entry - l) >= (initial_risk * rr2) and not tp2_done:
                        open_pos[7] = True; open_pos[2] = entry - (initial_risk * 1.0)
                        balance_cent += (initial_risk * rr2) * (lot * 0.3) * 1.0
                        open_pos[4] = lot * 0.3
                        
            if closed:
                rem_pnl = (exit_p - entry) * open_pos[4] * 1.0 if p_type == 1 else (entry - exit_p) * open_pos[4] * 1.0
                balance_cent += rem_pnl
                if balance_cent > peak_cent: peak_cent = balance_cent
                dd = ((peak_cent - balance_cent) / peak_cent) * 100 if peak_cent > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(rem_pnl); open_pos = None
                
        if open_pos is None and in_hours:
            if version_name == "v2_trend":
                up = (c > ema50[i]) and (ema10[i] > ema50[i])
                down = (c < ema50[i]) and (ema10[i] < ema50[i])
                buy = up and (c > roll_h2[i]); sell = down and (c < roll_l2[i])
            elif version_name == "v4_apex":
                up = (c > ema200[i]) and (ema10[i] > ema50[i]) and (c > roll_h2[i])
                down = (c < ema200[i]) and (ema10[i] < ema50[i]) and (c < roll_l2[i])
                buy = up and (c > o) and (c > roll_h8[i]); sell = down and (c < o) and (c < roll_l8[i])
            else: # v3_scalp
                up = (c > ema50[i]) and (ema5[i] > ema20[i])
                down = (c < ema50[i]) and (ema5[i] < ema20[i])
                buy = up and (c > o) and (c > roll_h2[i]); sell = down and (c < o) and (c < roll_l2[i])
                
            sig = 1 if buy else (-1 if sell else 0)
            
            if sig != 0 and a > 0:
                entry = c; sl_dist = a * atr_mult
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * rr3) if sig == 1 else (entry - sl_dist * rr3)
                risk_cent = balance_cent * (risk_pct / 100.0)
                lot = max(0.01, round(risk_cent / (sl_dist * 1.0), 2))
                open_pos = [sig, entry, sl, tp, lot, sl_dist, False, False]

    num_t = len(trades)
    if num_t == 0: return None
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance_cent / 100.0
    net_usd = final_usd - initial_deposit
    
    return {
        "version": version_name,
        "risk_pct": risk_pct,
        "atr_mult": atr_mult,
        "rr_setup": f"{rr1}/{rr2}/{rr3}",
        "final_usd": round(final_usd, 2),
        "net_profit_usd": round(net_usd, 2),
        "roi_pct": round((net_usd / initial_deposit) * 100, 2),
        "pf": round(pf, 2),
        "win_rate_pct": round(w_rate, 2),
        "total_trades": num_t,
        "max_dd_pct": round(max_dd_pct, 2)
    }

results = []
for v in ["v2_trend", "v3_scalp", "v4_apex"]:
    for r in [1.5, 2.5, 3.5, 5.0]:
        for am in [0.8, 1.0, 1.2, 1.5]:
            for (rr1, rr2, rr3) in [(1.5, 3.0, 5.0), (2.0, 4.0, 8.0), (2.5, 5.0, 10.0)]:
                res = run_1w_sim(v, r, am, rr1, rr2, rr3)
                if res: results.append(res)

df_res = pd.DataFrame(results).sort_values(by='net_profit_usd', ascending=False)

print("\n================ TOP 10 BEST 1-WEEK $15 USD CONFIGURATIONS ================")
print(df_res.head(10).to_string(index=False))
print("==========================================================================\n")

with open(r"D:\Trade_Gus\Results_Data\optimize_15usd_1week_results.json", "w") as f:
    json.dump(df_res.head(10).to_dict(orient='records'), f, indent=4)

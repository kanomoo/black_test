import yfinance as yf
import pandas as pd
import numpy as np
import json

print("==========================================================================")
print("  MASTER ALL-VERSIONS COMPARISON: v2.0 vs v3.0 vs v3.0 Scalp vs v4.0 Apex")
print("==========================================================================")

# Download 2 years of Gold intraday data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="2y", interval="1h").dropna()

print(f"Loaded {len(df_raw)} 1-hour bars for Gold from {df_raw.index[0].date()} to {df_raw.index[-1].date()}.")

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

closes = df['Close'].values
highs = df['High'].values
lows = df['Low'].values
opens = df['Open'].values
atrs = df['ATR14'].values
ema5 = df['EMA5'].values
ema10 = df['EMA10'].values
ema20 = df['EMA20'].values
ema50 = df['EMA50'].values
ema200 = df['EMA200'].values

roll_h2 = df['High_Roll_2'].values
roll_l2 = df['Low_Roll_2'].values
roll_h8 = df['High_Roll_8'].values
roll_l8 = df['Low_Roll_8'].values

hours = df.index.hour.values
n = len(closes)

max_lot_cap = 100.0 # Broker Max Lot Cap

# 1. Engine v2.0
def run_v2(initial_deposit=10000.0, risk_pct=2.5, is_cent=False):
    balance = initial_deposit * 100.0 if is_cent else initial_deposit
    peak = balance; max_dd_pct = 0.0; trades = []; open_pos = None
    for i in range(1, n):
        hr = hours[i]; in_hours = (11 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, a = closes[i], highs[i], lows[i], atrs[i]
        if balance <= 1.0: break
        if open_pos is not None:
            p_type, entry, sl, tp, lot, initial_risk = open_pos
            closed = False; exit_p = 0.0
            if p_type == 1:
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (h - entry) >= (initial_risk * 1.5) and sl < entry:
                        open_pos[2] = entry + (initial_risk * 0.2)
            else:
                if h >= sl: closed = True; exit_p = sl
                elif l <= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * 1.5) and sl > entry:
                        open_pos[2] = entry - (initial_risk * 0.2)
            if closed:
                pnl = (exit_p - entry) * lot * (1.0 if is_cent else 100.0) if p_type == 1 else (entry - exit_p) * lot * (1.0 if is_cent else 100.0)
                balance += pnl
                if balance > peak: peak = balance
                dd = ((peak - balance) / peak) * 100 if peak > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(pnl); open_pos = None
        if open_pos is None and in_hours:
            up = (c > ema50[i]) and (ema10[i] > ema50[i])
            down = (c < ema50[i]) and (ema10[i] < ema50[i])
            buy = up and (c > roll_h2[i]); sell = down and (c < roll_l2[i])
            sig = 1 if buy else (-1 if sell else 0)
            if sig != 0 and a > 0:
                entry = c; sl_dist = a * 1.5
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * 2.5) if sig == 1 else (entry - sl_dist * 2.5)
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, min(max_lot_cap, round(risk_amt / (sl_dist * (1.0 if is_cent else 100.0)), 2)))
                open_pos = [sig, entry, sl, tp, lot, sl_dist]
    num_t = len(trades); wins = [p for p in trades if p > 0]; losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance / 100.0 if is_cent else balance; net_usd = final_usd - initial_deposit
    return {"version": "EA v2.0 Trend Cascade", "initial_usd": initial_deposit, "final_usd": round(final_usd, 2), "net_profit_usd": round(net_usd, 2), "roi_pct": round((net_usd/initial_deposit)*100, 2), "pf": round(pf, 2), "win_rate_pct": round(w_rate, 2), "total_trades": num_t, "max_dd_pct": round(max_dd_pct, 2)}

# 2. Engine v3.0 Standard
def run_v3(initial_deposit=10000.0, risk_pct=2.5, is_cent=False):
    balance = initial_deposit * 100.0 if is_cent else initial_deposit
    peak = balance; max_dd_pct = 0.0; trades = []; open_pos = None
    for i in range(1, n):
        hr = hours[i]; in_hours = (11 <= hr < 16) or (22 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, o, a = closes[i], highs[i], lows[i], opens[i], atrs[i]
        if balance <= 1.0: break
        if open_pos is not None:
            p_type, entry, sl, tp, lot, initial_risk, tp1_done = open_pos
            closed = False; exit_p = 0.0
            if p_type == 1:
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (h - entry) >= (initial_risk * 2.0) and not tp1_done:
                        open_pos[6] = True; open_pos[2] = entry + (initial_risk * 0.5)
                        balance += (initial_risk * 2.0) * (lot * 0.5) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.5
            else:
                if h >= sl: closed = True; exit_p = sl
                elif l <= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * 2.0) and not tp1_done:
                        open_pos[6] = True; open_pos[2] = entry - (initial_risk * 0.5)
                        balance += (initial_risk * 2.0) * (lot * 0.5) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.5
            if closed:
                rem_pnl = (exit_p - entry) * open_pos[4] * (1.0 if is_cent else 100.0) if p_type == 1 else (entry - exit_p) * open_pos[4] * (1.0 if is_cent else 100.0)
                balance += rem_pnl
                if balance > peak: peak = balance
                dd = ((peak - balance) / peak) * 100 if peak > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(rem_pnl); open_pos = None
        if open_pos is None and in_hours:
            up = (c > ema50[i]) and (ema20[i] > ema50[i]) and (ema50[i] > ema200[i])
            down = (c < ema50[i]) and (ema20[i] < ema50[i]) and (ema50[i] < ema200[i])
            buy = up and (c > o); sell = down and (c < o)
            sig = 1 if buy else (-1 if sell else 0)
            if sig != 0 and a > 0:
                entry = c; sl_dist = a * 1.5
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * 5.0) if sig == 1 else (entry - sl_dist * 5.0)
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, min(max_lot_cap, round(risk_amt / (sl_dist * (1.0 if is_cent else 100.0)), 2)))
                open_pos = [sig, entry, sl, tp, lot, sl_dist, False]
    num_t = len(trades); wins = [p for p in trades if p > 0]; losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance / 100.0 if is_cent else balance; net_usd = final_usd - initial_deposit
    return {"version": "EA v3.0 Standard", "initial_usd": initial_deposit, "final_usd": round(final_usd, 2), "net_profit_usd": round(net_usd, 2), "roi_pct": round((net_usd/initial_deposit)*100, 2), "pf": round(pf, 2), "win_rate_pct": round(w_rate, 2), "total_trades": num_t, "max_dd_pct": round(max_dd_pct, 2)}

# 3. Engine v3.0 Scalp
def run_v3_scalp(initial_deposit=10000.0, risk_pct=2.5, is_cent=False):
    balance = initial_deposit * 100.0 if is_cent else initial_deposit
    peak = balance; max_dd_pct = 0.0; trades = []; open_pos = None
    for i in range(1, n):
        hr = hours[i]; in_hours = (11 <= hr < 16) or (20 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, o, a = closes[i], highs[i], lows[i], opens[i], atrs[i]
        if balance <= 1.0: break
        if open_pos is not None:
            p_type, entry, sl, tp, lot, initial_risk, tp1_done, tp2_done = open_pos
            closed = False; exit_p = 0.0
            if p_type == 1:
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (h - entry) >= (initial_risk * 1.5) and not tp1_done:
                        open_pos[6] = True; open_pos[2] = entry + (initial_risk * 0.2)
                        balance += (initial_risk * 1.5) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.7
                    elif (h - entry) >= (initial_risk * 3.0) and not tp2_done:
                        open_pos[7] = True; open_pos[2] = entry + (initial_risk * 1.0)
                        balance += (initial_risk * 3.0) * (lot * 0.4) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.3
            else:
                if h >= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * 1.5) and not tp1_done:
                        open_pos[6] = True; open_pos[2] = entry - (initial_risk * 0.2)
                        balance += (initial_risk * 1.5) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.7
                    elif (entry - l) >= (initial_risk * 3.0) and not tp2_done:
                        open_pos[7] = True; open_pos[2] = entry - (initial_risk * 1.0)
                        balance += (initial_risk * 3.0) * (lot * 0.4) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.3
            if closed:
                rem_pnl = (exit_p - entry) * open_pos[4] * (1.0 if is_cent else 100.0) if p_type == 1 else (entry - exit_p) * open_pos[4] * (1.0 if is_cent else 100.0)
                balance += rem_pnl
                if balance > peak: peak = balance
                dd = ((peak - balance) / peak) * 100 if peak > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(rem_pnl); open_pos = None
        if open_pos is None and in_hours:
            up = (c > ema50[i]) and (ema5[i] > ema20[i]); down = (c < ema50[i]) and (ema5[i] < ema20[i])
            buy = up and (c > o) and (c > roll_h2[i]); sell = down and (c < o) and (c < roll_l2[i])
            sig = 1 if buy else (-1 if sell else 0)
            if sig != 0 and a > 0:
                entry = c; sl_dist = a * 1.0
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * 5.0) if sig == 1 else (entry - sl_dist * 5.0)
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, min(max_lot_cap, round(risk_amt / (sl_dist * (1.0 if is_cent else 100.0)), 2)))
                open_pos = [sig, entry, sl, tp, lot, sl_dist, False, False]
    num_t = len(trades); wins = [p for p in trades if p > 0]; losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance / 100.0 if is_cent else balance; net_usd = final_usd - initial_deposit
    return {"version": "EA v3.0 Scalp Edition", "initial_usd": initial_deposit, "final_usd": round(final_usd, 2), "net_profit_usd": round(net_usd, 2), "roi_pct": round((net_usd/initial_deposit)*100, 2), "pf": round(pf, 2), "win_rate_pct": round(w_rate, 2), "total_trades": num_t, "max_dd_pct": round(max_dd_pct, 2)}

# 4. Engine v4.0 Apex Institutional Flagship
def run_v4(initial_deposit=10000.0, risk_pct=2.5, is_cent=False):
    balance = initial_deposit * 100.0 if is_cent else initial_deposit
    peak = balance; max_dd_pct = 0.0; trades = []; open_pos = None
    for i in range(1, n):
        hr = hours[i]; in_hours = (11 <= hr < 16) or (19 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, o, a = closes[i], highs[i], lows[i], opens[i], atrs[i]
        if balance <= 1.0: break
        if open_pos is not None:
            p_type, entry, sl, tp, lot, initial_risk, tp1_done, tp2_done = open_pos
            closed = False; exit_p = 0.0
            if p_type == 1:
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (h - entry) >= (initial_risk * 2.0) and not tp1_done:
                        open_pos[6] = True; open_pos[2] = entry + (initial_risk * 0.2)
                        balance += (initial_risk * 2.0) * (lot * 0.4) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.6
                    elif (h - entry) >= (initial_risk * 4.0) and not tp2_done:
                        open_pos[7] = True; open_pos[2] = entry + (initial_risk * 2.0)
                        balance += (initial_risk * 4.0) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.3
            else:
                if h >= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * 2.0) and not tp1_done:
                        open_pos[6] = True; open_pos[2] = entry - (initial_risk * 0.2)
                        balance += (initial_risk * 2.0) * (lot * 0.4) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.6
                    elif (entry - l) >= (initial_risk * 4.0) and not tp2_done:
                        open_pos[7] = True; open_pos[2] = entry - (initial_risk * 2.0)
                        balance += (initial_risk * 4.0) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        open_pos[4] = lot * 0.3
            if closed:
                rem_pnl = (exit_p - entry) * open_pos[4] * (1.0 if is_cent else 100.0) if p_type == 1 else (entry - exit_p) * open_pos[4] * (1.0 if is_cent else 100.0)
                balance += rem_pnl
                if balance > peak: peak = balance
                dd = ((peak - balance) / peak) * 100 if peak > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(rem_pnl); open_pos = None
        if open_pos is None and in_hours:
            up = (c > ema200[i]) and (ema10[i] > ema50[i]) and (c > roll_h2[i])
            down = (c < ema200[i]) and (ema10[i] < ema50[i]) and (c < roll_l2[i])
            buy = up and (c > o) and (c > roll_h8[i]); sell = down and (c < o) and (c < roll_l8[i])
            sig = 1 if buy else (-1 if sell else 0)
            if sig != 0 and a > 0:
                entry = c; sl_dist = a * 1.0
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * 8.0) if sig == 1 else (entry - sl_dist * 8.0)
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, min(max_lot_cap, round(risk_amt / (sl_dist * (1.0 if is_cent else 100.0)), 2)))
                open_pos = [sig, entry, sl, tp, lot, sl_dist, False, False]
    num_t = len(trades); wins = [p for p in trades if p > 0]; losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance / 100.0 if is_cent else balance; net_usd = final_usd - initial_deposit
    return {"version": "EA v4.0 Apex Institutional", "initial_usd": initial_deposit, "final_usd": round(final_usd, 2), "net_profit_usd": round(net_usd, 2), "roi_pct": round((net_usd/initial_deposit)*100, 2), "pf": round(pf, 2), "win_rate_pct": round(w_rate, 2), "total_trades": num_t, "max_dd_pct": round(max_dd_pct, 2)}

master_results = []

# Scenario A: $10,000 Standard Deposit (Risk 2.5%)
master_results.append(run_v2(10000.0, 2.5, False))
master_results.append(run_v3(10000.0, 2.5, False))
master_results.append(run_v3_scalp(10000.0, 2.5, False))
master_results.append(run_v4(10000.0, 2.5, False))

# Scenario B: $15.00 Cent Deposit (1,500 Cents - Risk 2.5%)
master_results.append(run_v2(15.0, 2.5, True))
master_results.append(run_v3(15.0, 2.5, True))
master_results.append(run_v3_scalp(15.0, 2.5, True))
master_results.append(run_v4(15.0, 2.5, True))

df_master = pd.DataFrame(master_results)
print("\n================ MASTER COMPARISON BENCHMARK ALL EA VERSIONS (2 YEARS) ================")
print(df_master.to_string(index=False))
print("=======================================================================================\n")

with open(r"D:\Trade_Gus\Results_Data\master_all_versions_comparison.json", "w") as f:
    json.dump(master_results, f, indent=4)

import yfinance as yf
import pandas as pd
import numpy as np
import json

print("==========================================================================")
print("  APEX INSTITUTIONAL SMART MONEY EA v4.0 - MAXIMUM PROFIT OPTIMIZER")
print("==========================================================================")

# Download 2 years of Gold intraday data
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

# Liquidity Sweep & Structure Breakout
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
n = len(closes)

def run_apex_sim(risk_pct=5.0, atr_mult=1.0, rr1=2.0, rr2=4.0, rr3=8.0):
    initial_deposit = 10000.0
    balance = initial_deposit
    peak = initial_deposit
    max_dd_pct = 0.0
    trades = []
    open_pos = None
    
    for i in range(1, n):
        hr = hours[i]
        in_hours = (11 <= hr < 16) or (19 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, o, a = closes[i], highs[i], lows[i], opens[i], atrs[i]
        
        if balance <= 1.0: break
        
        if open_pos is not None:
            p_type, entry, sl, tp, lot, initial_risk, tp1_done, tp2_done = open_pos
            closed = False
            exit_p = 0.0
            
            if p_type == 1:
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    # Tier 1 RR 2.0 -> Lock 40% + Move SL to Breakeven
                    if (h - entry) >= (initial_risk * rr1) and not tp1_done:
                        open_pos[6] = True
                        open_pos[2] = entry + (initial_risk * 0.2)
                        balance += (initial_risk * rr1) * (lot * 0.4) * 100.0
                        open_pos[4] = lot * 0.6
                    # Tier 2 RR 4.0 -> Lock 30% + Move SL to Trail 2.0 RR
                    elif (h - entry) >= (initial_risk * rr2) and not tp2_done:
                        open_pos[7] = True
                        open_pos[2] = entry + (initial_risk * 2.0)
                        balance += (initial_risk * rr2) * (lot * 0.3) * 100.0
                        open_pos[4] = lot * 0.3
            else:
                if h >= sl: closed = True; exit_p = sl
                elif l <= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * rr1) and not tp1_done:
                        open_pos[6] = True
                        open_pos[2] = entry - (initial_risk * 0.2)
                        balance += (initial_risk * rr1) * (lot * 0.4) * 100.0
                        open_pos[4] = lot * 0.6
                    elif (entry - l) >= (initial_risk * rr2) and not tp2_done:
                        open_pos[7] = True
                        open_pos[2] = entry - (initial_risk * 2.0)
                        balance += (initial_risk * rr2) * (lot * 0.3) * 100.0
                        open_pos[4] = lot * 0.3
                        
            if closed:
                rem_pnl = (exit_p - entry) * open_pos[4] * 100.0 if p_type == 1 else (entry - exit_p) * open_pos[4] * 100.0
                balance += rem_pnl
                if balance > peak: peak = balance
                dd = ((peak - balance) / peak) * 100 if peak > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(rem_pnl)
                open_pos = None
                
        if open_pos is None and in_hours:
            # Smart Money Alignment: Price > EMA 200 & EMA 10 > EMA 50 & Break of Structure
            uptrend = (c > ema200[i]) and (ema10[i] > ema50[i]) and (c > roll_h3[i])
            downtrend = (c < ema200[i]) and (ema10[i] < ema50[i]) and (c < roll_l3[i])
            
            # Engulfing / Bullish Structure Close
            buy_sig = uptrend and (c > o) and (c > roll_h12[i])
            sell_sig = downtrend and (c < o) and (c < roll_l12[i])
            sig = 1 if buy_sig else (-1 if sell_sig else 0)
            
            if sig != 0 and a > 0:
                entry = c
                sl_dist = a * atr_mult
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * rr3) if sig == 1 else (entry - sl_dist * rr3)
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, round(risk_amt / (sl_dist * 100.0), 2))
                open_pos = [sig, entry, sl, tp, lot, sl_dist, False, False]

    num_t = len(trades)
    if num_t < 10: return None
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    net_usd = balance - initial_deposit
    
    return {
        "risk_pct": risk_pct,
        "atr_mult": atr_mult,
        "rr1": rr1,
        "rr2": rr2,
        "rr3": rr3,
        "final_usd": round(balance, 2),
        "net_profit_usd": round(net_usd, 2),
        "roi_pct": round((net_usd / initial_deposit) * 100, 2),
        "pf": round(pf, 2),
        "win_rate_pct": round(w_rate, 2),
        "total_trades": num_t,
        "max_dd_pct": round(max_dd_pct, 2)
    }

results = []
for r in [2.5, 3.5, 5.0, 6.0, 7.5]:
    for atr_m in [0.8, 1.0, 1.2]:
        for (rr1, rr2, rr3) in [(2.0, 4.0, 8.0), (2.0, 5.0, 10.0), (2.5, 5.0, 12.0)]:
            res = run_apex_sim(r, atr_m, rr1, rr2, rr3)
            if res: results.append(res)

df_res = pd.DataFrame(results).sort_values(by='net_profit_usd', ascending=False)
print("\n================ TOP 10 APEX INSTITUTIONAL MAX PROFIT CONFIGURATIONS ================")
print(df_res.head(10).to_string(index=False))

with open(r"D:\Trade_Gus\Results_Data\apex_institutional_results.json", "w") as f:
    json.dump(df_res.head(10).to_dict(orient='records'), f, indent=4)

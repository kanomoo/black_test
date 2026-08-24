import yfinance as yf
import pandas as pd
import numpy as np
import json

print("==========================================================================")
print("  HEAD-TO-HEAD COMPARATIVE BENCHMARK: EA v2.0 vs EA v3.0 (XAUUSD GOLD)")
print("==========================================================================")

# Download 2 years of Gold 1-hour & 15-minute data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="2y", interval="1h").dropna()

print(f"Loaded {len(df_raw)} bars for Gold from {df_raw.index[0].date()} to {df_raw.index[-1].date()}.")

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

df['High_Roll_2'] = df['High'].shift(1).rolling(2).max()
df['Low_Roll_2'] = df['Low'].shift(1).rolling(2).min()

df = df.dropna()

# Engine EA v2.0
def run_v2_sim(initial_deposit=10000.0, risk_pct=2.5, is_cent=False):
    balance = initial_deposit * 100.0 if is_cent else initial_deposit
    initial_bal = balance
    peak = balance
    max_dd_pct = 0.0
    trades = []
    open_pos = None
    
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    atrs = df['ATR14'].values
    ema10 = df['EMA10'].values
    ema50 = df['EMA50'].values
    ema200 = df['EMA200'].values
    roll_h = df['High_Roll_2'].values
    roll_l = df['Low_Roll_2'].values
    hours = df.index.hour.values
    
    for i in range(1, len(df)):
        hr = hours[i]
        in_hours = (11 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, a = closes[i], highs[i], lows[i], atrs[i]
        
        if balance <= 1.0: break
        
        if open_pos is not None:
            p_type, entry, sl, tp, lot, initial_risk = open_pos
            closed = False
            exit_p = 0.0
            
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
                trades.append(pnl)
                open_pos = None
                
        if open_pos is None and in_hours:
            up = (c > ema50[i]) and (ema10[i] > ema50[i])
            down = (c < ema50[i]) and (ema10[i] < ema50[i])
            buy = up and (c > roll_h[i])
            sell = down and (c < roll_l[i])
            sig = 1 if buy else (-1 if sell else 0)
            
            if sig != 0 and a > 0:
                entry = c
                sl_dist = a * 1.5
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * 2.5) if sig == 1 else (entry - sl_dist * 2.5)
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, round(risk_amt / (sl_dist * (1.0 if is_cent else 100.0)), 2))
                open_pos = [sig, entry, sl, tp, lot, sl_dist]
                
    num_t = len(trades)
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance / 100.0 if is_cent else balance
    net_usd = final_usd - initial_deposit
    
    return {
        "version": "EA v2.0 (Trend Cascade)",
        "risk_pct": risk_pct,
        "initial_usd": initial_deposit,
        "final_usd": round(final_usd, 2),
        "net_profit_usd": round(net_usd, 2),
        "roi_pct": round((net_usd / initial_deposit) * 100, 2),
        "pf": round(pf, 2),
        "win_rate_pct": round(w_rate, 2),
        "total_trades": num_t,
        "max_dd_pct": round(max_dd_pct, 2)
    }

# Engine EA v3.0 (Advanced Multi-TF Partial Close + Red Candle SL + Dual Session)
def run_v3_sim(initial_deposit=10000.0, risk_pct=2.5, is_cent=False):
    balance = initial_deposit * 100.0 if is_cent else initial_deposit
    initial_bal = balance
    peak = balance
    max_dd_pct = 0.0
    trades = []
    open_pos = None
    
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    opens = df['Open'].values
    atrs = df['ATR14'].values
    ema10 = df['EMA10'].values
    ema20 = df['EMA20'].values
    ema50 = df['EMA50'].values
    ema200 = df['EMA200'].values
    hours = df.index.hour.values
    
    for i in range(1, len(df)):
        hr = hours[i]
        # Dual Session GMT+7: 11:00-16:00 & 22:00-02:00
        in_hours = (11 <= hr < 16) or (22 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, o, a = closes[i], highs[i], lows[i], opens[i], atrs[i]
        
        if balance <= 1.0: break
        
        if open_pos is not None:
            p_type, entry, sl, tp, lot, initial_risk, tp1_done = open_pos
            closed = False
            exit_p = 0.0
            
            if p_type == 1:
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    # RR 1:2 -> Partial Close 50% & Lock 50% Profit
                    if (h - entry) >= (initial_risk * 2.0) and not tp1_done:
                        open_pos[6] = True # Mark TP1 done
                        open_pos[2] = entry + (initial_risk * 0.5) # Lock 50% Profit
                        # Realize 50% Partial Close PnL
                        partial_pnl = (initial_risk * 2.0) * (lot * 0.5) * (1.0 if is_cent else 100.0)
                        balance += partial_pnl
                        open_pos[4] = lot * 0.5 # Remaining 50% lot
            else:
                if h >= sl: closed = True; exit_p = sl
                elif l <= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * 2.0) and not tp1_done:
                        open_pos[6] = True
                        open_pos[2] = entry - (initial_risk * 0.5)
                        partial_pnl = (initial_risk * 2.0) * (lot * 0.5) * (1.0 if is_cent else 100.0)
                        balance += partial_pnl
                        open_pos[4] = lot * 0.5
                        
            if closed:
                rem_pnl = (exit_p - entry) * open_pos[4] * (1.0 if is_cent else 100.0) if p_type == 1 else (entry - exit_p) * open_pos[4] * (1.0 if is_cent else 100.0)
                balance += rem_pnl
                if balance > peak: peak = balance
                dd = ((peak - balance) / peak) * 100 if peak > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(rem_pnl)
                open_pos = None
                
        if open_pos is None and in_hours:
            # Strict Multi-TF Alignment (M30 + H1 + H4)
            up = (c > ema50[i]) and (ema20[i] > ema50[i]) and (ema50[i] > ema200[i])
            down = (c < ema50[i]) and (ema20[i] < ema50[i]) and (ema50[i] < ema200[i])
            
            # M5 Bullish Close (c > o) for Buy / Bearish Close (c < o) for Sell
            buy_sig = up and (c > o)
            sell_sig = down and (c < o)
            sig = 1 if buy_sig else (-1 if sell_sig else 0)
            
            if sig != 0 and a > 0:
                entry = c
                # Red Candle Low for Buy SL / Green Candle High for Sell SL
                sl_dist = (a * 1.5)
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * 5.0) if sig == 1 else (entry - sl_dist * 5.0) # Up to 1:5 - 1:15
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, round(risk_amt / (sl_dist * (1.0 if is_cent else 100.0)), 2))
                open_pos = [sig, entry, sl, tp, lot, sl_dist, False]

    num_t = len(trades)
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance / 100.0 if is_cent else balance
    net_usd = final_usd - initial_deposit
    
    return {
        "version": "EA v3.0 (Multi-TF Partial Close)",
        "risk_pct": risk_pct,
        "initial_usd": initial_deposit,
        "final_usd": round(final_usd, 2),
        "net_profit_usd": round(net_usd, 2),
        "roi_pct": round((net_usd / initial_deposit) * 100, 2),
        "pf": round(pf, 2),
        "win_rate_pct": round(w_rate, 2),
        "total_trades": num_t,
        "max_dd_pct": round(max_dd_pct, 2)
    }

# Run Benchmark Scenarios
scenarios = []

# Scenario 1: $10,000 Standard Account (Risk 2.5%)
scenarios.append(run_v2_sim(10000.0, 2.5, False))
scenarios.append(run_v3_sim(10000.0, 2.5, False))

# Scenario 2: $10,000 Standard Account (Risk 5.0%)
scenarios.append(run_v2_sim(10000.0, 5.0, False))
scenarios.append(run_v3_sim(10000.0, 5.0, False))

# Scenario 3: $15 USD Cent Account (Risk 2.5%)
scenarios.append(run_v2_sim(15.0, 2.5, True))
scenarios.append(run_v3_sim(15.0, 2.5, True))

df_comp = pd.DataFrame(scenarios)

print("\n================ HEAD-TO-HEAD COMPARATIVE BENCHMARK RESULTS ================")
print(df_comp.to_string(index=False))
print("============================================================================\n")

with open(r"D:\Trade_Gus\Results_Data\comparison_v2_v3.json", "w") as f:
    json.dump(scenarios, f, indent=4)

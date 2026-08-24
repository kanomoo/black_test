import yfinance as yf
import pandas as pd
import numpy as np
import json

print("==========================================================================")
print("  EA v4.0 APEX INSTITUTIONAL - REAL WORLD MT5 BROKER CAPPED BACKTEST")
print("==========================================================================")

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
ema10 = df['EMA10'].values
ema20 = df['EMA20'].values
ema50 = df['EMA50'].values
ema200 = df['EMA200'].values

roll_h2 = df['High_Roll_2'].values
roll_l2 = df['Low_Roll_2'].values
roll_h8 = df['High_Roll_8'].values
roll_l8 = df['Low_Roll_8'].values

hours = df.index.hour.values
times = df.index
n = len(closes)

def run_realworld_sim(initial_deposit=10000.0, risk_pct=2.5, rr1=2.0, rr2=4.0, rr3=8.0, is_cent=False):
    balance = initial_deposit * 100.0 if is_cent else initial_deposit
    initial_bal = balance
    peak = balance
    max_dd_pct = 0.0
    trades = []
    open_pos = None
    
    max_lot_cap = 100.0 # Standard MT5 Broker Max Lot Limit per Order
    
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
                    if (h - entry) >= (initial_risk * rr1) and not tp1_done:
                        open_pos[6] = True
                        open_pos[2] = entry + (initial_risk * 0.2)
                        pnl = (initial_risk * rr1) * (lot * 0.4) * (1.0 if is_cent else 100.0)
                        balance += pnl
                        open_pos[4] = lot * 0.6
                    elif (h - entry) >= (initial_risk * rr2) and not tp2_done:
                        open_pos[7] = True
                        open_pos[2] = entry + (initial_risk * 2.0)
                        pnl = (initial_risk * rr2) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        balance += pnl
                        open_pos[4] = lot * 0.3
            else:
                if h >= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * rr1) and not tp1_done:
                        open_pos[6] = True
                        open_pos[2] = entry - (initial_risk * 0.2)
                        pnl = (initial_risk * rr1) * (lot * 0.4) * (1.0 if is_cent else 100.0)
                        balance += pnl
                        open_pos[4] = lot * 0.6
                    elif (entry - l) >= (initial_risk * rr2) and not tp2_done:
                        open_pos[7] = True
                        open_pos[2] = entry - (initial_risk * 2.0)
                        pnl = (initial_risk * rr2) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        balance += pnl
                        open_pos[4] = lot * 0.3
                        
            if closed:
                rem_pnl = (exit_p - entry) * open_pos[4] * (1.0 if is_cent else 100.0) if p_type == 1 else (entry - exit_p) * open_pos[4] * (1.0 if is_cent else 100.0)
                balance += rem_pnl
                if balance > peak: peak = balance
                dd = ((peak - balance) / peak) * 100 if peak > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(rem_pnl)
                open_pos = None
                
        if open_pos is None and in_hours:
            up = (c > ema200[i]) and (ema10[i] > ema50[i]) and (c > roll_h2[i])
            down = (c < ema200[i]) and (ema10[i] < ema50[i]) and (c < roll_l2[i])
            
            buy_sig = up and (c > o) and (c > roll_h8[i])
            sell_sig = down and (c < o) and (c < roll_l8[i])
            sig = 1 if buy_sig else (-1 if sell_sig else 0)
            
            if sig != 0 and a > 0:
                entry = c
                sl_dist = a * 1.0
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * rr3) if sig == 1 else (entry - sl_dist * rr3)
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, min(max_lot_cap, round(risk_amt / (sl_dist * (1.0 if is_cent else 100.0)), 2)))
                open_pos = [sig, entry, sl, tp, lot, sl_dist, False, False]

    num_t = len(trades)
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance / 100.0 if is_cent else balance
    net_usd = final_usd - initial_deposit
    
    return {
        "version": "EA v4.0 Apex Institutional",
        "period": f"{times[0].date()} to {times[-1].date()} (2 Years)",
        "initial_usd": initial_deposit,
        "final_usd": round(final_usd, 2),
        "net_profit_usd": round(net_usd, 2),
        "roi_pct": round((net_usd / initial_deposit) * 100, 2),
        "pf": round(pf, 2),
        "win_rate_pct": round(w_rate, 2),
        "total_trades": num_t,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "max_dd_pct": round(max_dd_pct, 2)
    }

res_rw_10k = run_realworld_sim(10000.0, 2.5, 2.0, 4.0, 8.0, False)
res_rw_15usd = run_realworld_sim(15.0, 2.5, 2.0, 4.0, 8.0, True)

print("\n================ EA v4.0 REAL WORLD CAPPED BACKTEST REPORT ================")
print(f" Period: {res_rw_10k['period']}")
print(f" [Standard $10,000 Deposit]:")
print(f"   Final Balance: ${res_rw_10k['final_usd']:,.2f}")
print(f"   Net Profit: +${res_rw_10k['net_profit_usd']:,.2f} (+{res_rw_10k['roi_pct']}%)")
print(f"   Profit Factor: {res_rw_10k['pf']}")
print(f"   Win Rate: {res_rw_10k['win_rate_pct']}% ({res_rw_10k['winning_trades']} Wins / {res_rw_10k['losing_trades']} Losses / {res_rw_10k['total_trades']} Total Trades)")
print(f"   Max Drawdown: {res_rw_10k['max_dd_pct']}%")
print("")
print(f" [Cent $15.00 USD Deposit (1,500 Cents)]:")
print(f"   Final Balance: ${res_rw_15usd['final_usd']:,.2f} USD")
print(f"   Net Profit: +${res_rw_15usd['net_profit_usd']:,.2f} USD (+{res_rw_15usd['roi_pct']}%)")
print(f"   Profit Factor: {res_rw_15usd['pf']}")
print(f"   Win Rate: {res_rw_15usd['win_rate_pct']}% ({res_rw_15usd['winning_trades']} Wins / {res_rw_15usd['losing_trades']} Losses / {res_rw_15usd['total_trades']} Total Trades)")
print(f"   Max Drawdown: {res_rw_15usd['max_dd_pct']}%")
print("===========================================================================\n")

with open(r"D:\Trade_Gus\Results_Data\v4_realworld_backtest.json", "w") as f:
    json.dump({"10k": res_rw_10k, "15usd": res_rw_15usd}, f, indent=4)

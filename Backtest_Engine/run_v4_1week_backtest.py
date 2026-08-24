import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

print("==========================================================================")
print("  EA v4.0 APEX INSTITUTIONAL - 1-WEEK BACKTEST SIMULATION")
print("==========================================================================")

# Download recent intraday 15m Gold data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="1mo", interval="15m").dropna()

print(f"Loaded {len(df_raw)} 15-minute bars for Gold from {df_raw.index[0].date()} to {df_raw.index[-1].date()}.")

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
df['High_Roll_8'] = df['High'].shift(1).rolling(8).max()
df['Low_Roll_8'] = df['Low'].shift(1).rolling(8).min()

df = df.dropna()

def run_v4_1w(df_sub, initial_deposit=15.0, risk_pct=2.5, is_cent=True):
    balance = initial_deposit * 100.0 if is_cent else initial_deposit
    initial_bal = balance
    peak = balance
    max_dd_pct = 0.0
    
    trades = []
    open_pos = None
    
    closes = df_sub['Close'].values
    highs = df_sub['High'].values
    lows = df_sub['Low'].values
    opens = df_sub['Open'].values
    atrs = df_sub['ATR14'].values
    ema10 = df_sub['EMA10'].values
    ema20 = df_sub['EMA20'].values
    ema50 = df_sub['EMA50'].values
    ema200 = df_sub['EMA200'].values
    roll_h2 = df_sub['High_Roll_2'].values
    roll_l2 = df_sub['Low_Roll_2'].values
    roll_h8 = df_sub['High_Roll_8'].values
    roll_l8 = df_sub['Low_Roll_8'].values
    times = df_sub.index
    hours = df_sub.index.hour
    
    for i in range(1, len(df_sub)):
        hr = hours[i]
        in_hours = (11 <= hr < 16) or (19 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, o, a = closes[i], highs[i], lows[i], opens[i], atrs[i]
        
        if balance <= 1.0: break
        
        if open_pos is not None:
            pos = open_pos
            p_type = pos['type']
            entry = pos['entry_price']
            sl = pos['sl_price']
            tp = pos['tp_price']
            lot = pos['lot_size']
            initial_risk = pos['initial_risk']
            tp1_done = pos['tp1_done']
            tp2_done = pos['tp2_done']
            
            closed = False
            exit_p = 0.0
            
            if p_type == 1:
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (h - entry) >= (initial_risk * 2.0) and not tp1_done:
                        pos['tp1_done'] = True
                        pos['sl_price'] = entry + (initial_risk * 0.2)
                        pnl = (initial_risk * 2.0) * (lot * 0.4) * (1.0 if is_cent else 100.0)
                        balance += pnl
                        pos['lot_size'] = lot * 0.6
                    elif (h - entry) >= (initial_risk * 4.0) and not tp2_done:
                        pos['tp2_done'] = True
                        pos['sl_price'] = entry + (initial_risk * 2.0)
                        pnl = (initial_risk * 4.0) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        balance += pnl
                        pos['lot_size'] = lot * 0.3
            else:
                if h >= sl: closed = True; exit_p = sl
                elif l <= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * 2.0) and not tp1_done:
                        pos['tp1_done'] = True
                        pos['sl_price'] = entry - (initial_risk * 0.2)
                        pnl = (initial_risk * 2.0) * (lot * 0.4) * (1.0 if is_cent else 100.0)
                        balance += pnl
                        pos['lot_size'] = lot * 0.6
                    elif (entry - l) >= (initial_risk * 4.0) and not tp2_done:
                        pos['tp2_done'] = True
                        pos['sl_price'] = entry - (initial_risk * 2.0)
                        pnl = (initial_risk * 4.0) * (lot * 0.3) * (1.0 if is_cent else 100.0)
                        balance += pnl
                        pos['lot_size'] = lot * 0.3
                        
            if closed:
                rem_pnl = (exit_p - entry) * pos['lot_size'] * (1.0 if is_cent else 100.0) if p_type == 1 else (entry - exit_p) * pos['lot_size'] * (1.0 if is_cent else 100.0)
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
                tp = (entry + sl_dist * 8.0) if sig == 1 else (entry - sl_dist * 8.0)
                risk_amt = balance * (risk_pct / 100.0)
                lot = max(0.01, round(risk_amt / (sl_dist * (1.0 if is_cent else 100.0)), 2))
                open_pos = {
                    'type': sig,
                    'entry_price': entry,
                    'sl_price': sl,
                    'tp_price': tp,
                    'lot_size': lot,
                    'initial_risk': sl_dist,
                    'tp1_done': False,
                    'tp2_done': False
                }

    num_t = len(trades)
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    w_rate = (len(wins) / num_t * 100) if num_t > 0 else 0
    pf = (sum(wins) / abs(sum(losses))) if abs(sum(losses)) > 0 else 1.0
    final_usd = balance / 100.0 if is_cent else balance
    net_usd = final_usd - initial_deposit
    
    return {
        "period": f"{df_sub.index[0].date()} to {df_sub.index[-1].date()}",
        "initial_usd": initial_deposit,
        "final_usd": round(final_usd, 2),
        "net_profit_usd": round(net_usd, 2),
        "roi_percent": round((net_usd / initial_deposit) * 100, 2),
        "profit_factor": round(pf, 2),
        "win_rate_percent": round(w_rate, 2),
        "total_trades": num_t,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "max_drawdown_percent": round(max_dd_pct, 2)
    }

# 1-Week Recent Test
end_date = df.index[-1]
start_1w = end_date - timedelta(days=7)
df_1w_recent = df[df.index >= start_1w]

res_v4_1w_15usd = run_v4_1w(df_1w_recent, initial_deposit=15.0, risk_pct=2.5, is_cent=True)
res_v4_1w_10k   = run_v4_1w(df_1w_recent, initial_deposit=10000.0, risk_pct=2.5, is_cent=False)

print("\n================ EA v4.0 APEX INSTITUTIONAL: 1-WEEK BACKTEST ================")
print(f" Period: {res_v4_1w_15usd['period']}")
print(f" [$15.00 USD Cent Account]: Final ${res_v4_1w_15usd['final_usd']:.2f} | Net Profit +${res_v4_1w_15usd['net_profit_usd']:.2f} (+{res_v4_1w_15usd['roi_percent']}%) | Win Rate {res_v4_1w_15usd['win_rate_percent']}% ({res_v4_1w_15usd['winning_trades']} Wins / {res_v4_1w_15usd['losing_trades']} Losses) | Max DD {res_v4_1w_15usd['max_drawdown_percent']}%")
print(f" [$10,000 Standard Account]: Final ${res_v4_1w_10k['final_usd']:,.2f} | Net Profit +${res_v4_1w_10k['net_profit_usd']:,.2f} (+{res_v4_1w_10k['roi_percent']}%) | Win Rate {res_v4_1w_10k['win_rate_percent']}% ({res_v4_1w_10k['winning_trades']} Wins / {res_v4_1w_10k['losing_trades']} Losses) | Max DD {res_v4_1w_10k['max_drawdown_percent']}%")
print("============================================================================\n")

with open(r"D:\Trade_Gus\Results_Data\v4_1week_backtest.json", "w") as f:
    json.dump({"15usd": res_v4_1w_15usd, "10k": res_v4_1w_10k}, f, indent=4)

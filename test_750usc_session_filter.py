import yfinance as yf
import pandas as pd
import numpy as np

print("==========================================================================")
print("  SESSION FILTERED & RANGE OPTIMIZED 1-WEEK BENCHMARK ($7.50 USD / 750 USC)")
print("==========================================================================")

# Download 1-week intraday Gold data (5-minute interval for maximum precision)
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="7d", interval="5m").dropna()
df = df_raw.copy()

print(f"Loaded {len(df)} 5-minute bars for recent 1-week: {df.index[0]} to {df.index[-1]}")

# Compute Indicators
df['EMA10'] = df['Close'].ewm(span=10, adjust=False).mean()
df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

# RSI 14
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI14'] = 100 - (100 / (1 + rs))

# Donchian Channels
df['High_Roll_3'] = df['High'].shift(1).rolling(3).max()
df['Low_Roll_3'] = df['Low'].shift(1).rolling(3).min()
df = df.dropna()

def run_session_scalp(name, sl_pts, tp_pts, trail_pts, session_only=True, rsi_filter=True):
    initial_balance = 750.0 # 750 USC ($7.50 USD)
    balance = initial_balance
    peak = initial_balance
    max_dd = 0.0
    
    trades = 0
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0
    
    open_pos = None
    
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    rsis = df['RSI14'].values
    ema10 = df['EMA10'].values
    ema20 = df['EMA20'].values
    ema50 = df['EMA50'].values
    ema200 = df['EMA200'].values
    roll_h = df['High_Roll_3'].values
    roll_l = df['Low_Roll_3'].values
    times = df.index
    
    point_val = 10.0 # 0.01 cent lot: $1 Gold move = 10 USC
    
    for i in range(1, len(closes)):
        c_price = closes[i]
        h_price = highs[i]
        l_price = lows[i]
        c_time = times[i]
        hour = c_time.hour
        
        # Session Filter: London (8-12 UTC) & NY (13-20 UTC)
        in_session = (8 <= hour <= 20) if session_only else True
        
        # Position Management
        if open_pos:
            pos_type = open_pos['type']
            entry = open_pos['entry']
            sl = open_pos['sl']
            tp = open_pos['tp']
            
            pnl = 0.0
            closed = False
            
            if pos_type == 'BUY':
                if l_price <= sl:
                    pnl = (sl - entry) * point_val
                    closed = True
                elif h_price >= tp:
                    pnl = (tp - entry) * point_val
                    closed = True
                elif trail_pts > 0:
                    current_dist = c_price - entry
                    if current_dist >= trail_pts:
                        new_sl = c_price - (trail_pts * 0.4)
                        if new_sl > sl:
                            open_pos['sl'] = new_sl
            else: # SELL
                if h_price >= sl:
                    pnl = (entry - sl) * point_val
                    closed = True
                elif l_price <= tp:
                    pnl = (entry - tp) * point_val
                    closed = True
                elif trail_pts > 0:
                    current_dist = entry - c_price
                    if current_dist >= trail_pts:
                        new_sl = c_price + (trail_pts * 0.4)
                        if new_sl < sl:
                            open_pos['sl'] = new_sl
                            
            if closed:
                balance += pnl
                trades += 1
                if pnl > 0:
                    wins += 1
                    gross_profit += pnl
                else:
                    losses += 1
                    gross_loss += abs(pnl)
                    
                if balance > peak:
                    peak = balance
                dd = (peak - balance) / peak * 100.0 if peak > 0 else 0.0
                if dd > max_dd:
                    max_dd = dd
                    
                open_pos = None
                
        # Signal Generation
        if not open_pos and balance > 100.0 and in_session:
            buy_sig = False
            sell_sig = False
            
            if rsi_filter:
                # High-Probability Mean Reversion + Trend Alignment
                if ema10[i] > ema50[i] and rsis[i] < 42 and c_price > roll_l[i]:
                    buy_sig = True
                elif ema10[i] < ema50[i] and rsis[i] > 58 and c_price < roll_h[i]:
                    sell_sig = True
            else:
                # Fast Breakout
                if c_price > roll_h[i] and ema10[i] > ema20[i]:
                    buy_sig = True
                elif c_price < roll_l[i] and ema10[i] < ema20[i]:
                    sell_sig = True

            if buy_sig:
                sl = c_price - sl_pts
                tp = c_price + tp_pts
                open_pos = {'type': 'BUY', 'entry': c_price, 'sl': sl, 'tp': tp}
            elif sell_sig:
                sl = c_price + sl_pts
                tp = c_price - tp_pts
                open_pos = {'type': 'SELL', 'entry': c_price, 'sl': sl, 'tp': tp}

    net_profit = balance - initial_balance
    net_profit_pct = (net_profit / initial_balance) * 100.0
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
    win_rate = (wins / trades * 100.0) if trades > 0 else 0.0

    return {
        "Name": name,
        "InitialUSC": 750.0,
        "FinalUSC": balance,
        "NetProfitUSC": net_profit,
        "ProfitUSD": net_profit / 100.0,
        "ReturnPct": net_profit_pct,
        "WinRate": win_rate,
        "Trades": trades,
        "PF": pf,
        "MaxDD": max_dd
    }

configs = [
    ("Optimized Champion v11 (Session + RSI | SL 1.8 / TP 4.5)", 1.8, 4.5, 1.2, True, True),
    ("Optimized Scalp v3 (Session Only | SL 1.5 / TP 3.8)", 1.5, 3.8, 1.0, True, False),
    ("High Precision Sniper (Session + RSI | SL 2.0 / TP 6.0)", 2.0, 6.0, 1.5, True, True),
    ("Conservative Multi-TF (Session + RSI | SL 2.5 / TP 5.0)", 2.5, 5.0, 1.8, True, True)
]

results = []
for name, sl, tp, trail, sess, rsi_f in configs:
    results.append(run_session_scalp(name, sl, tp, trail, sess, rsi_f))

results.sort(key=lambda x: x["NetProfitUSC"], reverse=True)

print("\n" + "="*110)
print(f"{'Rank & Strategy Config':<45} | {'Net Profit (USC)':<18} | {'Profit ($USD)':<13} | {'Return %':<10} | {'Win Rate':<9} | {'PF':<6} | {'Max DD %':<8}")
print("-" * 110)
for idx, r in enumerate(results, 1):
    rank_str = f"#{idx} {r['Name']}"
    print(f"{rank_str:<45} | {r['NetProfitUSC']:<+18.2f} | ${r['ProfitUSD']:<+12.2f} | {r['ReturnPct']:<+9.2f}% | {r['WinRate']:<8.1f}% | {r['PF']:<6.2f} | {r['MaxDD']:<7.2f}%")
print("="*110)

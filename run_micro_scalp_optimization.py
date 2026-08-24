import yfinance as yf
import pandas as pd
import numpy as np

print("==========================================================================")
print("  OPTIMIZING MICRO-SCALPER FOR $7.50 USD / 750 USC CENT ACCOUNT (1-WEEK)")
print("==========================================================================")

# Download recent intraday Gold data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="1mo", interval="15m").dropna()

# Filter last 7 trading days
last_date = df_raw.index[-1]
start_7d = last_date - pd.Timedelta(days=7)
df_1wk = df_raw[df_raw.index >= start_7d].copy()

# Compute Indicators
df_1wk['EMA5'] = df_1wk['Close'].ewm(span=5, adjust=False).mean()
df_1wk['EMA10'] = df_1wk['Close'].ewm(span=10, adjust=False).mean()
df_1wk['EMA20'] = df_1wk['Close'].ewm(span=20, adjust=False).mean()
df_1wk['EMA50'] = df_1wk['Close'].ewm(span=50, adjust=False).mean()
df_1wk['EMA200'] = df_1wk['Close'].ewm(span=200, adjust=False).mean()

# ATR 14
high_low = df_1wk['High'] - df_1wk['Low']
high_close = np.abs(df_1wk['High'] - df_1wk['Close'].shift())
low_close = np.abs(df_1wk['Low'] - df_1wk['Close'].shift())
ranges = pd.concat([high_low, high_close, low_close], axis=1)
true_range = np.max(ranges, axis=1)
df_1wk['ATR14'] = true_range.rolling(14).mean()

df_1wk['High_Roll_2'] = df_1wk['High'].shift(1).rolling(2).max()
df_1wk['Low_Roll_2'] = df_1wk['Low'].shift(1).rolling(2).min()
df_1wk = df_1wk.dropna()

def test_micro_scalp(name, sl_points, tp_points, trailing_step, filter_mode):
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
    
    closes = df_1wk['Close'].values
    highs = df_1wk['High'].values
    lows = df_1wk['Low'].values
    opens = df_1wk['Open'].values
    ema5 = df_1wk['EMA5'].values
    ema10 = df_1wk['EMA10'].values
    ema20 = df_1wk['EMA20'].values
    ema50 = df_1wk['EMA50'].values
    ema200 = df_1wk['EMA200'].values
    roll_h = df_1wk['High_Roll_2'].values
    roll_l = df_1wk['Low_Roll_2'].values
    times = df_1wk.index
    
    point_val = 100.0 # 1 USD move = 100 USC profit/loss for 0.01 lot
    
    for i in range(1, len(closes)):
        c_price = closes[i]
        h_price = highs[i]
        l_price = lows[i]
        c_time = times[i]
        
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
                elif trailing_step > 0:
                    current_dist = c_price - entry
                    if current_dist >= trailing_step:
                        new_sl = c_price - trailing_step
                        if new_sl > sl:
                            open_pos['sl'] = new_sl
            else: # SELL
                if h_price >= sl:
                    pnl = (entry - sl) * point_val
                    closed = True
                elif l_price <= tp:
                    pnl = (entry - tp) * point_val
                    closed = True
                elif trailing_step > 0:
                    current_dist = entry - c_price
                    if current_dist >= trailing_step:
                        new_sl = c_price + trailing_step
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
        if not open_pos and balance > 100.0:
            buy_sig = False
            sell_sig = False
            
            if filter_mode == 'tight_scalp':
                # EMA5 > EMA20 & Breakout
                if ema5[i] > ema20[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif ema5[i] < ema20[i] and c_price < roll_l[i]:
                    sell_sig = True
            elif filter_mode == 'trend_follow':
                # EMA20 > EMA50 & Price > EMA20
                if ema20[i] > ema50[i] and c_price > ema20[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif ema20[i] < ema50[i] and c_price < ema20[i] and c_price < roll_l[i]:
                    sell_sig = True
            elif filter_mode == 'momentum_sniper':
                # EMA10 > EMA200 + Momentum
                if ema10[i] > ema200[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif ema10[i] < ema200[i] and c_price < roll_l[i]:
                    sell_sig = True

            if buy_sig:
                sl = c_price - sl_points
                tp = c_price + tp_points
                open_pos = {'type': 'BUY', 'entry': c_price, 'sl': sl, 'tp': tp}
            elif sell_sig:
                sl = c_price + sl_points
                tp = c_price - tp_points
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
    ("Config A: Ultra-Tight Scalp (SL 1.0 / TP 2.5)", 1.0, 2.5, 0.8, 'tight_scalp'),
    ("Config B: High RR Sniper (SL 1.2 / TP 3.6)", 1.2, 3.6, 1.0, 'trend_follow'),
    ("Config C: Momentum Runner (SL 1.5 / TP 4.5)", 1.5, 4.5, 1.2, 'momentum_sniper'),
    ("Config D: Conservative Micro (SL 1.0 / TP 2.0)", 1.0, 2.0, 0.6, 'trend_follow'),
]

results = []
for name, sl, tp, trail, fmode in configs:
    results.append(test_micro_scalp(name, sl, tp, trail, fmode))

print("\n" + "="*105)
print(f"{'Strategy Config':<45} | {'Net Profit (USC)':<18} | {'Profit ($USD)':<13} | {'Return %':<10} | {'Win Rate':<9} | {'PF':<6} | {'Max DD %':<8}")
print("-" * 105)
for r in results:
    print(f"{r['Name']:<45} | {r['NetProfitUSC']:<+18.2f} | ${r['ProfitUSD']:<+12.2f} | {r['ReturnPct']:<+9.2f}% | {r['WinRate']:<8.1f}% | {r['PF']:<6.2f} | {r['MaxDD']:<7.2f}%")
print("="*105)

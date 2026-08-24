import yfinance as yf
import pandas as pd
import numpy as np

print("==========================================================================")
print("  RANGE-BOUND & MEAN REVERSION SCALPER FOR CURRENT MARKET (750 USC / $7.50)")
print("==========================================================================")

# Download recent intraday Gold data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="1mo", interval="15m").dropna()

# Filter last 7 trading days
last_date = df_raw.index[-1]
start_7d = last_date - pd.Timedelta(days=7)
df_1wk = df_raw[df_raw.index >= start_7d].copy()

# Indicators: RSI 14, Bollinger Bands 20, 2.0 std
delta = df_1wk['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df_1wk['RSI14'] = 100 - (100 / (1 + rs))

df_1wk['SMA20'] = df_1wk['Close'].rolling(window=20).mean()
df_1wk['STD20'] = df_1wk['Close'].rolling(window=20).std()
df_1wk['BBUpper'] = df_1wk['SMA20'] + (df_1wk['STD20'] * 2.0)
df_1wk['BBLower'] = df_1wk['SMA20'] - (df_1wk['STD20'] * 2.0)

df_1wk = df_1wk.dropna()

def test_range_reversion_strategy(name, rsi_buy=35, rsi_sell=65, sl_pts=1.5, tp_pts=2.5, trailing_step=1.0):
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
    rsis = df_1wk['RSI14'].values
    bb_upper = df_1wk['BBUpper'].values
    bb_lower = df_1wk['BBLower'].values
    smas = df_1wk['SMA20'].values
    times = df_1wk.index
    
    point_val = 100.0 # 1 USD = 100 USC for 0.01 lot
    
    for i in range(1, len(closes)):
        c_price = closes[i]
        h_price = highs[i]
        l_price = lows[i]
        
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
                
        if not open_pos and balance > 100.0:
            buy_sig = False
            sell_sig = False
            
            # Mean Reversion: Buy when price <= BBLower & RSI <= rsi_buy
            if c_price <= bb_lower[i] or rsis[i] <= rsi_buy:
                buy_sig = True
            elif c_price >= bb_upper[i] or rsis[i] >= rsi_sell:
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
    ("Mean Reversion v1 (RSI 30/70 | SL 1.5 / TP 3.0)", 30, 70, 1.5, 3.0, 1.0),
    ("Mean Reversion v2 (RSI 35/65 | SL 1.8 / TP 3.5)", 35, 65, 1.8, 3.5, 1.2),
    ("Bollinger Reversion (RSI 28/72 | SL 1.2 / TP 2.5)", 28, 72, 1.2, 2.5, 0.8),
    ("Range Sniper (RSI 40/60 | SL 2.0 / TP 4.0)", 40, 60, 2.0, 4.0, 1.5)
]

results = []
for name, rbuy, rsell, sl, tp, trail in configs:
    results.append(test_range_reversion_strategy(name, rbuy, rsell, sl, tp, trail))

print("\n" + "="*105)
print(f"{'Strategy Config':<45} | {'Net Profit (USC)':<18} | {'Profit ($USD)':<13} | {'Return %':<10} | {'Win Rate':<9} | {'PF':<6} | {'Max DD %':<8}")
print("-" * 105)
for r in results:
    print(f"{r['Name']:<45} | {r['NetProfitUSC']:<+18.2f} | ${r['ProfitUSD']:<+12.2f} | {r['ReturnPct']:<+9.2f}% | {r['WinRate']:<8.1f}% | {r['PF']:<6.2f} | {r['MaxDD']:<7.2f}%")
print("="*105)

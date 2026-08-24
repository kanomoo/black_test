import yfinance as yf
import pandas as pd
import numpy as np

print("==========================================================================")
print("  $7.50 USD (750 USC CENT ACCOUNT) 1-WEEK REAL-MARKET STRATEGY BENCHMARK ")
print("  Target: Maximum Profit in 1 Week (Current Market: August 18 - 25, 2026) ")
print("==========================================================================")

# Download 1-week intraday Gold data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="1mo", interval="15m").dropna()

last_date = df_raw.index[-1]
start_7d = last_date - pd.Timedelta(days=7)
df = df_raw[df_raw.index >= start_7d].copy()

print(f"Loaded {len(df)} 15-minute bars for recent 1-week: {df.index[0].date()} to {df.index[-1].date()}")

# Compute Indicators
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
df = df.dropna()

def simulate_ea(ea_name, strategy_type, sl_pts=2.5, tp_pts=5.0, trail_pts=1.5, partial_tp=True):
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
    opens = df['Open'].values
    ema5 = df['EMA5'].values
    ema10 = df['EMA10'].values
    ema20 = df['EMA20'].values
    ema50 = df['EMA50'].values
    ema200 = df['EMA200'].values
    roll_h = df['High_Roll_2'].values
    roll_l = df['Low_Roll_2'].values
    times = df.index
    
    # On HFM Cent Account (0.01 lot XAUUSDc): $1.00 Gold move = 10 USC profit/loss ($0.10 USD)
    point_val = 10.0
    
    for i in range(1, len(closes)):
        c_price = closes[i]
        h_price = highs[i]
        l_price = lows[i]
        
        # Open Position Management
        if open_pos:
            pos_type = open_pos['type']
            entry = open_pos['entry']
            sl = open_pos['sl']
            tp = open_pos['tp']
            vol = open_pos['vol']
            
            pnl = 0.0
            closed = False
            
            if pos_type == 'BUY':
                if l_price <= sl:
                    pnl = (sl - entry) * point_val * (vol / 0.01)
                    closed = True
                elif h_price >= tp:
                    pnl = (tp - entry) * point_val * (vol / 0.01)
                    closed = True
                elif trail_pts > 0:
                    current_dist = c_price - entry
                    if current_dist >= trail_pts:
                        new_sl = c_price - (trail_pts * 0.5)
                        if new_sl > sl:
                            open_pos['sl'] = new_sl
            else: # SELL
                if h_price >= sl:
                    pnl = (entry - sl) * point_val * (vol / 0.01)
                    closed = True
                elif l_price <= tp:
                    pnl = (entry - tp) * point_val * (vol / 0.01)
                    closed = True
                elif trail_pts > 0:
                    current_dist = entry - c_price
                    if current_dist >= trail_pts:
                        new_sl = c_price + (trail_pts * 0.5)
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
        if not open_pos and balance > 100.0: # Minimum margin check
            buy_sig = False
            sell_sig = False
            
            if strategy_type == 'v3_scalp':
                if ema10[i] > ema200[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif ema10[i] < ema200[i] and c_price < roll_l[i]:
                    sell_sig = True
            elif strategy_type == 'v7_maxprofit':
                if c_price > roll_h[i] and c_price > ema10[i]:
                    buy_sig = True
                elif c_price < roll_l[i] and c_price < ema10[i]:
                    sell_sig = True
            elif strategy_type == 'v10_grandmaster':
                if c_price > ema50[i] and ema10[i] > ema50[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif c_price < ema50[i] and ema10[i] < ema50[i] and c_price < roll_l[i]:
                    sell_sig = True
            elif strategy_type == 'v11_champion':
                if c_price > ema200[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif c_price < ema200[i] and c_price < roll_l[i]:
                    sell_sig = True
            elif strategy_type == 'v8_smc_fibo':
                if c_price > ema20[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif c_price < ema20[i] and c_price < roll_l[i]:
                    sell_sig = True

            if buy_sig:
                sl = c_price - sl_pts
                tp = c_price + tp_pts
                open_pos = {'type': 'BUY', 'entry': c_price, 'sl': sl, 'tp': tp, 'vol': 0.01}
            elif sell_sig:
                sl = c_price + sl_pts
                tp = c_price - tp_pts
                open_pos = {'type': 'SELL', 'entry': c_price, 'sl': sl, 'tp': tp, 'vol': 0.01}

    net_profit = balance - initial_balance
    net_profit_pct = (net_profit / initial_balance) * 100.0
    pf = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
    win_rate = (wins / trades * 100.0) if trades > 0 else 0.0

    return {
        "Name": ea_name,
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
    ("EA v3.0 MultiTF Scalp", "v3_scalp", 2.0, 4.0, 1.2),
    ("EA v7.0 Apex MaxProfit", "v7_maxprofit", 2.5, 6.0, 1.8),
    ("EA v8.0 SMC Fibo Scalper", "v8_smc_fibo", 2.0, 5.0, 1.5),
    ("EA v10.0 Apex Grandmaster", "v10_grandmaster", 2.5, 5.5, 1.5),
    ("EA v11.0 Apex Champion", "v11_champion", 2.2, 5.0, 1.4),
]

results = []
for name, stype, sl, tp, trail in configs:
    results.append(simulate_ea(name, stype, sl, tp, trail))

# Sort results by Net Profit (descending)
results.sort(key=lambda x: x["NetProfitUSC"], reverse=True)

print("\n" + "="*110)
print(f"{'Rank & EA Version':<30} | {'Net Profit (USC)':<18} | {'Profit ($USD)':<13} | {'Return %':<10} | {'Win Rate':<9} | {'PF':<6} | {'Max DD %':<8}")
print("-" * 110)
for idx, r in enumerate(results, 1):
    rank_str = f"#{idx} {r['Name']}"
    print(f"{rank_str:<30} | {r['NetProfitUSC']:<+18.2f} | ${r['ProfitUSD']:<+12.2f} | {r['ReturnPct']:<+9.2f}% | {r['WinRate']:<8.1f}% | {r['PF']:<6.2f} | {r['MaxDD']:<7.2f}%")
print("="*110)

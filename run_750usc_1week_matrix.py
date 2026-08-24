import yfinance as yf
import pandas as pd
import numpy as np

print("==========================================================================")
print("  750 USC ($7.50 USD) 1-WEEK REAL-MARKET BENCHMARK (0.01 CENT LOT)")
print("==========================================================================")

# Download recent intraday Gold data (1-month period, 15m interval)
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="1mo", interval="15m").dropna()

# Filter last 7 trading days
last_date = df_raw.index[-1]
start_7d = last_date - pd.Timedelta(days=7)
df_1wk = df_raw[df_raw.index >= start_7d].copy()

print(f"Loaded {len(df_1wk)} 15-minute bars for recent 1-week: {df_1wk.index[0]} to {df_1wk.index[-1]}")

# Compute Indicators
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

# Simulation Engine for 750 USC ($7.50 USD)
def simulate_750usc_strategy(name, strategy_type, sl_points=2.5, tp_points=5.0, trailing_step=1.5):
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
    atrs = df_1wk['ATR14'].values
    ema10 = df_1wk['EMA10'].values
    ema50 = df_1wk['EMA50'].values
    ema200 = df_1wk['EMA200'].values
    roll_h = df_1wk['High_Roll_2'].values
    roll_l = df_1wk['Low_Roll_2'].values
    times = df_1wk.index
    
    lot = 0.01 # 0.01 Cent Lot
    point_val = 100.0 # 1 USD Gold price move ($1.00) = 100 USC profit/loss for 0.01 lot
    
    for i in range(1, len(closes)):
        c_price = closes[i]
        h_price = highs[i]
        l_price = lows[i]
        o_price = opens[i]
        c_time = times[i]
        
        # Check open position management
        if open_pos:
            pos_type = open_pos['type']
            entry = open_pos['entry']
            sl = open_pos['sl']
            tp = open_pos['tp']
            
            pnl = 0.0
            closed = False
            
            if pos_type == 'BUY':
                # Check SL
                if l_price <= sl:
                    pnl = (sl - entry) * point_val
                    closed = True
                # Check TP
                elif h_price >= tp:
                    pnl = (tp - entry) * point_val
                    closed = True
                # Trailing SL update if enabled
                elif strategy_type in ['v7', 'v10', 'v11']:
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
                elif strategy_type in ['v7', 'v10', 'v11']:
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
                
        # Signal Generation (if no open position)
        if not open_pos and balance > 50.0: # minimum 50 USC to trade 0.01 lot
            buy_sig = False
            sell_sig = False
            
            if strategy_type == 'v3_scalp':
                if ema10[i] > ema200[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif ema10[i] < ema200[i] and c_price < roll_l[i]:
                    sell_sig = True
            elif strategy_type == 'v7':
                if c_price > roll_h[i] and c_price > ema10[i]:
                    buy_sig = True
                elif c_price < roll_l[i] and c_price < ema10[i]:
                    sell_sig = True
            elif strategy_type == 'v10':
                if c_price > ema50[i] and ema10[i] > ema50[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif c_price < ema50[i] and ema10[i] < ema50[i] and c_price < roll_l[i]:
                    sell_sig = True
            elif strategy_type == 'v11':
                if c_price > ema200[i] and c_price > roll_h[i]:
                    buy_sig = True
                elif c_price < ema200[i] and c_price < roll_l[i]:
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

# Run All 4 EA Strategies
results = []
results.append(simulate_750usc_strategy("EA v3.0 MultiTF Scalp", "v3_scalp", sl_points=2.0, tp_points=4.0, trailing_step=1.0))
results.append(simulate_750usc_strategy("EA v7.0 Apex MaxProfit", "v7", sl_points=2.5, tp_points=7.0, trailing_step=1.8))
results.append(simulate_750usc_strategy("EA v10.0 Apex Grandmaster", "v10", sl_points=3.0, tp_points=6.0, trailing_step=2.0))
results.append(simulate_750usc_strategy("EA v11.0 Apex Champion", "v11", sl_points=2.2, tp_points=5.5, trailing_step=1.5))

print("\n" + "="*100)
print(f"{'EA Version':<26} | {'Net Profit (USC)':<18} | {'Profit ($USD)':<13} | {'Return %':<10} | {'Win Rate':<9} | {'PF':<6} | {'Max DD %':<8}")
print("-" * 100)
for r in results:
    print(f"{r['Name']:<26} | {r['NetProfitUSC']:<+18.2f} | ${r['ProfitUSD']:<+12.2f} | {r['ReturnPct']:<+9.2f}% | {r['WinRate']:<8.1f}% | {r['PF']:<6.2f} | {r['MaxDD']:<7.2f}%")
print("="*100)

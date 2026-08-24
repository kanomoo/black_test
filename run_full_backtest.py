import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime

print("Starting Backtest Simulation for XAUUSD Multi-TF Scalping EA v2.0...")

# Fetch Gold data
gold = yf.Ticker("GC=F")
df_h1 = gold.history(period="60d", interval="1h")
df_h4 = gold.history(period="60d", interval="1h").resample('4h').agg({
    'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
}).dropna()
df_m30 = gold.history(period="60d", interval="30m")
df_m5 = gold.history(period="60d", interval="15m") # Using 15m as fine granular proxy

if len(df_h1) == 0 or len(df_m5) == 0:
    print("Failed to download market data for Gold. Generating synthetic market backtest.")
    np.random.seed(42)
    n_bars = 2000
    dates = pd.date_range(end=datetime.now(), periods=n_bars, freq='15min')
    returns = np.random.normal(0.0001, 0.002, n_bars)
    price = 2400.0 * np.exp(np.cumsum(returns))
    df_m5 = pd.DataFrame({
        'Open': price * (1 + np.random.uniform(-0.001, 0.001, n_bars)),
        'High': price * (1 + np.random.uniform(0.0005, 0.003, n_bars)),
        'Low': price * (1 - np.random.uniform(0.0005, 0.003, n_bars)),
        'Close': price,
        'Volume': np.random.randint(100, 1000, n_bars)
    }, index=dates)

print(f"Loaded {len(df_m5)} bars of Gold intraday price data.")

# Parameters
initial_deposit = 10000.0
balance = initial_deposit
equity = initial_deposit
peak_equity = initial_deposit
max_drawdown = 0.0
max_drawdown_pct = 0.0

risk_percent = 15.0 # 15% per trade
sl_buffer = 1.50 # $1.50 (150 points)
lot_step = 0.01

trades = []
open_position = None

# Backtest Loop
for i in range(5, len(df_m5)):
    curr_time = df_m5.index[i]
    curr_bar = df_m5.iloc[i]
    prev_bar = df_m5.iloc[i-1]
    
    # 1. Trading Hours Check (11:00 - 02:00 GMT+7)
    hour = curr_time.hour
    in_hours = (11 <= hour <= 23) or (0 <= hour < 2)
    
    # 2. Check Open Position Update
    if open_position is not None:
        pos = open_position
        pos_type = pos['type']
        entry_price = pos['entry_price']
        sl_price = pos['sl_price']
        tp5_price = pos['tp5_price']
        lot_size = pos['lot_size']
        initial_risk = pos['initial_risk']
        
        high = curr_bar['High']
        low = curr_bar['Low']
        
        closed = False
        exit_price = 0.0
        exit_reason = ""
        
        if pos_type == 'BUY':
            current_profit = high - entry_price
            if low <= sl_price: # Hit SL
                closed = True
                exit_price = sl_price
                exit_reason = 'SL'
            elif high >= tp5_price: # Hit TP5
                closed = True
                exit_price = tp5_price
                exit_reason = 'TP5 (RR 1:15)'
            else: # Check Cascade Trailing SL
                current_rr = (high - entry_price) / initial_risk if initial_risk > 0 else 0
                for level, rr_target in enumerate([2.0, 3.0, 5.0, 10.0]):
                    if current_rr >= rr_target and not pos['tp_closed'][level]:
                        new_sl = entry_price + (high - entry_price) * 0.5
                        if new_sl > pos['sl_price']:
                            pos['sl_price'] = new_sl
                            pos['tp_closed'][level] = True
                            
        elif pos_type == 'SELL':
            current_profit = entry_price - low
            if high >= sl_price: # Hit SL
                closed = True
                exit_price = sl_price
                exit_reason = 'SL'
            elif low <= tp5_price: # Hit TP5
                closed = True
                exit_price = tp5_price
                exit_reason = 'TP5 (RR 1:15)'
            else: # Check Cascade Trailing SL
                current_rr = (entry_price - low) / initial_risk if initial_risk > 0 else 0
                for level, rr_target in enumerate([2.0, 3.0, 5.0, 10.0]):
                    if current_rr >= rr_target and not pos['tp_closed'][level]:
                        new_sl = entry_price - (entry_price - low) * 0.5
                        if new_sl < pos['sl_price']:
                            pos['sl_price'] = new_sl
                            pos['tp_closed'][level] = True
                            
        if closed:
            if pos_type == 'BUY':
                pnl = (exit_price - entry_price) * lot_size * 100 # 100 oz per lot for Gold
            else:
                pnl = (entry_price - exit_price) * lot_size * 100
                
            balance += pnl
            equity = balance
            if equity > peak_equity:
                peak_equity = equity
            dd = peak_equity - equity
            dd_pct = (dd / peak_equity) * 100 if peak_equity > 0 else 0
            if dd_pct > max_drawdown_pct:
                max_drawdown_pct = dd_pct
                max_drawdown = dd
                
            trades.append({
                'entry_time': str(pos['entry_time']),
                'exit_time': str(curr_time),
                'type': pos_type,
                'entry_price': round(entry_price, 2),
                'exit_price': round(exit_price, 2),
                'lot_size': round(lot_size, 2),
                'pnl': round(pnl, 2),
                'balance': round(balance, 2),
                'reason': exit_reason
            })
            open_position = None
            
    # 3. Open New Position
    if open_position is None and in_hours:
        # Check trend confirmation on H1 / M30
        h1_bull = prev_bar['Close'] > prev_bar['Open']
        h1_bear = prev_bar['Close'] < prev_bar['Open']
        
        # M5 confirmation
        m5_bull = curr_bar['Close'] > curr_bar['Open']
        m5_bear = curr_bar['Close'] < curr_bar['Open']
        
        signal = None
        if h1_bull and m5_bull:
            signal = 'BUY'
        elif h1_bear and m5_bear:
            signal = 'SELL'
            
        if signal is not None:
            if signal == 'BUY':
                entry_price = curr_bar['Close']
                sl_price = prev_bar['Low'] - sl_buffer
                risk_dist = entry_price - sl_price
                if risk_dist > 0:
                    tp5_price = entry_price + (risk_dist * 15.0)
                    risk_amount = balance * (risk_percent / 100.0)
                    lot_size = max(0.01, round(risk_amount / (risk_dist * 100), 2))
                    
                    open_position = {
                        'entry_time': curr_time,
                        'type': 'BUY',
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'tp5_price': tp5_price,
                        'initial_risk': risk_dist,
                        'lot_size': lot_size,
                        'tp_closed': [False, False, False, False]
                    }
            elif signal == 'SELL':
                entry_price = curr_bar['Close']
                sl_price = prev_bar['High'] + sl_buffer
                risk_dist = sl_price - entry_price
                if risk_dist > 0:
                    tp5_price = entry_price - (risk_dist * 15.0)
                    risk_amount = balance * (risk_percent / 100.0)
                    lot_size = max(0.01, round(risk_amount / (risk_dist * 100), 2))
                    
                    open_position = {
                        'entry_time': curr_time,
                        'type': 'SELL',
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'tp5_price': tp5_price,
                        'initial_risk': risk_dist,
                        'lot_size': lot_size,
                        'tp_closed': [False, False, False, False]
                    }

# Metrics Calculation
total_trades = len(trades)
wins = [t for t in trades if t['pnl'] > 0]
losses = [t for t in trades if t['pnl'] < 0]
win_count = len(wins)
loss_count = len(losses)
win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

total_profit = sum(t['pnl'] for t in wins)
total_loss = abs(sum(t['pnl'] for t in losses))
net_profit = balance - initial_deposit
profit_factor = (total_profit / total_loss) if total_loss > 0 else (total_profit if total_profit > 0 else 1.0)
roi_pct = (net_profit / initial_deposit) * 100

report = {
    "ea_name": "XAUUSD Multi-TF Scalping EA v2.0",
    "symbol": "XAUUSD (Gold)",
    "period": f"{df_m5.index[0].date()} to {df_m5.index[-1].date()}",
    "initial_deposit": initial_deposit,
    "final_balance": round(balance, 2),
    "net_profit": round(net_profit, 2),
    "roi_percent": round(roi_pct, 2),
    "profit_factor": round(profit_factor, 2),
    "win_rate_percent": round(win_rate, 2),
    "total_trades": total_trades,
    "winning_trades": win_count,
    "losing_trades": loss_count,
    "max_drawdown_amount": round(max_drawdown, 2),
    "max_drawdown_percent": round(max_drawdown_pct, 2),
    "trades": trades[:20] # top 20 trades
}

with open(r"D:\Trade_Gus\backtest_report.json", "w") as f:
    json.dump(report, f, indent=4)

print("\n================ BACKTEST SUMMARY REPORT ================")
print(f" EA Name: {report['ea_name']}")
print(f" Symbol: {report['symbol']}")
print(f" Period: {report['period']}")
print(f" Initial Deposit: ${initial_deposit:,.2f}")
print(f" Final Balance: ${balance:,.2f}")
print(f" Total Net Profit: ${net_profit:,.2f} ({roi_pct:.2f}%)")
print(f" Profit Factor: {profit_factor:.2f}")
print(f" Win Rate: {win_rate:.2f}% ({win_count} Wins / {loss_count} Losses / {total_trades} Total Trades)")
print(f" Max Drawdown: ${max_drawdown:,.2f} ({max_drawdown_pct:.2f}%)")
print("=========================================================\n")

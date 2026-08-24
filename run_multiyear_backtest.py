import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime

print("Starting 2-Year Multi-Year Backtest for XAUUSD EA v2.0...")

gold = yf.Ticker("GC=F")
df = gold.history(period="2y", interval="1h").dropna()

print(f"Loaded {len(df)} 1-hour bars for Gold from {df.index[0].date()} to {df.index[-1].date()} (2 Full Years).")

# Technical Indicators
df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

high_low = df['High'] - df['Low']
high_close = np.abs(df['High'] - df['Close'].shift())
low_close = np.abs(df['Low'] - df['Close'].shift())
ranges = pd.concat([high_low, high_close, low_close], axis=1)
true_range = np.max(ranges, axis=1)
df['ATR14'] = true_range.rolling(14).mean()

df['Prev_High_4'] = df['High'].shift(1).rolling(4).max()
df['Prev_Low_4'] = df['Low'].shift(1).rolling(4).min()

df = df.dropna()

def run_2y_backtest(risk_pct=1.5, atr_mult=1.5, rr_target=2.0):
    initial_deposit = 10000.0
    balance = initial_deposit
    peak_equity = initial_deposit
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    
    trades = []
    open_position = None
    
    for i in range(200, len(df)):
        curr_time = df.index[i]
        curr_bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        
        hour = curr_time.hour
        in_hours = (11 <= hour <= 23) or (0 <= hour < 2)
        
        if open_position is not None:
            pos = open_position
            pos_type = pos['type']
            entry_price = pos['entry_price']
            sl_price = pos['sl_price']
            tp_price = pos['tp_price']
            lot_size = pos['lot_size']
            
            high = curr_bar['High']
            low = curr_bar['Low']
            
            closed = False
            exit_price = 0.0
            exit_reason = ""
            
            if pos_type == 'BUY':
                if low <= sl_price:
                    closed = True
                    exit_price = sl_price
                    exit_reason = 'SL'
                elif high >= tp_price:
                    closed = True
                    exit_price = tp_price
                    exit_reason = f'TP (RR 1:{rr_target})'
                else:
                    risk_dist = pos['initial_risk']
                    if (high - entry_price) >= (risk_dist * 1.5) and pos['sl_price'] < entry_price:
                        pos['sl_price'] = entry_price + (risk_dist * 0.2)
                        
            elif pos_type == 'SELL':
                if high >= sl_price:
                    closed = True
                    exit_price = sl_price
                    exit_reason = 'SL'
                elif low <= tp_price:
                    closed = True
                    exit_price = tp_price
                    exit_reason = f'TP (RR 1:{rr_target})'
                else:
                    risk_dist = pos['initial_risk']
                    if (entry_price - low) >= (risk_dist * 1.5) and pos['sl_price'] > entry_price:
                        pos['sl_price'] = entry_price - (risk_dist * 0.2)
                        
            if closed:
                if pos_type == 'BUY':
                    pnl = (exit_price - entry_price) * lot_size * 100
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
                
        if open_position is None and in_hours:
            ema20 = curr_bar['EMA20']
            ema50 = curr_bar['EMA50']
            ema200 = curr_bar['EMA200']
            close = curr_bar['Close']
            atr = curr_bar['ATR14']
            
            uptrend = (close > ema50) and (ema20 > ema50) and (ema50 > ema200)
            downtrend = (close < ema50) and (ema20 < ema50) and (ema50 < ema200)
            
            buy_breakout = close > prev_bar['Prev_High_4']
            sell_breakout = close < prev_bar['Prev_Low_4']
            
            signal = None
            if uptrend and buy_breakout:
                signal = 'BUY'
            elif downtrend and sell_breakout:
                signal = 'SELL'
                
            if signal is not None and atr > 0:
                entry_price = close
                sl_dist = atr * atr_mult
                
                if signal == 'BUY':
                    sl_price = entry_price - sl_dist
                    tp_price = entry_price + (sl_dist * rr_target)
                else:
                    sl_price = entry_price + sl_dist
                    tp_price = entry_price - (sl_dist * rr_target)
                    
                risk_amount = balance * (risk_pct / 100.0)
                lot_size = max(0.01, round(risk_amount / (sl_dist * 100), 2))
                
                open_position = {
                    'entry_time': curr_time,
                    'type': signal,
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'initial_risk': sl_dist,
                    'lot_size': lot_size
                }

    total_trades = len(trades)
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    
    total_profit = sum(t['pnl'] for t in wins)
    total_loss = abs(sum(t['pnl'] for t in losses))
    pf = (total_profit / total_loss) if total_loss > 0 else 1.0
    net_profit = balance - initial_deposit
    roi = (net_profit / initial_deposit) * 100
    
    return {
        "period": f"{df.index[0].date()} to {df.index[-1].date()} (2 Years)",
        "initial_deposit": initial_deposit,
        "final_balance": round(balance, 2),
        "net_profit": round(net_profit, 2),
        "roi_percent": round(roi, 2),
        "profit_factor": round(pf, 2),
        "win_rate_percent": round(win_rate, 2),
        "total_trades": total_trades,
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "max_drawdown_amount": round(max_drawdown, 2),
        "max_drawdown_percent": round(max_drawdown_pct, 2)
    }

res_2y = run_2y_backtest(risk_pct=1.5, atr_mult=1.5, rr_target=2.0)

print("\n================ 2-YEAR MULTI-YEAR BACKTEST REPORT ================")
print(f" Period: {res_2y['period']}")
print(f" Initial Deposit: ${res_2y['initial_deposit']:,.2f}")
print(f" Final Balance: ${res_2y['final_balance']:,.2f}")
print(f" Net Profit: ${res_2y['net_profit']:,.2f} ({res_2y['roi_percent']}%)")
print(f" Profit Factor: {res_2y['profit_factor']}")
print(f" Win Rate: {res_2y['win_rate_percent']}% ({res_2y['winning_trades']} Wins / {res_2y['losing_trades']} Losses / {res_2y['total_trades']} Total Trades)")
print(f" Max Drawdown: ${res_2y['max_drawdown_amount']:,.2f} ({res_2y['max_drawdown_percent']}%)")
print("===================================================================\n")

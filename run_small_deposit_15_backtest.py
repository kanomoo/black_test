import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime

print("==========================================================================")
print("  $15 INITIAL DEPOSIT BACKTEST - XAUUSD MAX PROFIT CONFIGURATION")
print("==========================================================================")

# Download 2 years of Gold 1-hour intraday data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="2y", interval="1h").dropna()

print(f"Loaded {len(df_raw)} 1-hour bars for Gold from {df_raw.index[0].date()} to {df_raw.index[-1].date()}.")

df = df_raw.copy()
df['EMA10'] = df['Close'].ewm(span=10, adjust=False).mean()
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

def run_15usd_backtest(risk_pct=3.0, atr_mult=1.5, rr_target=3.0):
    initial_deposit = 15.0 # $15 Initial Deposit
    balance = initial_deposit
    peak_equity = initial_deposit
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    
    trades = []
    open_position = None
    
    closes = df['Close'].values
    highs = df['High'].values
    lows = df['Low'].values
    atrs = df['ATR14'].values
    ema10 = df['EMA10'].values
    ema200 = df['EMA200'].values
    roll_h = df['High_Roll_2'].values
    roll_l = df['Low_Roll_2'].values
    times = df.index
    
    for i in range(1, len(df)):
        curr_time = times[i]
        hour = curr_time.hour
        in_hours = (11 <= hour <= 23) or (0 <= hour < 2)
        
        close = closes[i]
        high = highs[i]
        low = lows[i]
        atr = atrs[i]
        
        # Check Stop Out / Margin Call
        if balance <= 1.0: # Account Stop Out
            print(f"Margin Call / Stop Out reached at bar {i} ({curr_time.date()}). Balance: ${balance:.2f}")
            break
            
        if open_position is not None:
            pos = open_position
            pos_type = pos['type']
            entry_price = pos['entry_price']
            sl_price = pos['sl_price']
            tp_price = pos['tp_price']
            lot_size = pos['lot_size']
            initial_risk = pos['initial_risk']
            
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
                else: # Trailing Stop to BreakEven at 1.5 RR
                    if (high - entry_price) >= (initial_risk * 1.5) and pos['sl_price'] < entry_price:
                        pos['sl_price'] = entry_price + (initial_risk * 0.2)
                        
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
                    if (entry_price - low) >= (initial_risk * 1.5) and pos['sl_price'] > entry_price:
                        pos['sl_price'] = entry_price - (initial_risk * 0.2)
                        
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
            e10 = ema10[i]
            e200 = ema200[i]
            ph = roll_h[i]
            pl = roll_l[i]
            
            uptrend = (close > e200) and (e10 > e200)
            downtrend = (close < e200) and (e10 < e200)
            
            buy_sig = uptrend and (close > ph)
            sell_sig = downtrend and (close < pl)
            
            signal = None
            if buy_sig:
                signal = 'BUY'
            elif sell_sig:
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
                # Minimum lot size on MT5 is 0.01 lot
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
        "max_drawdown_percent": round(max_drawdown_pct, 2),
        "trades_sample": trades[:10]
    }

report_15 = run_15usd_backtest(risk_pct=3.0, atr_mult=1.5, rr_target=3.0)

print("\n================ $15 INITIAL DEPOSIT BACKTEST REPORT ================")
print(f" Period: {report_15['period']}")
print(f" Initial Deposit: ${report_15['initial_deposit']:.2f}")
print(f" Final Balance: ${report_15['final_balance']:,.2f}")
print(f" Net Profit: ${report_15['net_profit']:,.2f} ({report_15['roi_percent']}%)")
print(f" Profit Factor: {report_15['profit_factor']}")
print(f" Win Rate: {report_15['win_rate_percent']}% ({report_15['winning_trades']} Wins / {report_15['losing_trades']} Losses / {report_15['total_trades']} Total Trades)")
print(f" Max Drawdown: ${report_15['max_drawdown_amount']:,.2f} ({report_15['max_drawdown_percent']}%)")
print("======================================================================\n")

with open(r"D:\Trade_Gus\report_15usd.json", "w") as f:
    json.dump(report_15, f, indent=4)

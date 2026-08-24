import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime

print("Starting Parameter Optimization Backtest for XAUUSD EA v2.0...")

gold = yf.Ticker("GC=F")
df_m5 = gold.history(period="60d", interval="15m")

if len(df_m5) == 0:
    print("No market data fetched.")
    quit()

def run_simulation(risk_pct, sl_buf):
    initial_deposit = 10000.0
    balance = initial_deposit
    peak_equity = initial_deposit
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    
    trades = []
    open_position = None
    
    for i in range(5, len(df_m5)):
        curr_time = df_m5.index[i]
        curr_bar = df_m5.iloc[i]
        prev_bar = df_m5.iloc[i-1]
        
        hour = curr_time.hour
        in_hours = (11 <= hour <= 23) or (0 <= hour < 2)
        
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
                if low <= sl_price:
                    closed = True
                    exit_price = sl_price
                    exit_reason = 'SL'
                elif high >= tp5_price:
                    closed = True
                    exit_price = tp5_price
                    exit_reason = 'TP5 (RR 1:15)'
                else:
                    current_rr = (high - entry_price) / initial_risk if initial_risk > 0 else 0
                    for level, rr_target in enumerate([2.0, 3.0, 5.0, 10.0]):
                        if current_rr >= rr_target and not pos['tp_closed'][level]:
                            new_sl = entry_price + (high - entry_price) * 0.5
                            if new_sl > pos['sl_price']:
                                pos['sl_price'] = new_sl
                                pos['tp_closed'][level] = True
                                
            elif pos_type == 'SELL':
                if high >= sl_price:
                    closed = True
                    exit_price = sl_price
                    exit_reason = 'SL'
                elif low <= tp5_price:
                    closed = True
                    exit_price = tp5_price
                    exit_reason = 'TP5 (RR 1:15)'
                else:
                    current_rr = (entry_price - low) / initial_risk if initial_risk > 0 else 0
                    for level, rr_target in enumerate([2.0, 3.0, 5.0, 10.0]):
                        if current_rr >= rr_target and not pos['tp_closed'][level]:
                            new_sl = entry_price - (entry_price - low) * 0.5
                            if new_sl < pos['sl_price']:
                                pos['sl_price'] = new_sl
                                pos['tp_closed'][level] = True
                                
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
                    
                trades.append(pnl)
                open_position = None
                
        if open_position is None and in_hours:
            h1_bull = prev_bar['Close'] > prev_bar['Open']
            h1_bear = prev_bar['Close'] < prev_bar['Open']
            
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
                    sl_price = prev_bar['Low'] - sl_buf
                    risk_dist = entry_price - sl_price
                    if risk_dist > 0:
                        tp5_price = entry_price + (risk_dist * 15.0)
                        risk_amount = balance * (risk_pct / 100.0)
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
                    sl_price = prev_bar['High'] + sl_buf
                    risk_dist = sl_price - entry_price
                    if risk_dist > 0:
                        tp5_price = entry_price - (risk_dist * 15.0)
                        risk_amount = balance * (risk_pct / 100.0)
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

    total_trades = len(trades)
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    total_profit = sum(wins)
    total_loss = abs(sum(losses))
    pf = (total_profit / total_loss) if total_loss > 0 else 1.0
    net_profit = balance - initial_deposit
    roi = (net_profit / initial_deposit) * 100
    
    return {
        'risk_pct': risk_pct,
        'sl_buf': sl_buf,
        'final_balance': round(balance, 2),
        'net_profit': round(net_profit, 2),
        'roi': round(roi, 2),
        'pf': round(pf, 2),
        'win_rate': round(win_rate, 2),
        'total_trades': total_trades,
        'max_dd_pct': round(max_drawdown_pct, 2)
    }

results = []
for r in [15.0, 5.0, 2.0, 1.0]:
    for b in [1.50, 2.50, 3.50]:
        res = run_simulation(r, b)
        results.append(res)

df_res = pd.DataFrame(results)
print("\n" + df_res.to_string(index=False))

with open(r"D:\Trade_Gus\optimization_results.json", "w") as f:
    json.dump(results, f, indent=4)

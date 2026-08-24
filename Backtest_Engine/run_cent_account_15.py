import yfinance as yf
import pandas as pd
import numpy as np
import json

print("==========================================================================")
print("  $15 CENT ACCOUNT REALISTIC SIMULATION (1,500 CENT BALANCE)")
print("==========================================================================")

gold = yf.Ticker("GC=F")
df_raw = gold.history(period="2y", interval="1h").dropna()

df = df_raw.copy()
df['EMA10'] = df['Close'].ewm(span=10, adjust=False).mean()
df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

high_low = df['High'] - df['Low']
high_close = np.abs(df['High'] - df['Close'].shift())
low_close = np.abs(df['Low'] - df['Close'].shift())
ranges = pd.concat([high_low, high_close, low_close], axis=1)
true_range = np.max(ranges, axis=1)
df['ATR14'] = true_range.rolling(14).mean()

df['High_Roll_2'] = df['High'].shift(1).rolling(2).max()
df['Low_Roll_2'] = df['Low'].shift(1).rolling(2).min()

df = df.dropna()

def run_cent_sim(initial_usd=15.0, risk_pct=2.5, atr_mult=1.5, rr_target=2.5):
    initial_cent = initial_usd * 100.0 # $15 USD = 1,500 Cent Balance
    balance_cent = initial_cent
    peak_equity = initial_cent
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
        
        if balance_cent <= 50.0:
            print(f"Stop Out reached at {curr_time.date()}")
            break
            
        if open_position is not None:
            pos = open_position
            pos_type = pos['type']
            entry_price = pos['entry_price']
            sl_price = pos['sl_price']
            tp_price = pos['tp_price']
            cent_lot = pos['lot_size']
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
                else:
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
                # 1 Cent Lot = 1 oz Gold. 0.01 Cent Lot = 0.01 oz Gold -> $1.00 move = 1 Cent PnL
                if pos_type == 'BUY':
                    pnl_cent = (exit_price - entry_price) * cent_lot * 1.0
                else:
                    pnl_cent = (entry_price - exit_price) * cent_lot * 1.0
                    
                balance_cent += pnl_cent
                
                if balance_cent > peak_equity:
                    peak_equity = balance_cent
                dd = peak_equity - balance_cent
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
                    'cent_lot': round(cent_lot, 2),
                    'pnl_cent': round(pnl_cent, 2),
                    'pnl_usd': round(pnl_cent / 100.0, 2),
                    'balance_cent': round(balance_cent, 2),
                    'balance_usd': round(balance_cent / 100.0, 2),
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
                    
                risk_amt_cent = balance_cent * (risk_pct / 100.0)
                cent_lot = max(0.01, round(risk_amt_cent / (sl_dist * 1.0), 2))
                
                open_position = {
                    'entry_time': curr_time,
                    'type': signal,
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'initial_risk': sl_dist,
                    'lot_size': cent_lot
                }

    total_trades = len(trades)
    wins = [t for t in trades if t['pnl_cent'] > 0]
    losses = [t for t in trades if t['pnl_cent'] < 0]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    
    total_profit = sum(t['pnl_cent'] for t in wins)
    total_loss = abs(sum(t['pnl_cent'] for t in losses))
    pf = (total_profit / total_loss) if total_loss > 0 else 1.0
    
    final_usd = balance_cent / 100.0
    net_profit_usd = final_usd - initial_usd
    roi = (net_profit_usd / initial_usd) * 100
    
    return {
        "period": f"{df.index[0].date()} to {df.index[-1].date()} (2 Years)",
        "initial_usd": initial_usd,
        "initial_cent": initial_cent,
        "final_usd": round(final_usd, 2),
        "final_cent": round(balance_cent, 2),
        "net_profit_usd": round(net_profit_usd, 2),
        "roi_percent": round(roi, 2),
        "profit_factor": round(pf, 2),
        "win_rate_percent": round(win_rate, 2),
        "total_trades": total_trades,
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "max_drawdown_percent": round(max_drawdown_pct, 2)
    }

res_15_cent = run_cent_sim(initial_usd=15.0, risk_pct=2.5, atr_mult=1.5, rr_target=2.5)

print("\n================ $15 CENT ACCOUNT REALISTIC BACKTEST REPORT ================")
print(f" Period: {res_15_cent['period']}")
print(f" Initial Deposit: ${res_15_cent['initial_usd']:.2f} USD ({res_15_cent['initial_cent']:,.0f} Cent Balance)")
print(f" Final Balance: ${res_15_cent['final_usd']:,.2f} USD ({res_15_cent['final_cent']:,.0f} Cent Balance)")
print(f" Net Profit: ${res_15_cent['net_profit_usd']:,.2f} USD (+{res_15_cent['roi_percent']}%)")
print(f" Profit Factor: {res_15_cent['profit_factor']}")
print(f" Win Rate: {res_15_cent['win_rate_percent']}% ({res_15_cent['winning_trades']} Wins / {res_15_cent['losing_trades']} Losses / {res_15_cent['total_trades']} Total Trades)")
print(f" Max Drawdown: {res_15_cent['max_drawdown_percent']}%")
print("===========================================================================\n")

with open(r"D:\Trade_Gus\report_15usd_cent.json", "w") as f:
    json.dump(res_15_cent, f, indent=4)

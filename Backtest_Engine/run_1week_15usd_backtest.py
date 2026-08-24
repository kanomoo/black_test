import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

print("==========================================================================")
print("  1-WEEK BACKTEST SIMULATION ($15 USD DEPOSIT - BEST EA CONFIG)")
print("==========================================================================")

# Download 1-minute / 15-minute intraday data for Gold over recent period
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="1mo", interval="15m").dropna()

print(f"Loaded {len(df_raw)} 15-minute bars for Gold from {df_raw.index[0].date()} to {df_raw.index[-1].date()}.")

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

def run_1week_sim(df_sub, is_cent_account=True, initial_usd=15.0, risk_pct=2.5, atr_mult=1.5, rr_target=2.5):
    if is_cent_account:
        initial_balance = initial_usd * 100.0 # 1,500 Cent Balance
    else:
        initial_balance = initial_usd # $15.00 Standard USD
        
    balance = initial_balance
    peak_equity = initial_balance
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    
    trades = []
    open_position = None
    
    closes = df_sub['Close'].values
    highs = df_sub['High'].values
    lows = df_sub['Low'].values
    atrs = df_sub['ATR14'].values
    ema10 = df_sub['EMA10'].values
    ema200 = df_sub['EMA200'].values
    roll_h = df_sub['High_Roll_2'].values
    roll_l = df_sub['Low_Roll_2'].values
    times = df_sub.index
    
    for i in range(1, len(df_sub)):
        curr_time = times[i]
        hour = curr_time.hour
        in_hours = (11 <= hour <= 23) or (0 <= hour < 2)
        
        close = closes[i]
        high = highs[i]
        low = lows[i]
        atr = atrs[i]
        
        if balance <= 1.0: # Stop Out
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
                if is_cent_account:
                    # 0.01 Cent Lot = 0.01 oz Gold -> $1.00 move = 1 Cent PnL
                    pnl_units = (exit_price - entry_price) * lot_size * 1.0 if pos_type == 'BUY' else (entry_price - exit_price) * lot_size * 1.0
                else:
                    # Standard Lot: 0.01 Standard Lot = 1 oz Gold -> $1.00 move = $1.00 PnL
                    pnl_units = (exit_price - entry_price) * lot_size * 100.0 if pos_type == 'BUY' else (entry_price - exit_price) * lot_size * 100.0
                    
                balance += pnl_units
                if balance > peak_equity:
                    peak_equity = balance
                dd = peak_equity - balance
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
                    'pnl': round(pnl_units, 2),
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
                    
                if is_cent_account:
                    # Cent Account: risk in Cent
                    risk_amt = balance * (risk_pct / 100.0)
                    lot_size = max(0.01, round(risk_amt / (sl_dist * 1.0), 2))
                else:
                    # Standard Account: risk in USD
                    risk_amt = balance * (risk_pct / 100.0)
                    lot_size = max(0.01, round(risk_amt / (sl_dist * 100.0), 2))
                    
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
    
    if is_cent_account:
        final_usd = balance / 100.0
        net_profit_usd = final_usd - initial_usd
    else:
        final_usd = balance
        net_profit_usd = final_usd - initial_usd
        
    roi = (net_profit_usd / initial_usd) * 100
    
    return {
        "is_cent": is_cent_account,
        "period": f"{df_sub.index[0].date()} to {df_sub.index[-1].date()}",
        "initial_usd": initial_usd,
        "final_usd": round(final_usd, 2),
        "net_profit_usd": round(net_profit_usd, 2),
        "roi_percent": round(roi, 2),
        "profit_factor": round(pf, 2),
        "win_rate_percent": round(win_rate, 2),
        "total_trades": total_trades,
        "winning_trades": win_count,
        "losing_trades": loss_count,
        "max_drawdown_percent": round(max_drawdown_pct, 2),
        "trades": trades
    }

# Run 1-week test on recent 7 days
end_date = df.index[-1]
start_1w = end_date - timedelta(days=7)
df_1w_recent = df[df.index >= start_1w]

res_1w_cent = run_1week_sim(df_1w_recent, is_cent_account=True, initial_usd=15.0)
res_1w_std = run_1week_sim(df_1w_recent, is_cent_account=False, initial_usd=15.0)

# Run 4 individual 1-week backtests over the past 4 weeks
week_results = []
for w in range(4):
    w_end = end_date - timedelta(days=w*7)
    w_start = w_end - timedelta(days=7)
    df_w = df[(df.index >= w_start) & (df.index < w_end)]
    if len(df_w) > 50:
        r_cent = run_1week_sim(df_w, is_cent_account=True, initial_usd=15.0)
        r_cent['week_label'] = f"Week {4-w} ({w_start.date()} to {w_end.date()})"
        week_results.append(r_cent)

print("\n================ 1-WEEK BACKTEST REPORT ($15 USD) ================")
print(f" Recent 1-Week Period: {res_1w_cent['period']}")
print(f" Initial Deposit: ${res_1w_cent['initial_usd']:.2f} USD")
print(f" Cent Account Final Balance: ${res_1w_cent['final_usd']:.2f} USD (Net Profit: ${res_1w_cent['net_profit_usd']:.2f} / ROI: {res_1w_cent['roi_percent']}%)")
print(f" Cent Account Win Rate: {res_1w_cent['win_rate_percent']}% ({res_1w_cent['winning_trades']} Wins / {res_1w_cent['losing_trades']} Losses / {res_1w_cent['total_trades']} Trades)")
print(f" Cent Account Profit Factor: {res_1w_cent['profit_factor']}")
print(f" Cent Account Max Drawdown: {res_1w_cent['max_drawdown_percent']}%")
print("===================================================================\n")

full_report = {
    "recent_1w_cent": res_1w_cent,
    "recent_1w_std": res_1w_std,
    "past_4_weeks": week_results
}

with open(r"D:\Trade_Gus\report_1week_15usd.json", "w") as f:
    json.dump(full_report, f, indent=4)

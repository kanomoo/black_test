import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

print("==========================================================================")
print("  EA v3 SCALP EDITION - 1-WEEK BACKTEST ($15 USD / 1,500 CENT BALANCE)")
print("==========================================================================")

# Download recent intraday 15m Gold data
gold = yf.Ticker("GC=F")
df_raw = gold.history(period="1mo", interval="15m").dropna()

print(f"Loaded {len(df_raw)} 15-minute bars for Gold from {df_raw.index[0].date()} to {df_raw.index[-1].date()}.")

df = df_raw.copy()
df['EMA5'] = df['Close'].ewm(span=5, adjust=False).mean()
df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

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

def run_scalp_1w(df_sub, initial_usd=15.0, risk_pct=2.5, rr1=1.5, rr2=3.0, rr3=5.0):
    initial_cent = initial_usd * 100.0 # 1,500 Cents
    balance_cent = initial_cent
    peak_equity = initial_cent
    max_dd_pct = 0.0
    
    trades = []
    open_pos = None
    
    closes = df_sub['Close'].values
    highs = df_sub['High'].values
    lows = df_sub['Low'].values
    opens = df_sub['Open'].values
    atrs = df_sub['ATR14'].values
    ema5 = df_sub['EMA5'].values
    ema20 = df_sub['EMA20'].values
    ema50 = df_sub['EMA50'].values
    roll_h = df_sub['High_Roll_2'].values
    roll_l = df_sub['Low_Roll_2'].values
    times = df_sub.index
    hours = df_sub.index.hour
    
    for i in range(1, len(df_sub)):
        hr = hours[i]
        in_hours = (11 <= hr < 16) or (20 <= hr <= 23) or (0 <= hr < 2)
        c, h, l, o, a = closes[i], highs[i], lows[i], opens[i], atrs[i]
        curr_time = times[i]
        
        if balance_cent <= 10.0: break
        
        if open_pos is not None:
            pos = open_pos
            p_type = pos['type']
            entry = pos['entry_price']
            sl = pos['sl_price']
            tp = pos['tp_price']
            cent_lot = pos['lot_size']
            initial_risk = pos['initial_risk']
            tp1_done = pos['tp1_done']
            tp2_done = pos['tp2_done']
            
            closed = False
            exit_p = 0.0
            
            if p_type == 1: # BUY
                if l <= sl: closed = True; exit_p = sl
                elif h >= tp: closed = True; exit_p = tp
                else:
                    if (h - entry) >= (initial_risk * rr1) and not tp1_done:
                        pos['tp1_done'] = True
                        pos['sl_price'] = entry + (initial_risk * 0.2)
                        pnl_cent = (initial_risk * rr1) * (cent_lot * 0.3) * 1.0
                        balance_cent += pnl_cent
                        pos['lot_size'] = cent_lot * 0.7
                    elif (h - entry) >= (initial_risk * rr2) and not tp2_done:
                        pos['tp2_done'] = True
                        pos['sl_price'] = entry + (initial_risk * 1.0)
                        pnl_cent = (initial_risk * rr2) * (cent_lot * 0.4) * 1.0
                        balance_cent += pnl_cent
                        pos['lot_size'] = cent_lot * 0.3
            else: # SELL
                if h >= sl: closed = True; exit_p = sl
                elif l <= tp: closed = True; exit_p = tp
                else:
                    if (entry - l) >= (initial_risk * rr1) and not tp1_done:
                        pos['tp1_done'] = True
                        pos['sl_price'] = entry - (initial_risk * 0.2)
                        pnl_cent = (initial_risk * rr1) * (cent_lot * 0.3) * 1.0
                        balance_cent += pnl_cent
                        pos['lot_size'] = cent_lot * 0.7
                    elif (entry - l) >= (initial_risk * rr2) and not tp2_done:
                        pos['tp2_done'] = True
                        pos['sl_price'] = entry - (initial_risk * 1.0)
                        pnl_cent = (initial_risk * rr2) * (cent_lot * 0.4) * 1.0
                        balance_cent += pnl_cent
                        pos['lot_size'] = cent_lot * 0.3
                        
            if closed:
                rem_pnl = (exit_p - entry) * pos['lot_size'] * 1.0 if p_type == 1 else (entry - exit_p) * pos['lot_size'] * 1.0
                balance_cent += rem_pnl
                if balance_cent > peak_equity: peak_equity = balance_cent
                dd = ((peak_equity - balance_cent) / peak_equity) * 100 if peak_equity > 0 else 0
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(rem_pnl)
                open_pos = None
                
        if open_pos is None and in_hours:
            up = (c > ema50[i]) and (ema5[i] > ema20[i])
            down = (c < ema50[i]) and (ema5[i] < ema20[i])
            buy_sig = up and (c > o) and (c > roll_h[i])
            sell_sig = down and (c < o) and (c < roll_l[i])
            sig = 1 if buy_sig else (-1 if sell_sig else 0)
            
            if sig != 0 and a > 0:
                entry = c
                sl_dist = a * 1.0
                sl = (entry - sl_dist) if sig == 1 else (entry + sl_dist)
                tp = (entry + sl_dist * rr3) if sig == 1 else (entry - sl_dist * rr3)
                risk_cent = balance_cent * (risk_pct / 100.0)
                cent_lot = max(0.01, round(risk_cent / (sl_dist * 1.0), 2))
                open_pos = {
                    'type': sig,
                    'entry_price': entry,
                    'sl_price': sl,
                    'tp_price': tp,
                    'lot_size': cent_lot,
                    'initial_risk': sl_dist,
                    'tp1_done': False,
                    'tp2_done': False
                }

    total_trades = len(trades)
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p < 0]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    total_profit = sum(wins)
    total_loss = abs(sum(losses))
    pf = (total_profit / total_loss) if total_loss > 0 else 1.0
    
    final_usd = balance_cent / 100.0
    net_profit_usd = final_usd - initial_usd
    roi = (net_profit_usd / initial_usd) * 100
    
    return {
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
        "max_drawdown_percent": round(max_dd_pct, 2)
    }

# 1-Week Recent Test
end_date = df.index[-1]
start_1w = end_date - timedelta(days=7)
df_1w_recent = df[df.index >= start_1w]

res_scalp_1w = run_scalp_1w(df_1w_recent, initial_usd=15.0, risk_pct=2.5)

print("\n================ EA v3 SCALP EDITION: 1-WEEK $15 BACKTEST ================")
print(f" Period: {res_scalp_1w['period']}")
print(f" Initial Deposit: ${res_scalp_1w['initial_usd']:.2f} USD (1,500 Cents)")
print(f" Final Balance: ${res_scalp_1w['final_usd']:.2f} USD ({res_scalp_1w['final_usd']*100:.0f} Cents)")
print(f" Net Profit: ${res_scalp_1w['net_profit_usd']:.2f} USD (+{res_scalp_1w['roi_percent']}%)")
print(f" Profit Factor: {res_scalp_1w['profit_factor']}")
print(f" Win Rate: {res_scalp_1w['win_rate_percent']}% ({res_scalp_1w['winning_trades']} Wins / {res_scalp_1w['losing_trades']} Losses / {res_scalp_1w['total_trades']} Trades)")
print(f" Max Drawdown: {res_scalp_1w['max_drawdown_percent']}%")
print("=========================================================================\n")

with open(r"D:\Trade_Gus\Results_Data\v3_scalp_1week_15usd.json", "w") as f:
    json.dump(res_scalp_1w, f, indent=4)

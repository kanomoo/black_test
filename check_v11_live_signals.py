import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd

mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
if not mt5.initialize(path=mt5_path):
    print("MT5 initialize failed:", mt5.last_error())
    quit()

symbol = "XAUUSDc"
mt5.symbol_select(symbol, True)

print("==========================================================================")
print(f"  REAL-TIME MARKET ANALYSIS FOR EA V11 (XAUUSDc / {datetime.now()})  ")
print("==========================================================================")

# 1. H1 Trend Analysis
h1_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 150)
if h1_rates is not None and len(h1_rates) > 100:
    df_h1 = pd.DataFrame(h1_rates)
    df_h1['ema20'] = df_h1['close'].ewm(span=20, adjust=False).mean()
    df_h1['ema50'] = df_h1['close'].ewm(span=50, adjust=False).mean()
    df_h1['ema100'] = df_h1['close'].ewm(span=100, adjust=False).mean()
    
    last_h1 = df_h1.iloc[-2] # bar 1
    close_h1 = last_h1['close']
    e20, e50, e100 = last_h1['ema20'], last_h1['ema50'], last_h1['ema100']
    
    h1_trend = "SIDEWAY / NO TREND (Wait)"
    if close_h1 > e100 and e20 > e50 and e50 > e100:
        h1_trend = "STRONG BULLISH UPTREND (BUY Side Allowed)"
    elif close_h1 < e100 and e20 < e50 and e50 < e100:
        h1_trend = "STRONG BEARISH DOWNTREND (SELL Side Allowed)"
        
    print(f"H1 Trend Status  : {h1_trend}")
    print(f"H1 Close Price   : {close_h1:.2f} | EMA20: {e20:.2f} | EMA50: {e50:.2f} | EMA100: {e100:.2f}")

# 2. M5 Signal Analysis
m5_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)
if m5_rates is not None and len(m5_rates) > 20:
    df_m5 = pd.DataFrame(m5_rates)
    
    # RSI 14
    delta = df_m5['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df_m5['rsi'] = 100 - (100 / (1 + rs))
    
    bar1 = df_m5.iloc[-2]
    close1, open1 = bar1['close'], bar1['open']
    rsi1 = bar1['rsi']
    
    # Donchian 15
    highest_h = df_m5['high'].iloc[-17:-2].max()
    lowest_l  = df_m5['low'].iloc[-17:-2].min()
    
    print("\nM5 Real-Time Signal Status:")
    print(f" - Last M5 Candle : Open={open1:.2f}, Close={close1:.2f} ({'Green/Bullish' if close1>open1 else 'Red/Bearish'})")
    print(f" - M5 RSI(14)     : {rsi1:.2f} (BUY range: 54-74, SELL range: 26-46)")
    print(f" - Donchian 15    : Highest High = {highest_h:.2f} | Lowest Low = {lowest_l:.2f}")
    
    print("\nTrigger Check:")
    print(f" - BUY Trigger    : Breakout > {highest_h:.2f}? {'YES' if close1>highest_h else 'NO'} | RSI in 54-74? {'YES' if 54<rsi1<74 else 'NO'}")
    print(f" - SELL Trigger   : Breakout < {lowest_l:.2f}? {'YES' if close1<lowest_l else 'NO'} | RSI in 26-46? {'YES' if 26<rsi1<46 else 'NO'}")

mt5.shutdown()

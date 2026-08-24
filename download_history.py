import MetaTrader5 as mt5
from datetime import datetime, timedelta
import os

mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
if not mt5.initialize(path=mt5_path):
    print("initialize() failed, error code =", mt5.last_error())
    quit()

print("MT5 initialized successfully!")
term_info = mt5.terminal_info()
if term_info:
    print(f"Connected to: {term_info.name}, Path: {term_info.path}")

symbol = "XAUUSD"
if not mt5.symbol_select(symbol, True):
    print(f"Failed to select symbol {symbol}")

timeframes = {
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4
}

utc_to = datetime.now()
utc_from = utc_to - timedelta(days=90)

for name, tf in timeframes.items():
    rates = mt5.copy_rates_range(symbol, tf, utc_from, utc_to)
    if rates is not None and len(rates) > 0:
        print(f"Downloaded {len(rates)} bars for {symbol} ({name}) from {utc_from.date()} to {utc_to.date()}")
    else:
        print(f"Failed to download bars for {symbol} ({name}), error: {mt5.last_error()}")

mt5.shutdown()

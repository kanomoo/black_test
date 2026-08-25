import MetaTrader5 as mt5
from datetime import datetime

mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
if not mt5.initialize(path=mt5_path):
    print("MT5 initialize failed:", mt5.last_error())
    quit()

symbol = "XAUUSDc"
mt5.symbol_select(symbol, True)

print("==========================================================================")
print(f"  CHECKING MAXIMUM HISTORICAL DATA AVAILABLE FOR {symbol} IN MT5  ")
print("==========================================================================")

for tf_name, tf in [("M5", mt5.TIMEFRAME_M5), ("M15", mt5.TIMEFRAME_M15), ("H1", mt5.TIMEFRAME_H1), ("H4", mt5.TIMEFRAME_H4)]:
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 500000)
    if rates is not None and len(rates) > 0:
        first_time = datetime.fromtimestamp(rates[0][0])
        last_time = datetime.fromtimestamp(rates[-1][0])
        total_bars = len(rates)
        print(f"Timeframe {tf_name:<5}: {total_bars:>7} bars | Oldest: {first_time} | Newest: {last_time}")
    else:
        print(f"Timeframe {tf_name:<5}: No data")

mt5.shutdown()

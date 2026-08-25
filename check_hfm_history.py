import MetaTrader5 as mt5
from datetime import datetime

mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
if not mt5.initialize(path=mt5_path):
    print("initialize() failed, error code =", mt5.last_error())
    quit()

symbol = "XAUUSDc"
mt5.symbol_select(symbol, True)

years = [2024, 2025, 2026]
for y in years:
    utc_from = datetime(y, 1, 1)
    utc_to = datetime(y, 12, 31) if y < 2026 else datetime.now()
    rates_m5 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, utc_from, utc_to)
    rates_h1 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, utc_from, utc_to)
    print(f"Year {y}: M5 bars = {len(rates_m5) if rates_m5 is not None else 0}, H1 bars = {len(rates_h1) if rates_h1 is not None else 0}")

mt5.shutdown()

import MetaTrader5 as mt5
import json

mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
if not mt5.initialize(path=mt5_path):
    print("initialize() failed, error code =", mt5.last_error())
    quit()

acc_info = mt5.account_info()
if acc_info is not None:
    data = acc_info._asdict()
    print("ACCOUNT_INFO_SUCCESS")
    print(json.dumps(data, indent=4))
else:
    print("Failed to get account info:", mt5.last_error())

mt5.shutdown()

import subprocess
import time
import sys
import MetaTrader5 as mt5

print("1. Terminating any old MT5 instances...")
subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1.5)

print("2. Launching MetaTrader 5 GUI...")
mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
ini_path = r"D:\Trade_Gus\startup.ini"

# Launch MT5 GUI with config ini
subprocess.run(f'cmd.exe /c start "" "{mt5_path}" /config:"{ini_path}"', shell=True)

print("3. Waiting for MT5 GUI to open...")
time.sleep(4)

print("4. Sending login credentials to MT5 terminal...")
if mt5.initialize(path=mt5_path):
    login_success = mt5.login(205081617, password="Dew717254.", server="HFMarketsGlobal-Live15")
    if login_success:
        acc = mt5.account_info()
        print(f"SUCCESS! Logged into Account: {acc.login} ({acc.name})")
        print(f"Server: {acc.server}")
        print(f"Balance: {acc.balance} {acc.currency}")
    else:
        print(f"ERROR: mt5.login failed with error code {mt5.last_error()}")
    mt5.shutdown()
else:
    print(f"ERROR: mt5.initialize failed with error code {mt5.last_error()}")

import os
import subprocess
import time
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
ini_path = r"D:\Trade_Gus\Backtest_Engine\native_mt5_run.ini"
report_path = r"D:\Trade_Gus\Reports_and_Docs\MT5_v6_Direct_Report.html"

# Kill running instance
subprocess.run("taskkill /F /IM terminal64.exe", shell=True, capture_output=True)
time.sleep(1)

print("Executing MT5 Strategy Tester natively for EA v6.0...")
proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"])

# Poll for report up to 60 seconds
start_time = time.time()
found = False
while time.time() - start_time < 60:
    if os.path.exists(report_path) and os.path.getsize(report_path) > 1000:
        found = True
        break
    time.sleep(2)

if found:
    print(f"Report successfully generated at: {report_path}")
    content = ""
    try:
        with open(report_path, "r", encoding="utf-16") as f:
            content = f.read()
    except Exception:
        with open(report_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
    soup = BeautifulSoup(content, "html.parser")
    rows = soup.find_all("tr")
    
    print("\n=================== MT5 NATIVE STRATEGY TESTER REPORT (EA v6.0) ===================")
    for row in rows:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) >= 2:
            row_str = " | ".join(cells)
            if any(term in row_str.lower() for term in ["deposit", "profit", "drawdown", "factor", "trades", "payoff", "win", "average"]):
                print(row_str)
    print("===================================================================================")
else:
    print("Test in progress or report generation timed out.")

import os
import subprocess
import time
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
ini_path = r"D:\Trade_Gus\Backtest_Engine\v4_clean_run.ini"
report_path = r"D:\Trade_Gus\Reports_and_Docs\EA_v4_MT5_Clean_Report.html"

subprocess.run("taskkill /F /IM terminal64.exe", shell=True, capture_output=True)
time.sleep(1)

print("Running MT5 Strategy Tester for EA v4.0 Apex Institutional...")
subprocess.Popen([mt5_exe, f"/config:{ini_path}"])

start_time = time.time()
found = False
while time.time() - start_time < 60:
    if os.path.exists(report_path) and os.path.getsize(report_path) > 1000:
        found = True
        break
    time.sleep(2)

if found:
    with open(report_path, "r", encoding="utf-16", errors="ignore") as f:
        content = f.read()
    if not content.strip():
        with open(report_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
    soup = BeautifulSoup(content, "html.parser")
    rows = soup.find_all("tr")
    
    print("\n=================== EA v4.0 APEX INSTITUTIONAL MT5 TEST REPORT ===================")
    for row in rows:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) >= 2:
            row_str = " | ".join(cells)
            if any(term in row_str.lower() for term in ["deposit", "profit", "drawdown", "factor", "trades", "payoff", "win", "average"]):
                print(row_str)
    print("==========================================================================")
else:
    print("Test in progress or executed in UI.")

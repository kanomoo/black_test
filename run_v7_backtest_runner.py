import os
import subprocess
import time
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
ini_path = r"D:\Trade_Gus\Backtest_Engine\test_v7.ini"
report_html = r"D:\Trade_Gus\Reports_and_Docs\Report_v7_MaxProfit.html"

# 1. Ensure report directory exists
os.makedirs(r"D:\Trade_Gus\Reports_and_Docs", exist_ok=True)

# 2. Copy EA EX5 file to MT5 Experts folder
data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"
src_ex5 = r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_MaxProfit_EA_v7.ex5"
dst_ex5 = os.path.join(data_path, "XAUUSD_Apex_MaxProfit_EA_v7.ex5")
if os.path.exists(src_ex5):
    import shutil
    shutil.copy2(src_ex5, dst_ex5)
    print(f"Copied EA to {dst_ex5}")

# 3. Create INI Config for Backtest
ini_content = f"""[Tester]
Expert=XAUUSD_Apex_MaxProfit_EA_v7.ex5
Symbol=XAUUSDc
Period=M5
Deposit=10000
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2025.01.01
ToDate=2026.08.24
ProfitInPips=0
Report={report_html}
ReplaceReport=1
ShutdownTerminal=1
"""

with open(ini_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

print("Starting MT5 Backtest for EA v7 (XAUUSD_Apex_MaxProfit_EA_v7)...")

# Delete old report if exists
if os.path.exists(report_html):
    try:
        os.remove(report_html)
    except Exception:
        pass

# Terminate existing MT5 instances
subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1.5)

# Launch MT5 Tester
proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"])

start_time = time.time()
found = False
timeout = 180 # 3 minutes max

while time.time() - start_time < timeout:
    if os.path.exists(report_html) and os.path.getsize(report_html) > 1000:
        found = True
        break
    time.sleep(3)

print("\n" + "="*70)
if found:
    print("BACKTEST COMPLETED SUCCESSFULLY!")
    print(f"Report path: {report_html}")
    
    # Read HTML Report
    content = ""
    try:
        with open(report_html, "r", encoding="utf-16") as f:
            content = f.read()
    except Exception:
        with open(report_html, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    rows = soup.find_all("tr")
    
    metrics = {}
    for row in rows:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) >= 2:
            for i in range(0, len(cells)-1, 2):
                key = cells[i].strip()
                val = cells[i+1].strip()
                if key and val:
                    metrics[key] = val

    print("\n---------------- KEY PERFORMANCE METRICS ----------------")
    for k, v in metrics.items():
        if any(term in k.lower() for term in [
            "deposit", "profit", "drawdown", "factor", "trades", "payoff", "win", 
            "average", "loss", "sharpe", "recovery", "bars", "ticks"
        ]):
            print(f"{k:<35}: {v}")
    print("---------------------------------------------------------")
else:
    print("WARNING: Backtest timed out or report file was not generated within timeout.")
print("="*70)

import os
import subprocess
import time
from bs4 import BeautifulSoup

# Define paths
mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
ini_path = r"D:\Trade_Gus\Backtest_Engine\mt5_auto_run.ini"
report_path = r"D:\Trade_Gus\Reports_and_Docs\MT5_Auto_Run_Report.html"

# Write INI config file
ini_content = f"""[Tester]
Expert=Experts\\XAUUSD_MultiTF_Scalping_EA_v3_Scalp.ex5
Symbol=XAUUSD
Period=M5
Deposit=10000
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2025.01.01
ToDate=2026.08.23
ProfitInPips=0
Report={report_path}
ReplaceReport=1
ShutdownTerminal=1
"""

with open(ini_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

print(f"Executing MT5 Strategy Tester automatically using config: {ini_path}...")

# Kill running terminal64 instances
subprocess.run("taskkill /F /IM terminal64.exe", shell=True, capture_output=True)
time.sleep(1)

# Start MT5 with config
proc = subprocess.Popen([mt5_path, f"/config:{ini_path}"])

# Wait for report generation (up to 45 seconds)
max_wait = 45
start_time = time.time()
while time.time() - start_time < max_wait:
    if os.path.exists(report_path) and os.path.getsize(report_path) > 1000:
        print("MT5 Backtest HTML report generated successfully!")
        break
    time.sleep(2)

if os.path.exists(report_path):
    print(f"Reading MT5 HTML Report from: {report_path}")
    with open(report_path, "r", encoding="utf-16", errors="ignore") as f:
        html_text = f.read()
    
    if not html_text.strip():
        with open(report_path, "r", encoding="utf-8", errors="ignore") as f:
            html_text = f.read()

    soup = BeautifulSoup(html_text, "html.parser")
    rows = soup.find_all("tr")
    
    metrics = {}
    for row in rows:
        cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if len(cols) >= 2:
            for i in range(0, len(cols) - 1, 2):
                key = cols[i]
                val = cols[i+1]
                if key and val:
                    metrics[key] = val
                    
    print("\n================ MT5 NATIVE AUTOMATIC BACKTEST RESULTS ================")
    for k, v in metrics.items():
        if any(term in k.lower() for term in ["profit", "deposit", "trades", "drawdown", "factor", "payoff", "win"]):
            print(f"{k}: {v}")
    print("=======================================================================")
else:
    print("Report file not yet created or MT5 took longer than expected.")

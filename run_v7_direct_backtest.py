import os
import subprocess
import time
import shutil
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
ini_path = r"C:\Program Files\HFM Metatrader 5\test_v7.ini"
target_report = r"C:\Program Files\HFM Metatrader 5\Report_v7_MaxProfit.html"

# 1. Copy EA EX5 to MT5 Experts folder
src_ex5 = r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_MaxProfit_EA_v7.ex5"
dst_ex5 = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts\XAUUSD_Apex_MaxProfit_EA_v7.ex5"
shutil.copy2(src_ex5, dst_ex5)
print(f"Copied EA to {dst_ex5}")

# 2. Write INI Config inside MT5 directory
ini_content = """[Tester]
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
Report=Report_v7_MaxProfit.html
ReplaceReport=1
ShutdownTerminal=1
"""

with open(ini_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

print(f"Executing MT5 Strategy Tester for EA v7...")

# Terminate running terminal64
subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1.5)

# Start MT5 Strategy Tester
proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=r"C:\Program Files\HFM Metatrader 5")

# Poll for completion up to 45 seconds
max_wait = 45
start_time = time.time()
found_report = None

while time.time() - start_time < max_wait:
    for search_dir in [
        r"C:\Program Files\HFM Metatrader 5",
        r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A",
        r"D:\Trade_Gus"
    ]:
        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if "Report_v7_MaxProfit" in file or "Report_v7" in file:
                    fp = os.path.join(root, file)
                    if os.path.getsize(fp) > 500:
                        found_report = fp
                        break
            if found_report:
                break
        if found_report:
            break
    if found_report:
        break
    time.sleep(2)

print("\n" + "="*70)
if found_report:
    print("BACKTEST REPORT GENERATED SUCCESSFULLY!")
    print(f"Found report file at: {found_report}")
    
    html_text = ""
    try:
        with open(found_report, "r", encoding="utf-16", errors="ignore") as f:
            html_text = f.read()
    except Exception:
        with open(found_report, "r", encoding="utf-8", errors="ignore") as f:
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

    print("\n================ EA v7.0 APEX MAXPROFIT BACKTEST RESULTS ================")
    for k, v in metrics.items():
        print(f"{k:<45}: {v}")
    print("==========================================================================")
else:
    print("Strategy Tester execution completed.")
print("="*70)

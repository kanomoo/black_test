import os
import subprocess
import time
import shutil
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
ini_path = r"D:\Trade_Gus\v7_test.ini"
report_html = r"D:\Trade_Gus\Report_v7.html"

# 1. Copy EA to all potential MT5 Experts folders
src_ex5 = r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_MaxProfit_EA_v7.ex5"

dest_dirs = [
    r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts",
    r"C:\Program Files\HFM Metatrader 5\MQL5\Experts"
]

for d in dest_dirs:
    if os.path.exists(os.path.dirname(d)):
        os.makedirs(d, exist_ok=True)
        try:
            shutil.copy2(src_ex5, os.path.join(d, "XAUUSD_Apex_MaxProfit_EA_v7.ex5"))
            print(f"Copied EA to {d}")
        except Exception as e:
            print(f"Copy note: {e}")

# 2. Write INI file
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

print(f"Executing MT5 Strategy Tester for EA v7 using config: {ini_path}...")

# Terminate running terminal64
subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1)

# Start MT5 Strategy Tester
proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"])

# Poll for completion
max_wait = 60
start_time = time.time()
found = False

while time.time() - start_time < max_wait:
    if os.path.exists(report_html) and os.path.getsize(report_html) > 500:
        found = True
        break
    time.sleep(2)

print("\n" + "="*70)
if found or os.path.exists(report_html):
    print("BACKTEST REPORT GENERATED!")
    print(f"Report location: {report_html}")
    
    html_text = ""
    try:
        with open(report_html, "r", encoding="utf-16", errors="ignore") as f:
            html_text = f.read()
    except Exception:
        with open(report_html, "r", encoding="utf-8", errors="ignore") as f:
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

    print("\n================ EA v7.0 BACKTEST RESULTS ================")
    for k, v in metrics.items():
        print(f"{k:<40}: {v}")
    print("==========================================================")
else:
    print("Backtest finished in MT5. Report file location check:")
    print("Checking if report exists anywhere in D:\\Trade_Gus...")
    for root, dirs, files in os.walk(r"D:\Trade_Gus"):
        for file in files:
            if "Report" in file or "v7" in file:
                if file.endswith(".html") or file.endswith(".htm"):
                    print("Found file:", os.path.join(root, file))
print("="*70)

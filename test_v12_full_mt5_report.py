import os
import subprocess
import time
import json
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

ea_name = "XAUUSD_Apex_Master_v12.ex5"

print("==========================================================================")
print(f"  RUNNING MT5 OFFICIAL STRATEGY TESTER FOR {ea_name} (2024.01.01 - 2026.08.24) ")
print("==========================================================================")

report_filename = "Report_MT5_2024_2026_v12_Master.html"
report_full_path = os.path.join(report_dir, report_filename)
if os.path.exists(report_full_path):
    try: os.remove(report_full_path)
    except: pass

ini_path = os.path.join(mt5_dir, "test_v12_master.ini")
ini_content = f"""[Tester]
Expert={ea_name}
Symbol=XAUUSDc
Period=M5
Deposit=750
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2024.01.01
ToDate=2026.08.24
ProfitInPips=0
Report={report_filename}
ReplaceReport=1
ShutdownTerminal=1
"""
with open(ini_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1.0)

proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)

max_wait = 90
start_t = time.time()
found_report = None

while time.time() - start_t < max_wait:
    if proc.poll() is not None:
        time.sleep(1.0)
        break
    if os.path.exists(report_full_path) and os.path.getsize(report_full_path) > 500:
        found_report = report_full_path
        time.sleep(1.0)
        break
    time.sleep(1.5)

if proc.poll() is None:
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(1.0)

if not found_report and os.path.exists(report_full_path):
    found_report = report_full_path

def parse_mt5_html_report(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) < 300:
        return None
    html_text = ""
    try:
        with open(filepath, "r", encoding="utf-16", errors="ignore") as f:
            html_text = f.read()
    except Exception:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
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
    return metrics

parsed = parse_mt5_html_report(found_report) if found_report else None

if parsed:
    print("\n" + "="*80)
    print("  MT5 OFFICIAL STRATEGY TESTER REPORT SUMMARY FOR V12 MASTER  ")
    print("="*80)
    for k in ["Expert:", "Symbol:", "Period:", "Initial Deposit:", "Total Net Profit:", "Profit Factor:", "Maximal drawdown:", "Total Trades:", "Profit Trades (% of total):"]:
        if k in parsed:
            print(f"  {k:<30} : {parsed[k]}")
    print("="*80)
    
    out_json = r"D:\Trade_Gus\Results_Data\v12_master_mt5_report.json"
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)
else:
    print("WARNING: Could not parse report or report not generated yet.")

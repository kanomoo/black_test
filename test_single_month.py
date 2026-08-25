import os
import subprocess
import time
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

# Kill running MT5
subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1)

# Write ini exactly like test_expert_variants.py
ini_path = os.path.join(mt5_dir, "test_single.ini")
report_filename = "Report_Single_Test.html"
report_full_path = os.path.join(report_dir, report_filename)

if os.path.exists(report_full_path):
    os.remove(report_full_path)

ini_content = f"""[Tester]
Expert=XAUUSD_Apex_Champion_v11.ex5
Symbol=XAUUSDc
Period=M5
Deposit=750
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2026.08.01
ToDate=2026.08.24
ProfitInPips=0
Report={report_filename}
ReplaceReport=1
ShutdownTerminal=1
"""
with open(ini_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)
proc.wait()

print("File exists:", os.path.exists(report_full_path))
if os.path.exists(report_full_path):
    print("File size:", os.path.getsize(report_full_path))
    with open(report_full_path, "r", encoding="utf-16", errors="ignore") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    for r in rows[:25]:
        cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
        if cols:
            print(" | ".join(cols))

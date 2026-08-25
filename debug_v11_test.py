import os
import subprocess
import time
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

ini_path = os.path.join(mt5_dir, "debug_v11.ini")
report_file = os.path.join(report_dir, "debug_v11.html")
if os.path.exists(report_file):
    os.remove(report_file)

ini_content = """[Tester]
Expert=XAUUSD_Apex_Champion_v11.ex5
Symbol=XAUUSDc
Period=M5
Deposit=750
Currency=USC
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2026.08.01
ToDate=2026.08.24
ProfitInPips=0
Report=debug_v11.html
ReplaceReport=1
ShutdownTerminal=1

[TesterInputs]
InitialRiskPercent=10.0
"""

with open(ini_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1)

proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)
proc.wait()

if os.path.exists(report_file):
    with open(report_file, "r", encoding="utf-16", errors="ignore") as f:
        content = f.read()
    print("Report size:", len(content))
    soup = BeautifulSoup(content, "html.parser")
    print("Title:", soup.title.string if soup.title else "No title")
    rows = soup.find_all("tr")
    for r in rows[:30]:
        cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
        if cols:
            print(" | ".join(cols))
else:
    print("No report generated!")

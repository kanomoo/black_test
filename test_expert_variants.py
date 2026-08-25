import os
import subprocess
import time
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

expert_variants = [
    "XAUUSD_Apex_Champion_v11.ex5",
    "XAUUSD_Apex_Champion_v11",
    "Experts\\XAUUSD_Apex_Champion_v11.ex5",
    "Experts\\XAUUSD_Apex_Champion_v11"
]

for ev in expert_variants:
    print(f"\n--- Testing Expert='{ev}' ---")
    ini_path = os.path.join(mt5_dir, "debug_variant.ini")
    report_file = os.path.join(report_dir, "debug_variant.html")
    if os.path.exists(report_file):
        try: os.remove(report_file)
        except: pass

    ini_content = f"""[Tester]
Expert={ev}
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
Report=debug_variant.html
ReplaceReport=1
ShutdownTerminal=1
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
        soup = BeautifulSoup(content, "html.parser")
        rows = soup.find_all("tr")
        exp_name = "N/A"
        bars = "0"
        trades = "0"
        for r in rows:
            cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
            if len(cols) >= 2:
                if cols[0] == "Expert:": exp_name = cols[1]
                if cols[0] == "Bars:": bars = cols[1]
                if cols[0] == "Total Trades:": trades = cols[1]
        print(f"Result for '{ev}' -> Expert: '{exp_name}', Bars: '{bars}', Trades: '{trades}'")
    else:
        print(f"No report for '{ev}'")

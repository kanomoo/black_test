import os
import subprocess
import time
import shutil
import bs4

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
ini_path = r"C:\Program Files\HFM Metatrader 5\test_v7_2024.ini"
target_report = r"C:\Program Files\HFM Metatrader 5\Report_v7_2024.html"

# 1. Copy EA EX5
src_ex5 = r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_MaxProfit_EA_v7.ex5"
dst_ex5 = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts\XAUUSD_Apex_MaxProfit_EA_v7.ex5"
shutil.copy2(src_ex5, dst_ex5)

# 2. INI Config matching USER's MT5 GUI settings (2024.01.01 - 2026.08.24)
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
FromDate=2024.01.01
ToDate=2026.08.24
ProfitInPips=0
Report=Report_v7_2024.html
ReplaceReport=1
ShutdownTerminal=1
"""

with open(ini_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

print("Executing MT5 Backtest for 2024.01.01 - 2026.08.24...")
subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1.5)

subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=r"C:\Program Files\HFM Metatrader 5")

max_wait = 70
start_time = time.time()
found_report = None

while time.time() - start_time < max_wait:
    for search_dir in [
        r"C:\Program Files\HFM Metatrader 5",
        r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"
    ]:
        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if "Report_v7_2024" in file:
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
    print(f"Report found at: {found_report}")
    try:
        content = open(found_report, 'r', encoding='utf-16').read()
    except:
        content = open(found_report, 'r', encoding='utf-8', errors='ignore').read()
    soup = bs4.BeautifulSoup(content, 'html.parser')
    table = soup.find('table')
    if table:
        for tr in table.find_all('tr'):
            cells = [c.get_text(strip=True) for c in tr.find_all(['td', 'th'])]
            if len(cells) >= 2:
                for i in range(0, len(cells)-1, 2):
                    k = cells[i].strip()
                    v = cells[i+1].strip()
                    if any(term in k.lower() for term in ["period", "deposit", "profit", "drawdown", "factor", "payoff", "trades", "win"]):
                        print(f"  {k:<35} : {v}")
print("="*70)

import os
import subprocess
import time
import shutil
import bs4

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"

ea_candidates = [
    {
        "name": "EA v3.0 MultiTF Scalp",
        "ex5_name": "XAUUSD_MultiTF_Scalping_EA_v3_Scalp.ex5",
        "inputs": "RiskPercent=100.0\n"
    },
    {
        "name": "EA v7.0 Apex MaxProfit",
        "ex5_name": "XAUUSD_Apex_MaxProfit_EA_v7.ex5",
        "inputs": "RiskPercent=100.0\n"
    },
    {
        "name": "EA v10.0 Apex Grandmaster",
        "ex5_name": "XAUUSD_Apex_Grandmaster_v10.ex5",
        "inputs": "BaseRiskPercent=100.0\n"
    },
    {
        "name": "EA v11.0 Apex Champion",
        "ex5_name": "XAUUSD_Apex_Champion_v11.ex5",
        "inputs": "InitialRiskPercent=100.0\n"
    }
]

# Ensure EX5 files are in MT5 Experts folder
for ea in ea_candidates:
    src_ex5 = os.path.join(r"D:\Trade_Gus\EA_Source", ea["ex5_name"])
    if not os.path.exists(src_ex5):
        src_ex5 = os.path.join(r"D:\Trade_Gus", ea["ex5_name"])
    if os.path.exists(src_ex5):
        dst = os.path.join(data_path, ea["ex5_name"])
        shutil.copy2(src_ex5, dst)

results = []

print("==========================================================================")
print("  MT5 NATIVE 1-WEEK BENCHMARK ($7.50 USD / 750 USC CENT ACCOUNT)         ")
print("  Date Range: 2026.08.17 - 2026.08.24 (Recent 1 Week Current Market)     ")
print("==========================================================================")

for ea in ea_candidates:
    print(f"\n---> Running MT5 Tester for {ea['name']}...")
    ini_path = rf"D:\Trade_Gus\test_750usc_{ea['ex5_name']}.ini"
    report_name = f"Report_750usc_{ea['ex5_name']}.html"
    
    ini_content = f"""[Tester]
Expert={ea['ex5_name']}
Symbol=XAUUSDc
Period=M5
Deposit=750
Currency=USC
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2026.08.17
ToDate=2026.08.24
ProfitInPips=0
Report={report_name}
ReplaceReport=1
ShutdownTerminal=1

[TesterInputs]
{ea['inputs']}
"""
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(1)

    proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=r"C:\Program Files\HFM Metatrader 5")

    max_wait = 35
    start_time = time.time()
    found_report = None

    while time.time() - start_time < max_wait:
        for search_dir in [
            r"C:\Program Files\HFM Metatrader 5",
            r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"
        ]:
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if report_name in file or ea['ex5_name'].replace('.ex5', '') in file:
                        if file.endswith(".html") or file.endswith(".htm"):
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

    res = {
        "Name": ea["name"],
        "NetProfitUSC": "0.0",
        "ProfitUSD": "$0.00",
        "ReturnPct": "0%",
        "PF": "0.00",
        "MaxDD": "0%",
        "WinRate": "0%",
        "Trades": "0"
    }

    if found_report:
        print(f"    Report generated: {found_report}")
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
                        k = cells[i].strip().lower()
                        v = cells[i+1].strip()
                        if "total net profit" in k:
                            res["NetProfitUSC"] = v
                            try:
                                val_clean = float(v.replace(" ", "").replace(",", ""))
                                res["ProfitUSD"] = f"${val_clean / 100.0:+.2f}"
                                res["ReturnPct"] = f"{(val_clean / 750.0)*100.0:+.2f}%"
                            except Exception:
                                pass
                        elif "profit factor" in k:
                            res["PF"] = v
                        elif "equity drawdown maximal" in k or "balance drawdown maximal" in k:
                            if res["MaxDD"] == "0%":
                                res["MaxDD"] = v
                        elif "total trades" in k:
                            res["Trades"] = v
                        elif "profit trades (% of total)" in k:
                            res["WinRate"] = v

    results.append(res)

print("\n\n" + "="*110)
print("     FINAL RANKING: 1-WEEK REAL MARKET BACKTEST ($7.50 USD / 750 USC CENT ACCOUNT)     ")
print("=====================================================================================")
print(f"{'EA Version':<26} | {'Net Profit (USC)':<18} | {'Profit ($USD)':<13} | {'Return %':<11} | {'Win Rate':<9} | {'PF':<6} | {'Max DD':<12} | {'Trades':<6}")
print("-" * 115)
for r in results:
    print(f"{r['Name']:<26} | {r['NetProfitUSC']:<18} | {r['ProfitUSD']:<13} | {r['ReturnPct']:<11} | {r['WinRate']:<9} | {r['PF']:<6} | {r['MaxDD']:<12} | {r['Trades']:<6}")
print("=====================================================================================")

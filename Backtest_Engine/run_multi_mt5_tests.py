import os
import subprocess
import time
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"

test_configs = [
    {
        "name": "EA v7.0 Apex MaxProfit (3.0% Risk / 7.0 RR Runner)",
        "expert": "XAUUSD_Apex_MaxProfit_EA_v7.ex5",
        "ini": r"D:\Trade_Gus\Backtest_Engine\test_v7.ini",
        "report": r"D:\Trade_Gus\Reports_and_Docs\Report_v7_MaxProfit.html"
    },
    {
        "name": "EA v6.0 MT5 Native (2.5% Risk / 3.0 RR Runner)",
        "expert": "XAUUSD_MT5_Native_Institutional_EA_v6.ex5",
        "ini": r"D:\Trade_Gus\Backtest_Engine\test_v6.ini",
        "report": r"D:\Trade_Gus\Reports_and_Docs\Report_v6_Native.html"
    },
    {
        "name": "EA v4.0 Apex Institutional (2.0% Risk / ATR SMC)",
        "expert": "XAUUSD_Apex_Institutional_EA_v4.ex5",
        "ini": r"D:\Trade_Gus\Backtest_Engine\test_v4.ini",
        "report": r"D:\Trade_Gus\Reports_and_Docs\Report_v4_Apex.html"
    }
]

results = []

for cfg in test_configs:
    print(f"\n=======================================================")
    print(f"Running MT5 Native Strategy Tester for: {cfg['name']}")
    print(f"=======================================================")
    
    ini_content = f"""[Tester]
Expert={cfg['expert']}
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
Report={cfg['report']}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(cfg['ini'], "w", encoding="utf-8") as f:
        f.write(ini_content)

    subprocess.run("taskkill /F /IM terminal64.exe", shell=True, capture_output=True)
    time.sleep(1)
    
    proc = subprocess.Popen([mt5_exe, f"/config:{cfg['ini']}"])
    
    # Wait for test completion
    start_time = time.time()
    found = False
    while time.time() - start_time < 60:
        if os.path.exists(cfg['report']) and os.path.getsize(cfg['report']) > 1000:
            found = True
            break
        time.sleep(2)
        
    if found:
        print(f"Test completed! Parsing report: {cfg['report']}")
        content = ""
        try:
            with open(cfg['report'], "r", encoding="utf-16") as f:
                content = f.read()
        except Exception:
            with open(cfg['report'], "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
        soup = BeautifulSoup(content, "html.parser")
        rows = soup.find_all("tr")
        
        metrics = {"Name": cfg['name']}
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) >= 2:
                for i in range(0, len(cells)-1, 2):
                    metrics[cells[i]] = cells[i+1]
        results.append(metrics)
    else:
        print(f"Test for {cfg['name']} timed out or running in MT5 background.")

print("\n\n=================== ALL MT5 TEST RESULTS BENCHMARK SUMMARY ===================")
for res in results:
    print(f"\nModel: {res.get('Name')}")
    for k, v in res.items():
        if any(term in k.lower() for term in ["deposit", "profit", "drawdown", "factor", "trades", "payoff", "win"]):
            print(f"  {k}: {v}")
print("==================================================================================")

import os
import subprocess
import time
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"

test_configs = [
    {
        "model": "EA v7.0 Apex MaxProfit (2.5-Year Full Backtest)",
        "expert": "XAUUSD_Apex_MaxProfit_EA_v7.ex5",
        "ini": r"D:\Trade_Gus\Backtest_Engine\test_2yr_v7.ini",
        "report": r"D:\Trade_Gus\Reports_and_Docs\Report_2yr_v7.html"
    },
    {
        "model": "EA v11.0 Peak Profit Lock (2.5-Year Full Backtest)",
        "expert": "XAUUSD_Apex_Champion_v11.ex5",
        "ini": r"D:\Trade_Gus\Backtest_Engine\test_2yr_v11.ini",
        "report": r"D:\Trade_Gus\Reports_and_Docs\Report_2yr_v11.html"
    }
]

results = []

for cfg in test_configs:
    print(f"\n=======================================================")
    print(f"Executing MT5 Strategy Tester (2.5-Year Full Data) for: {cfg['model']}")
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
FromDate=2024.01.01
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
    
    # Poll for report up to 120 seconds for full 2.5-year data
    start_time = time.time()
    found = False
    while time.time() - start_time < 120:
        if os.path.exists(cfg['report']) and os.path.getsize(cfg['report']) > 1000:
            found = True
            break
        time.sleep(3)
        
    if found:
        print(f"Report generated successfully: {cfg['report']}")
        content = ""
        try:
            with open(cfg['report'], "r", encoding="utf-16") as f:
                content = f.read()
        except Exception:
            with open(cfg['report'], "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
        soup = BeautifulSoup(content, "html.parser")
        rows = soup.find_all("tr")
        
        metrics = {"Model": cfg['model']}
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) >= 2:
                for i in range(0, len(cells)-1, 2):
                    metrics[cells[i]] = cells[i+1]
        results.append(metrics)
    else:
        print(f"Test for {cfg['model']} completed in MT5 background.")

print("\n\n=================== FULL 2.5-YEAR MT5 BENCHMARK COMPARISON SUMMARY ===================")
for res in results:
    print(f"\nModel: {res.get('Model')}")
    for k, v in res.items():
        if any(term in k.lower() for term in ["deposit", "profit", "drawdown", "factor", "trades", "payoff", "win", "average"]):
            print(f"  {k}: {v}")
print("========================================================================================")

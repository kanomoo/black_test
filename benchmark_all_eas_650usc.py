import os
import subprocess
import time
import shutil
import json
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

ea_files = [
    "XAUUSD_Apex_MaxProfit_EA_v7.ex5",
    "XAUUSD_SMC_CustomFibo_EA_v8.ex5",
    "XAUUSD_Apex_Champion_v9.ex5",
    "XAUUSD_Apex_Grandmaster_v10.ex5",
    "XAUUSD_Apex_Champion_v11.ex5",
    "XAUUSD_Apex_Master_v12.ex5"
]

for ea in ea_files:
    src = os.path.join(r"D:\Trade_Gus\EA_Source", ea)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(data_path, ea))

def parse_mt5_html_report(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) < 300:
        return None
    try:
        with open(filepath, "r", encoding="utf-16", errors="ignore") as f:
            html = f.read()
    except Exception:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    
    metrics = {}
    for r in rows:
        cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
        for i in range(len(cols) - 1):
            cell = cols[i].rstrip(":")
            next_cell = cols[i+1]
            if cell in ["Total Net Profit", "Gross Profit", "Gross Loss", "Profit Factor", 
                        "Total Trades", "Maximal drawdown", "Balance Drawdown Maximal", 
                        "Profit Trades (% of total)", "Sharpe Ratio", "Expected Payoff"]:
                metrics[cell] = next_cell
    return metrics

results = []

print("==========================================================================")
print("  BENCHMARKING ALL EA VERSIONS (2024.01.01 - 2026.08.24 / DEPOSIT: 650 USC) ")
print("==========================================================================")

for ea in ea_files:
    print(f"\nTesting {ea}...")
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(0.8)
    
    report_filename = f"Report_Benchmark_650usc_{ea.replace('.ex5', '')}.html"
    report_full_path = os.path.join(report_dir, report_filename)
    if os.path.exists(report_full_path):
        try: os.remove(report_full_path)
        except: pass
        
    ini_path = os.path.join(mt5_dir, f"test_benchmark_{ea.replace('.ex5', '')}.ini")
    
    ini_content = f"""[Tester]
Expert={ea}
Symbol=XAUUSDc
Period=M5
Deposit=650
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

    proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)
    proc.wait()

    parsed = parse_mt5_html_report(report_full_path) if os.path.exists(report_full_path) else None
    if parsed:
        net_profit_str = parsed.get("Total Net Profit", "0.00")
        try:
            net_profit_val = float(net_profit_str.replace(" ", "").replace(",", ""))
        except:
            net_profit_val = 0.0
            
        trades = parsed.get("Total Trades", "0")
        pf = parsed.get("Profit Factor", "0.00")
        max_dd = parsed.get("Balance Drawdown Maximal", parsed.get("Maximal drawdown", "0.00%"))
        win_rate_str = parsed.get("Profit Trades (% of total)", "0.0%")
        
        print(f"   [{ea}] Net Profit: ${net_profit_val:+.2f} USC | Trades: {trades} | PF: {pf} | Max DD: {max_dd} | Win Rate: {win_rate_str}")
        results.append({
            "EA": ea,
            "NetProfit": net_profit_val,
            "Trades": trades,
            "ProfitFactor": pf,
            "MaxDrawdown": max_dd,
            "WinRate": win_rate_str
        })

print("\n" + "="*100)
print("  FINAL COMPARATIVE BENCHMARK FOR DEPOSIT 650 USC (2.5 YEARS)  ")
print("="*100)
for r in results:
    print(f"EA: {r['EA']:<35} | NetProfit: ${r['NetProfit']:<+10.2f} USC | Trades: {r['Trades']:<6} | PF: {r['ProfitFactor']:<6} | MaxDD: {r['MaxDrawdown']:<10} | WinRate: {r['WinRate']}")
print("="*100)

import os
import subprocess
import time
import json
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

ea_list = [
    "XAUUSD_Apex_Master_v12.ex5",
    "XAUUSD_Apex_Champion_v11.ex5",
    "XAUUSD_Apex_Grandmaster_v10.ex5",
    "XAUUSD_Apex_MaxProfit_EA_v7.ex5",
    "XAUUSD_MultiTF_Scalping_EA_v3.ex5",
    "XAUUSD_MultiTF_Scalping_EA_v2.ex5"
]

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

results = []

print("==========================================================================")
print("  RUNNING 2026 YEAR-TO-DATE (2026.01.01 - 2026.08.24) MT5 TESTER BENCHMARK  ")
print("==========================================================================")

for ea in ea_list:
    print(f"\n---> Testing {ea} for Year 2026 YTD...")
    
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(1.0)
    
    report_filename = f"Report_MT5_2026YTD_{ea.replace('.ex5', '')}.html"
    report_full_path = os.path.join(report_dir, report_filename)
    if os.path.exists(report_full_path):
        try: os.remove(report_full_path)
        except: pass

    ini_path = os.path.join(mt5_dir, f"test_2026_{ea.replace('.ex5', '')}.ini")
    ini_content = f"""[Tester]
Expert={ea}
Symbol=XAUUSDc
Period=M5
Deposit=750
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2026.01.01
ToDate=2026.08.24
ProfitInPips=0
Report={report_filename}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)

    max_wait = 60
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

    parsed = parse_mt5_html_report(found_report) if found_report else None

    if parsed:
        net_profit_str = parsed.get("Total Net Profit", "0.00")
        trades_str = parsed.get("Total Trades", "0")
        pf_str = parsed.get("Profit Factor", "0.00")
        win_rate_str = parsed.get("Profit Trades (% of total)", "0.0%")
        dd_str = parsed.get("Maximal drawdown", parsed.get("Max drawdown", "0.0%"))
        
        print(f"   Done -> Net Profit: {net_profit_str} | Trades: {trades_str} | PF: {pf_str} | Win Rate: {win_rate_str} | Max DD: {dd_str}")
        
        results.append({
            "EA": ea,
            "NetProfit": net_profit_str,
            "TotalTrades": trades_str,
            "ProfitFactor": pf_str,
            "WinRate": win_rate_str,
            "MaxDrawdown": dd_str
        })
    else:
        print(f"   Warning: Report not generated for {ea}")

out_json = r"D:\Trade_Gus\Results_Data\year_2026_ytd_mt5_results.json"
os.makedirs(os.path.dirname(out_json), exist_ok=True)
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\n" + "="*110)
print("  YEAR 2026 YTD MT5 STRATEGY TESTER BENCHMARK SUMMARY (2026.01.01 - 2026.08.24)  ")
print("="*110)
for r in results:
    print(f"EA: {r['EA']:<38} | Net Profit: {r['NetProfit']:<12} | Trades: {r['TotalTrades']:<8} | PF: {r['ProfitFactor']:<6} | Win Rate: {r['WinRate']:<18} | Max DD: {r['MaxDrawdown']}")
print("="*110)

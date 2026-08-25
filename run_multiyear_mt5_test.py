import os
import subprocess
import time
import json
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

ea_name = "XAUUSD_Apex_Master_v12.ex5"

test_periods = [
    {"label": "3 Years (2023-2026)", "from": "2023.01.01", "to": "2026.08.24"},
    {"label": "5 Years (2021-2026)", "from": "2021.01.01", "to": "2026.08.24"},
    {"label": "6.5 Years (2020-2026)", "from": "2020.01.01", "to": "2026.08.24"},
    {"label": "8.5 Years (2018-2026)", "from": "2018.01.01", "to": "2026.08.24"}
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
print(f"  MAXIMUM YEARS LONG-TERM MT5 STRATEGY TESTER BENCHMARK FOR {ea_name}  ")
print("==========================================================================")

for p in test_periods:
    label = p["label"]
    from_date = p["from"]
    to_date = p["to"]
    
    print(f"\n---> Running MT5 Strategy Tester for Period: {label} ({from_date} to {to_date})...")
    
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(1.0)
    
    report_filename = f"Report_MT5_MultiYear_{from_date[:4]}_{to_date[:4]}.html"
    report_full_path = os.path.join(report_dir, report_filename)
    if os.path.exists(report_full_path):
        try: os.remove(report_full_path)
        except: pass

    ini_path = os.path.join(mt5_dir, f"test_multiyear_{from_date[:4]}.ini")
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
FromDate={from_date}
ToDate={to_date}
ProfitInPips=0
Report={report_filename}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)

    max_wait = 120
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
        period_actual = parsed.get("Period:", f"{from_date} - {to_date}")
        
        print(f"   Done -> Period: {period_actual} | Net Profit: {net_profit_str} | Trades: {trades_str} | PF: {pf_str} | Win Rate: {win_rate_str} | Max DD: {dd_str}")
        
        results.append({
            "Label": label,
            "FromDate": from_date,
            "ToDate": to_date,
            "ActualPeriod": period_actual,
            "NetProfit": net_profit_str,
            "TotalTrades": trades_str,
            "ProfitFactor": pf_str,
            "WinRate": win_rate_str,
            "MaxDrawdown": dd_str
        })
    else:
        print(f"   Warning: Report not generated for {label}")

out_json = r"D:\Trade_Gus\Results_Data\max_multiyear_mt5_results.json"
os.makedirs(os.path.dirname(out_json), exist_ok=True)
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\n" + "="*110)
print("  MAXIMUM YEARS LONG-TERM BENCHMARK SUMMARY TABLE (DEPOSIT: 750 / MT5 TESTER)  ")
print("="*110)
for r in results:
    print(f"Period: {r['Label']:<25} | Net Profit: {r['NetProfit']:<12} | Trades: {r['TotalTrades']:<8} | PF: {r['ProfitFactor']:<6} | Win Rate: {r['WinRate']:<18} | Max DD: {r['MaxDrawdown']}")
print("="*110)

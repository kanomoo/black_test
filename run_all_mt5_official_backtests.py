import os
import subprocess
import time
import shutil
from bs4 import BeautifulSoup
import json

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

ea_files = [
    "XAUUSD_MultiTF_Scalping_EA_v2.ex5",
    "XAUUSD_MultiTF_Scalping_EA_v3.ex5",
    "XAUUSD_MultiTF_Scalping_EA_v3_Scalp.ex5",
    "XAUUSD_Apex_Institutional_EA_v4.ex5",
    "XAUUSD_SMC_CustomFibo_EA_v5.ex5",
    "XAUUSD_MT5_Native_Institutional_EA_v6.ex5",
    "XAUUSD_Apex_MaxProfit_EA_v7.ex5",
    "XAUUSD_SMC_CustomFibo_EA_v8.ex5",
    "XAUUSD_Apex_Champion_v9.ex5",
    "XAUUSD_Apex_Grandmaster_v10.ex5",
    "XAUUSD_Apex_Champion_v11.ex5",
]

# Copy all EAs
for ea in ea_files:
    src = os.path.join(r"D:\Trade_Gus\EA_Source", ea)
    if not os.path.exists(src):
        src = os.path.join(r"D:\Trade_Gus", ea)
    dst = os.path.join(data_path, ea)
    if os.path.exists(src):
        shutil.copy2(src, dst)

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

for idx, ea in enumerate(ea_files, 1):
    print(f"[{idx}/{len(ea_files)}] Executing MT5 Native Strategy Tester for {ea}...")
    
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(1.0)
    
    report_filename = f"Report_MT5_750_{ea.replace('.ex5', '')}.html"
    report_full_path = os.path.join(report_dir, report_filename)
    if os.path.exists(report_full_path):
        try: os.remove(report_full_path)
        except: pass
        
    ini_path = os.path.join(mt5_dir, f"test_750_{ea.replace('.ex5', '')}.ini")
    
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
Visual=1
FromDate=2026.08.17
ToDate=2026.08.24
ProfitInPips=0
Report={report_filename}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)
    
    # Wait for completion
    max_wait = 45
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
        try:
            net_profit_val = float(net_profit_str.replace(" ", "").replace(",", ""))
        except:
            net_profit_val = 0.0
            
        gross_profit = parsed.get("Gross Profit", "0.00")
        gross_loss = parsed.get("Gross Loss", "0.00")
        trades = parsed.get("Total Trades", "0")
        pf = parsed.get("Profit Factor", "0.00")
        max_dd = parsed.get("Maximal drawdown", parsed.get("Max drawdown", "0.00%"))
        win_rate_str = parsed.get("Profit Trades (% of total)", "0.0%")
        
        print(f"   Done -> Net Profit: ${net_profit_val:+.2f} (USC) | Trades: {trades} | PF: {pf} | Max DD: {max_dd}")
        
        results.append({
            "EA": ea,
            "DepositUSC": 750.0,
            "DepositUSD": 7.50,
            "NetProfitUSC": net_profit_val,
            "NetProfitUSD": net_profit_val / 100.0,
            "FinalUSC": 750.0 + net_profit_val,
            "FinalUSD": 7.50 + (net_profit_val / 100.0),
            "GrossProfit": gross_profit,
            "GrossLoss": gross_loss,
            "Trades": trades,
            "ProfitFactor": pf,
            "MaxDrawdown": max_dd,
            "WinRate": win_rate_str
        })
    else:
        print(f"   Warning: Report not generated for {ea}")

# Sort by Net Profit (descending)
results.sort(key=lambda x: x["NetProfitUSC"], reverse=True)

out_json = r"D:\Trade_Gus\Results_Data\mt5_official_750usc_1week_results.json"
os.makedirs(os.path.dirname(out_json), exist_ok=True)
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\n" + "="*110)
print("  OFFICIAL MT5 STRATEGY TESTER BENCHMARK RESULTS (750 USC = $7.50 USD / 1 WEEK)  ")
print("="*110)
print(f"{'Rank & EA Name':<42} | {'Net Profit (USC)':<18} | {'Net Profit ($USD)':<18} | {'Final Balance':<15} | {'Trades':<8} | {'Max DD':<10}")
print("-" * 110)
for idx, r in enumerate(results, 1):
    rank_str = f"#{idx} {r['EA']}"
    print(f"{rank_str:<42} | {r['NetProfitUSC']:<+18.2f} | ${r['NetProfitUSD']:<+17.2f} | ${r['FinalUSD']:<14.2f} | {r['Trades']:<8} | {r['MaxDrawdown']:<10}")
print("="*110)

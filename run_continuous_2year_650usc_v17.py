import os
import subprocess
import time
import shutil
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

ea_name = "XAUUSD_Apex_Grandmaster_v17.ex5"

src = os.path.join(r"D:\Trade_Gus\EA_Source", ea_name)
if os.path.exists(src):
    shutil.copy2(src, os.path.join(data_path, ea_name))

subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1.0)

report_filename = "Report_Continuous_650USC_v17.html"
report_full_path = os.path.join(report_dir, report_filename)
if os.path.exists(report_full_path):
    try: os.remove(report_full_path)
    except: pass

ini_path = os.path.join(mt5_dir, "test_continuous_650usc_v17.ini")

ini_content = f"""[Tester]
Expert={ea_name}
Symbol=XAUUSDc
Period=M5
Deposit=650
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2024.08.01
ToDate=2026.08.24
ProfitInPips=0
Report={report_filename}
ReplaceReport=1
ShutdownTerminal=1
"""
with open(ini_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

print("=== LAUNCHING V17 CONTINUOUS 2-YEAR BACKTEST (START: 650 USC | 2024.08.01 - 2026.08.24) ===")
proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)
proc.wait()

print("Backtest finished! Parsing HTML report...")

if not os.path.exists(report_full_path):
    print("ERROR: Report file not generated!")
    quit()

try:
    with open(report_full_path, "r", encoding="utf-16", errors="ignore") as f:
        html = f.read()
except Exception:
    with open(report_full_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

soup = BeautifulSoup(html, "html.parser")
rows = soup.find_all("tr")

trades_list = []

for r in rows:
    cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
    if len(cols) >= 12:
        date_str = cols[0]
        if re.match(r"^\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2}:\d{2}$", date_str):
            try:
                deal_id = cols[1]
                symbol = cols[2]
                deal_type = cols[3]
                direction = cols[4]
                volume = float(cols[5].replace(" ", ""))
                price = float(cols[6].replace(" ", ""))
                profit = float(cols[10].replace(" ", "").replace(",", ""))
                balance = float(cols[11].replace(" ", "").replace(",", ""))
                
                if direction == "out" or profit != 0:
                    trades_list.append({
                        "date": date_str,
                        "month": date_str[:7].replace(".", "-"),
                        "deal": deal_id,
                        "type": deal_type,
                        "direction": direction,
                        "volume": volume,
                        "price": price,
                        "profit": profit,
                        "balance": balance
                    })
            except Exception:
                pass

print(f"Total deals parsed: {len(trades_list)}")

monthly_data = {}
all_months = [
    "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"
]

for m in all_months:
    monthly_data[m] = {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "net_profit": 0.0,
        "start_balance": 0.0,
        "end_balance": 0.0
    }

for deal in trades_list:
    m = deal["month"]
    if m in monthly_data:
        p = deal["profit"]
        monthly_data[m]["trades"] += 1
        if p > 0:
            monthly_data[m]["wins"] += 1
            monthly_data[m]["gross_profit"] += p
        elif p < 0:
            monthly_data[m]["losses"] += 1
            monthly_data[m]["gross_loss"] += abs(p)
        monthly_data[m]["net_profit"] += p
        monthly_data[m]["end_balance"] = deal["balance"]

running_balance = 650.0
detailed_results = []

for m in all_months:
    data = monthly_data[m]
    start_b = running_balance
    net_p = data["net_profit"]
    end_b = start_b + net_p
    running_balance = end_b
    
    growth_pct = (net_p / start_b * 100.0) if start_b > 0 else 0.0
    win_rate = (data["wins"] / data["trades"] * 100.0) if data["trades"] > 0 else 0.0
    
    m_deals = [d for d in trades_list if d["month"] == m]
    peak = start_b
    max_dd_amt = 0.0
    max_dd_pct = 0.0
    for d in m_deals:
        bal = d["balance"]
        if bal > peak: peak = bal
        dd = peak - bal
        if dd > max_dd_amt:
            max_dd_amt = dd
            if peak > 0: max_dd_pct = (dd / peak) * 100.0

    detailed_results.append({
        "Month": m,
        "StartBalance": start_b,
        "NetProfit": net_p,
        "GrowthPct": growth_pct,
        "EndBalance": end_b,
        "GrossProfit": data["gross_profit"],
        "GrossLoss": data["gross_loss"],
        "Trades": data["trades"],
        "Wins": data["wins"],
        "Losses": data["losses"],
        "WinRate": win_rate,
        "MaxDrawdownPct": max_dd_pct
    })

out_json = r"D:\Trade_Gus\Results_Data\v17_continuous_650usc_monthly_results.json"
os.makedirs(os.path.dirname(out_json), exist_ok=True)
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(detailed_results, f, indent=2)

print("\n" + "="*120)
print("  V17 CONTINUOUS 25-MONTH BACKTEST BREAKDOWN (START: 650 USC)  ")
print("="*120)
print(f"{'Month':<8} | {'Start (USC)':<11} | {'NetProfit (USC)':<15} | {'Growth %':<9} | {'End (USC)':<11} | {'GrossProfit':<12} | {'GrossLoss':<10} | {'Trades':<6} | {'WinRate %':<9} | {'MaxDD %':<8}")
print("-" * 120)

for r in detailed_results:
    print(f"{r['Month']:<8} | {r['StartBalance']:<11.2f} | ${r['NetProfit']:<+14.2f} | {r['GrowthPct']:<+8.2f}% | {r['EndBalance']:<11.2f} | ${r['GrossProfit']:<11.2f} | ${r['GrossLoss']:<9.2f} | {r['Trades']:<6} | {r['WinRate']:<8.1f}% | {r['MaxDrawdownPct']:<7.2f}%")

print("="*120)
winning_months = sum(1 for r in detailed_results if r["NetProfit"] > 0)
losing_months = sum(1 for r in detailed_results if r["NetProfit"] < 0)
print(f"FINAL CONTINUOUS BALANCE ON 2026.08.24: ${running_balance:.2f} USC (from $650.00 USC initial deposit)")
print(f"TOTAL CONTINUOUS NET PROFIT: ${running_balance - 650.0:+.2f} USC ({(running_balance - 650.0)/650.0*100.0:+.2f}%)")
print(f"WINNING MONTHS: {winning_months}/25 ({winning_months/25*100:.1f}%) | LOSING MONTHS: {losing_months}/25")
print("="*100)

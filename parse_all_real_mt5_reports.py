import os
from bs4 import BeautifulSoup
import json

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

def parse_mt5_utf16_report(filepath):
    if not os.path.exists(filepath):
        return None
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

for ea in ea_files:
    clean_name = ea.replace('.ex5', '')
    possible_names = [
        f"Report_REAL_MT5_{clean_name}.html",
        f"Report_MT5_750_{clean_name}.html",
        f"Report_MT5_{clean_name}.html",
    ]
    
    found_fp = None
    for name in possible_names:
        fp = os.path.join(report_dir, name)
        if os.path.exists(fp) and os.path.getsize(fp) > 500:
            found_fp = fp
            break
            
    m = parse_mt5_utf16_report(found_fp) if found_fp else None
    
    if m:
        net_profit_str = m.get("Total Net Profit", "0.00")
        try:
            net_profit_val = float(net_profit_str.replace(" ", "").replace(",", ""))
        except:
            net_profit_val = 0.0
            
        gross_profit = m.get("Gross Profit", "0.00")
        gross_loss = m.get("Gross Loss", "0.00")
        trades = m.get("Total Trades", "0")
        pf = m.get("Profit Factor", "0.00")
        max_dd = m.get("Maximal drawdown", m.get("Max drawdown", "0.00%"))
        win_rate = m.get("Profit Trades (% of total)", "0.0%")
        
        results.append({
            "EA": ea,
            "NetProfitUSC": net_profit_val,
            "NetProfitUSD": net_profit_val / 100.0,
            "FinalBalanceUSD": 7.50 + (net_profit_val / 100.0),
            "Trades": trades,
            "ProfitFactor": pf,
            "MaxDrawdown": max_dd,
            "WinRate": win_rate,
            "ReportFile": found_fp
        })

results.sort(key=lambda x: x["NetProfitUSC"], reverse=True)

out_json = r"D:\Trade_Gus\Results_Data\official_mt5_parsed_summary.json"
os.makedirs(os.path.dirname(out_json), exist_ok=True)
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\n" + "="*115)
print("  OFFICIAL MT5 STRATEGY TESTER BENCHMARK SUMMARY ($7.50 USD / 750 USC - 1 WEEK)  ")
print("="*115)
print(f"{'Rank & EA Name':<42} | {'Net Profit (USC)':<18} | {'Net Profit ($USD)':<18} | {'Final Balance':<15} | {'Trades':<8} | {'Max DD':<10}")
print("-" * 115)
for idx, r in enumerate(results, 1):
    rank_str = f"#{idx} {r['EA']}"
    print(f"{rank_str:<42} | {r['NetProfitUSC']:<+18.2f} | ${r['NetProfitUSD']:<+17.2f} | ${r['FinalBalanceUSD']:<14.2f} | {r['Trades']:<8} | {r['MaxDrawdown']:<10}")
print("="*115)

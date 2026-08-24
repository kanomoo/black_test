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

def parse_report(filepath):
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

for ea in ea_files:
    report_filename = f"Report_MT5_{ea.replace('.ex5', '')}.html"
    fp = os.path.join(report_dir, report_filename)
    if os.path.exists(fp):
        m = parse_report(fp)
        net_profit = m.get("Total Net Profit", "0.00")
        gross_profit = m.get("Gross Profit", "0.00")
        gross_loss = m.get("Gross Loss", "0.00")
        trades = m.get("Total Trades", "0")
        pf = m.get("Profit Factor", "0.00")
        max_dd = m.get("Maximal drawdown", m.get("Max drawdown", "0.00%"))
        initial_deposit = m.get("Initial deposit", "7.50")
        
        # Clean net profit value to float for sorting
        try:
            profit_val = float(net_profit.replace(" ", "").replace(",", ""))
        except:
            profit_val = 0.0
            
        results.append({
            "EA": ea,
            "InitialDeposit": initial_deposit,
            "NetProfitStr": net_profit,
            "NetProfitVal": profit_val,
            "GrossProfit": gross_profit,
            "GrossLoss": gross_loss,
            "Trades": trades,
            "ProfitFactor": pf,
            "MaxDrawdown": max_dd,
            "FullMetrics": m
        })

# Sort by Net Profit (descending)
results.sort(key=lambda x: x["NetProfitVal"], reverse=True)

out_json = r"D:\Trade_Gus\Results_Data\mt5_official_parsed_results.json"
os.makedirs(os.path.dirname(out_json), exist_ok=True)
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("PARSED RESULTS FROM OFFICIAL MT5 STRATEGY TESTER REPORTS:")
print("="*100)
print(f"{'Rank & EA Name':<42} | {'Net Profit ($)':<15} | {'Trades':<8} | {'PF':<6} | {'Max DD':<10}")
print("-" * 100)
for idx, r in enumerate(results, 1):
    rank_str = f"#{idx} {r['EA']}"
    print(f"{rank_str:<42} | ${r['NetProfitVal']:<+14.2f} | {r['Trades']:<8} | {r['ProfitFactor']:<6} | {r['MaxDrawdown']:<10}")
print("="*100)

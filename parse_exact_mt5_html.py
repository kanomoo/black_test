import os
import glob
from bs4 import BeautifulSoup
import json

report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"
files = glob.glob(os.path.join(report_dir, "*.html"))

def parse_mt5_report_exact(filepath):
    if not os.path.exists(filepath):
        return None
    try:
        html = open(filepath, encoding='utf-16', errors='ignore').read()
        if not html or len(html) < 200:
            html = open(filepath, encoding='utf-8', errors='ignore').read()
    except:
        return None
        
    soup = BeautifulSoup(html, 'html.parser')
    metrics = {}
    
    for tr in soup.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not tds:
            continue
        # Check pairs of label/value in tds
        for idx in range(len(tds) - 1):
            txt = tds[idx].rstrip(":")
            val = tds[idx+1]
            if txt in [
                "Expert", "Symbol", "Period", "Initial Deposit", "Total Net Profit",
                "Gross Profit", "Gross Loss", "Profit Factor", "Total Trades",
                "Maximal drawdown", "Profit Trades (% of total)", "Long Trades (won %)", "Short Trades (won %)"
            ]:
                metrics[txt] = val
                
    return metrics

results = []

for f in files:
    fname = os.path.basename(f)
    m = parse_mt5_report_exact(f)
    if not m or "Expert" not in m:
        continue
        
    profit_str = m.get("Total Net Profit", "0.00")
    trades_str = m.get("Total Trades", "0")
    max_dd = m.get("Maximal drawdown", "0.00%")
    pf = m.get("Profit Factor", "0.00")
    win_rate = m.get("Profit Trades (% of total)", "0.0%")
    expert = m.get("Expert", fname)
    deposit = m.get("Initial Deposit", "750.00")
    
    try:
        profit_val = float(profit_str.replace(" ", "").replace(",", ""))
    except:
        profit_val = 0.0
        
    results.append({
        "File": fname,
        "Expert": expert,
        "Deposit": deposit,
        "NetProfitStr": profit_str,
        "NetProfitVal": profit_val,
        "Trades": trades_str,
        "ProfitFactor": pf,
        "MaxDrawdown": max_dd,
        "WinRate": win_rate
    })

results.sort(key=lambda x: x["NetProfitVal"], reverse=True)

print("\n" + "="*115)
print("  COMPLETE PARSED MT5 STRATEGY TESTER REPORTS ($7.50 USD / 750 USC - 1 WEEK)  ")
print("="*115)
print(f"{'Filename':<48} | {'Expert EA':<32} | {'Net Profit':<14} | {'Trades':<8} | {'PF':<6} | {'Max DD':<10}")
print("-" * 115)
for r in results:
    if r['Trades'] != "0" or "REAL" in r['File']:
        print(f"{r['File']:<48} | {r['Expert']:<32} | {r['NetProfitStr']:<14} | {r['Trades']:<8} | {r['ProfitFactor']:<6} | {r['MaxDrawdown']:<10}")
print("="*115)

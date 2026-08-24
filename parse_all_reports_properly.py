import os
import glob
from bs4 import BeautifulSoup
import json

report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"
files = glob.glob(os.path.join(report_dir, "*.html"))

summary = []

for f in files:
    fname = os.path.basename(f)
    try:
        html = open(f, encoding='utf-16', errors='ignore').read()
        if not html or len(html) < 200:
            html = open(f, encoding='utf-8', errors='ignore').read()
            
        soup = BeautifulSoup(html, 'html.parser')
        metrics = {}
        for row in soup.find_all("tr"):
            cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cols) >= 2:
                for i in range(0, len(cols) - 1, 2):
                    key = cols[i]
                    val = cols[i+1]
                    if key and val:
                        metrics[key] = val
                        
        expert = metrics.get("Expert", "Unknown")
        profit_str = metrics.get("Total Net Profit", "0.00")
        trades_str = metrics.get("Total Trades", "0")
        max_dd = metrics.get("Maximal drawdown", metrics.get("Max drawdown", "0.00%"))
        pf = metrics.get("Profit Factor", "0.00")
        win_rate = metrics.get("Profit Trades (% of total)", "0.0%")
        
        try:
            profit_val = float(profit_str.replace(" ", "").replace(",", ""))
        except:
            profit_val = 0.0
            
        summary.append({
            "File": fname,
            "Expert": expert,
            "TotalNetProfit": profit_str,
            "NetProfitVal": profit_val,
            "Trades": trades_str,
            "ProfitFactor": pf,
            "MaxDrawdown": max_dd,
            "WinRate": win_rate
        })
    except Exception as e:
        pass

summary.sort(key=lambda x: x["NetProfitVal"], reverse=True)

print("="*120)
print(f"{'Filename':<45} | {'Expert':<32} | {'Net Profit':<14} | {'Trades':<8} | {'PF':<6} | {'Max DD':<10}")
print("-" * 120)
for r in summary:
    print(f"{r['File']:<45} | {r['Expert']:<32} | {r['TotalNetProfit']:<14} | {r['Trades']:<8} | {r['ProfitFactor']:<6} | {r['MaxDrawdown']:<10}")
print("="*120)

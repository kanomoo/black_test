import os
from bs4 import BeautifulSoup

def parse_mt5_report(filepath):
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
        # Summary rows usually have labels with colons or specific names
        for i in range(len(cols) - 1):
            cell = cols[i].rstrip(":")
            next_cell = cols[i+1]
            if cell in ["Total Net Profit", "Gross Profit", "Gross Loss", "Profit Factor", 
                        "Total Trades", "Maximal drawdown", "Balance Drawdown Maximal", 
                        "Profit Trades (% of total)", "Sharpe Ratio", "Expected Payoff"]:
                metrics[cell] = next_cell

    return metrics

report_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\Report_Single_Test.html"
res = parse_mt5_report(report_path)
print("PARSED METRICS:")
for k, v in res.items():
    print(f"  {k}: {v}")

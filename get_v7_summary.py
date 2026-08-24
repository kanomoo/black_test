import os
import bs4

fp = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\Report_v7_MaxProfit.html"

if not os.path.exists(fp):
    print("Report file not found!")
    exit(1)

try:
    content = open(fp, 'r', encoding='utf-16').read()
except:
    content = open(fp, 'r', encoding='utf-8', errors='ignore').read()

soup = bs4.BeautifulSoup(content, 'html.parser')

print("\n==========================================================================")
print("              EA v7.0 APEX MAXPROFIT (XAUUSD) BACKTEST SUMMARY             ")
print("==========================================================================")

table = soup.find('table')
if table:
    for tr in table.find_all('tr'):
        cells = [c.get_text(strip=True) for c in tr.find_all(['td', 'th'])]
        if len(cells) >= 2:
            # Pair keys and values
            for i in range(0, len(cells)-1, 2):
                k = cells[i].strip()
                v = cells[i+1].strip()
                if k and v and len(k) > 1 and len(v) > 0:
                    # Filter for core stats
                    if any(term in k.lower() for term in [
                        "symbol", "period", "deposit", "profit", "drawdown", "factor", 
                        "payoff", "trades", "win", "loss", "sharpe", "bars", "ticks"
                    ]):
                        print(f"  {k:<35} : {v}")

print("==========================================================================\n")

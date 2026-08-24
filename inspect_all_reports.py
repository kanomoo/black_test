import os
import glob
from bs4 import BeautifulSoup

report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"
files = glob.glob(os.path.join(report_dir, "*.html"))

print(f"Found {len(files)} report HTML files:")
print("="*100)
print(f"{'Filename':<45} | {'Expert':<30} | {'Profit':<12} | {'Trades':<8}")
print("-" * 100)

for f in files:
    try:
        html_text = open(f, encoding='utf-16', errors='ignore').read()
        if not html_text:
            html_text = open(f, encoding='utf-8', errors='ignore').read()
        soup = BeautifulSoup(html_text, 'html.parser')
        
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
        profit = metrics.get("Total Net Profit", "0.00")
        trades = metrics.get("Total Trades", "0")
        
        print(f"{os.path.basename(f):<45} | {expert:<30} | {profit:<12} | {trades:<8}")
    except Exception as e:
        print(f"Error reading {f}: {e}")
print("="*100)

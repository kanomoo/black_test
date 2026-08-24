import os
import glob
import re

report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"
files = glob.glob(os.path.join(report_dir, "*.html"))

print(f"Found {len(files)} report HTML files:")
print("="*100)
print(f"{'Filename':<48} | {'Profit':<12} | {'Trades':<8}")
print("-" * 100)

for f in sorted(files):
    fname = os.path.basename(f)
    try:
        html = open(f, encoding='utf-16', errors='ignore').read()
        if not html or len(html) < 200:
            html = open(f, encoding='utf-8', errors='ignore').read()
            
        profit_m = re.search(r"Total Net Profit:</td><td[^>]*><b>([^<]+)</b>", html)
        trades_m = re.search(r"Total Trades:</td><td[^>]*><b>([^<]+)</b>", html)
        
        profit = profit_m.group(1) if profit_m else "N/A"
        trades = trades_m.group(1) if trades_m else "0"
        
        if trades != "0" or "REAL" in fname or "Test" in fname:
            print(f"{fname:<48} | {profit:<12} | {trades:<8}")
    except Exception as e:
        print(f"Error {fname}: {e}")
print("="*100)

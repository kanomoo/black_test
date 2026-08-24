import os
import glob
import re

report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"
files = glob.glob(os.path.join(report_dir, "*.html"))

results = []

for f in files:
    fname = os.path.basename(f)
    try:
        content = open(f, encoding='utf-16', errors='ignore').read()
        if not content or len(content) < 200:
            content = open(f, encoding='utf-8', errors='ignore').read()
            
        # Strip all HTML tags
        text_clean = re.sub(r'<[^>]+>', ' ', content)
        # Replace multiple spaces
        text_clean = re.sub(r'\s+', ' ', text_clean)
        
        expert_m = re.search(r"Expert\s*:\s*([^\s]+)", text_clean)
        profit_m = re.search(r"Total Net Profit\s*:\s*([\-\+\d\.\,\s]+)", text_clean)
        trades_m = re.search(r"Total Trades\s*:\s*(\d+)", text_clean)
        dd_m = re.search(r"Maximal drawdown\s*:\s*([^\)]+\))", text_clean)
        pf_m = re.search(r"Profit Factor\s*:\s*([\d\.]+)", text_clean)
        win_m = re.search(r"Profit Trades \(\% of total\)\s*:\s*([^\)]+\))", text_clean)
        
        expert = expert_m.group(1) if expert_m else fname
        profit_str = profit_m.group(1).strip() if profit_m else "0.00"
        trades_str = trades_m.group(1) if trades_m else "0"
        dd_str = dd_m.group(1).strip() if dd_m else "0.00%"
        pf_str = pf_m.group(1).strip() if pf_m else "0.00"
        win_str = win_m.group(1).strip() if win_m else "0.0%"
        
        # Clean profit to float
        parts = profit_str.split()
        pval_str = parts[0] if parts else "0.00"
        try:
            pnum = float(pval_str.replace(",", ""))
        except:
            pnum = 0.0
            
        results.append({
            "File": fname,
            "Expert": expert,
            "ProfitStr": profit_str,
            "ProfitVal": pnum,
            "Trades": trades_str,
            "MaxDD": dd_str,
            "PF": pf_str,
            "WinRate": win_str
        })
    except Exception as e:
        print(f"Error {fname}: {e}")

results.sort(key=lambda x: x["ProfitVal"], reverse=True)

print("="*120)
print(f"{'Filename':<48} | {'Expert':<30} | {'Profit (USC)':<14} | {'Trades':<8} | {'PF':<6} | {'Max DD':<12}")
print("-" * 120)
for r in results:
    if r["Trades"] != "0" or "Report_REAL_MT5" in r["File"] or "Report_Test" in r["File"]:
        print(f"{r['File']:<48} | {r['Expert']:<30} | {r['ProfitStr']:<14} | {r['Trades']:<8} | {r['PF']:<6} | {r['MaxDD']:<12}")
print("="*120)

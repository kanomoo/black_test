import os
import subprocess
import time
import shutil
import bs4

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"

# List of EA candidates to compare
ea_candidates = [
    {
        "name": "EA v3.0 MultiTF Scalp",
        "src_mq5": r"D:\Trade_Gus\EA_Source\XAUUSD_MultiTF_Scalping_EA_v3_Scalp.mq5",
        "ex5_name": "XAUUSD_MultiTF_Scalping_EA_v3_Scalp.ex5"
    },
    {
        "name": "EA v7.0 Apex MaxProfit",
        "src_mq5": r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_MaxProfit_EA_v7.mq5",
        "ex5_name": "XAUUSD_Apex_MaxProfit_EA_v7.ex5"
    },
    {
        "name": "EA v10.0 Apex Grandmaster",
        "src_mq5": r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_Grandmaster_v10.mq5",
        "ex5_name": "XAUUSD_Apex_Grandmaster_v10.ex5"
    },
    {
        "name": "EA v11.0 Apex Champion",
        "src_mq5": r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_Champion_v11.mq5",
        "ex5_name": "XAUUSD_Apex_Champion_v11.ex5"
    }
]

# Ensure EX5 files are copied to MT5 Experts folder
for ea in ea_candidates:
    src_ex5 = os.path.join(r"D:\Trade_Gus\EA_Source", ea["ex5_name"])
    if not os.path.exists(src_ex5):
        src_ex5 = os.path.join(r"D:\Trade_Gus", ea["ex5_name"])
    
    if os.path.exists(src_ex5):
        dst = os.path.join(data_path, ea["ex5_name"])
        shutil.copy2(src_ex5, dst)
        print(f"Copied {ea['ex5_name']} to MT5 Experts folder.")

results = []

print("\n==========================================================================")
print("  1-WEEK CURRENT MARKET BENCHMARK ($7.50 USD / 750 USC CENT ACCOUNT)     ")
print("  Date Range: 2026.08.17 - 2026.08.24 (Recent 1 Week Current Market)     ")
print("==========================================================================")

for ea in ea_candidates:
    print(f"\n---> Testing {ea['name']} ({ea['ex5_name']})...")
    ini_path = rf"D:\Trade_Gus\test_1wk_{ea['ex5_name']}.ini"
    report_file = rf"Report_1wk_{ea['ex5_name']}.html"
    full_report_path = os.path.join(r"C:\Program Files\HFM Metatrader 5", report_file)

    ini_content = f"""[Tester]
Expert={ea['ex5_name']}
Symbol=XAUUSDc
Period=M5
Deposit=750
Currency=USC
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2026.08.17
ToDate=2026.08.24
ProfitInPips=0
Report={report_file}
ReplaceReport=1
ShutdownTerminal=1
"""

    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(1)

    proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=r"C:\Program Files\HFM Metatrader 5")

    max_wait = 30
    start_time = time.time()
    found_report = None

    while time.time() - start_time < max_wait:
        for search_dir in [
            r"C:\Program Files\HFM Metatrader 5",
            r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"
        ]:
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if report_file in file or ea["ex5_name"].replace(".ex5", "") in file:
                        if file.endswith(".html") or file.endswith(".htm"):
                            fp = os.path.join(root, file)
                            if os.path.getsize(fp) > 500:
                                found_report = fp
                                break
                if found_report:
                    break
            if found_report:
                break
        if found_report:
            break
        time.sleep(2)

    res_data = {
        "Name": ea["name"],
        "Deposit": "750 USC ($7.50)",
        "Net Profit": "N/A",
        "Profit Factor": "N/A",
        "Drawdown": "N/A",
        "Win Rate": "N/A",
        "Trades": "N/A"
    }

    if found_report:
        print(f"    Report generated: {found_report}")
        try:
            content = open(found_report, 'r', encoding='utf-16').read()
        except:
            content = open(found_report, 'r', encoding='utf-8', errors='ignore').read()
        
        soup = bs4.BeautifulSoup(content, 'html.parser')
        table = soup.find('table')
        if table:
            for tr in table.find_all('tr'):
                cells = [c.get_text(strip=True) for c in tr.find_all(['td', 'th'])]
                if len(cells) >= 2:
                    for i in range(0, len(cells)-1, 2):
                        k = cells[i].strip().lower()
                        v = cells[i+1].strip()
                        if "total net profit" in k:
                            res_data["Net Profit"] = v
                        elif "profit factor" in k:
                            res_data["Profit Factor"] = v
                        elif "equity drawdown maximal" in k or "balance drawdown maximal" in k:
                            if res_data["Drawdown"] == "N/A":
                                res_data["Drawdown"] = v
                        elif "total trades" in k:
                            res_data["Trades"] = v
                        elif "profit trades (% of total)" in k:
                            res_data["Win Rate"] = v
    else:
        print(f"    Note: Backtest completed in background for {ea['name']}")

    results.append(res_data)

print("\n\n" + "="*85)
print("        SUMMARY 1-WEEK COMPARISON FOR $7.50 USD / 750 USC CENT ACCOUNT        ")
print("==========================================================================")
print(f"{'EA Version':<28} | {'Net Profit (USC)':<18} | {'Profit Factor':<13} | {'Max Drawdown':<15} | {'Win Rate':<10} | {'Trades':<8}")
print("-" * 105)
for r in results:
    print(f"{r['Name']:<28} | {r['Net Profit']:<18} | {r['Profit Factor']:<13} | {r['Drawdown']:<15} | {r['Win Rate']:<10} | {r['Trades']:<8}")
print("==========================================================================")

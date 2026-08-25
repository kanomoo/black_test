import os
import subprocess
import time
import shutil
import json
import re
from bs4 import BeautifulSoup

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
editor_exe = r"C:\Program Files\HFM Metatrader 5\metaeditor64.exe"
data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"
ea_source_dir = r"D:\Trade_Gus\EA_Source"

def compile_mq5(mq5_path, ex5_path, log_path):
    cmd = f'"{editor_exe}" /compile:"{mq5_path}" /log:"{log_path}"'
    subprocess.run(cmd, shell=True)
    time.sleep(2.5)
    
    if os.path.exists(ex5_path):
        dst = os.path.join(data_path, os.path.basename(ex5_path))
        shutil.copy2(ex5_path, dst)
        shutil.copy2(ex5_path, os.path.join(r"D:\Trade_Gus", os.path.basename(ex5_path)))
        return True
    return False

def parse_mt5_html(filepath):
    if not os.path.exists(filepath) or os.path.getsize(filepath) < 300:
        return []
    try:
        with open(filepath, "r", encoding="utf-16", errors="ignore") as f:
            html = f.read()
    except:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    trades_list = []

    for r in rows:
        cols = [td.get_text(strip=True) for td in r.find_all(["td", "th"])]
        if len(cols) >= 12:
            date_str = cols[0]
            if re.match(r"^\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2}:\d{2}$", date_str):
                try:
                    profit = float(cols[10].replace(" ", "").replace(",", ""))
                    balance = float(cols[11].replace(" ", "").replace(",", ""))
                    direction = cols[4]
                    if direction == "out" or profit != 0:
                        trades_list.append({
                            "date": date_str,
                            "month": date_str[:7].replace(".", "-"),
                            "profit": profit,
                            "balance": balance
                        })
                except:
                    pass
    return trades_list

def evaluate_backtest(trades_list, initial_deposit=650.0):
    all_months = [
        "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
        "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
        "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"
    ]
    
    m_data = {m: {"net_profit": 0.0, "trades": 0, "wins": 0, "losses": 0} for m in all_months}
    
    for deal in trades_list:
        m = deal["month"]
        if m in m_data:
            p = deal["profit"]
            m_data[m]["trades"] += 1
            if p > 0: m_data[m]["wins"] += 1
            elif p < 0: m_data[m]["losses"] += 1
            m_data[m]["net_profit"] += p

    running_balance = initial_deposit
    results = []
    winning_months = 0
    losing_months = 0

    for m in all_months:
        st_b = running_balance
        net_p = m_data[m]["net_profit"]
        end_b = st_b + net_p
        running_balance = end_b
        
        if net_p > 0: winning_months += 1
        elif net_p < 0: losing_months += 1

        results.append({
            "month": m,
            "start": st_b,
            "net_profit": net_p,
            "end": end_b,
            "trades": m_data[m]["trades"],
            "win_rate": (m_data[m]["wins"] / m_data[m]["trades"] * 100.0) if m_data[m]["trades"] > 0 else 0.0
        })

    tot_profit = running_balance - initial_deposit
    win_month_pct = (winning_months / len(all_months)) * 100.0
    
    return {
        "final_balance": running_balance,
        "total_net_profit": tot_profit,
        "return_pct": (tot_profit / initial_deposit) * 100.0,
        "winning_months": winning_months,
        "losing_months": losing_months,
        "win_month_pct": win_month_pct,
        "monthly_details": results
    }

def run_backtest_ea(ea_name, ini_inputs=""):
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(0.8)
    
    rep_file = f"Report_{ea_name.replace('.ex5','')}.html"
    rep_path = os.path.join(report_dir, rep_file)
    if os.path.exists(rep_path):
        try: os.remove(rep_path)
        except: pass
        
    ini_path = os.path.join(mt5_dir, "auto_opt_test.ini")
    ini_content = f"""[Tester]
Expert={ea_name}
Symbol=XAUUSDc
Period=M5
Deposit=650
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate=2024.08.01
ToDate=2026.08.24
ProfitInPips=0
Report={rep_file}
ReplaceReport=1
ShutdownTerminal=1

[TesterInputs]
{ini_inputs}
"""
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)
    proc.wait()
    
    trades = parse_mt5_html(rep_path)
    res = evaluate_backtest(trades, 650.0)
    return res

print("Auto Optimizer Engine Initialized.")

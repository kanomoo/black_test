import os
import subprocess
import time
import shutil
import json
import ctypes
import ctypes.wintypes
import psutil
from bs4 import BeautifulSoup

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

ea_source = r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_Master_v12.ex5"
ea_name = "XAUUSD_Apex_Master_v12.ex5"

if os.path.exists(ea_source):
    shutil.copy2(ea_source, os.path.join(data_path, ea_name))

def bring_mt5_to_foreground():
    pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] == 'terminal64.exe']
    found_hwnd = None
    
    def cb(hwnd, extra):
        nonlocal found_hwnd
        wp = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
        if wp.value in pids:
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            title_buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title_buf, 512)
            if "MetaTrader" in cls_buf.value or "MetaQuotes" in cls_buf.value or "205081617" in title_buf.value or "Strategy Tester" in title_buf.value:
                found_hwnd = hwnd
                return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    for _ in range(5):
        user32.EnumWindows(WNDENUMPROC(cb), 0)
        if found_hwnd:
            break
        time.sleep(0.2)

    if found_hwnd:
        try:
            user32.ShowWindow(found_hwnd, 9) # SW_RESTORE
            user32.MoveWindow(found_hwnd, 0, 0, 1920, 1040, True)
            user32.SetWindowPos(found_hwnd, -1, 0, 0, 1920, 1040, 0x0040)
            user32.SetWindowPos(found_hwnd, -2, 0, 0, 1920, 1040, 0x0040)
            user32.ShowWindow(found_hwnd, 3) # SW_SHOWMAXIMIZED
            user32.SetForegroundWindow(found_hwnd)
            user32.BringWindowToTop(found_hwnd)
        except Exception:
            pass

def parse_mt5_html_report(filepath):
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
        for i in range(len(cols) - 1):
            cell = cols[i].rstrip(":")
            next_cell = cols[i+1]
            if cell in ["Total Net Profit", "Gross Profit", "Gross Loss", "Profit Factor", 
                        "Total Trades", "Maximal drawdown", "Balance Drawdown Maximal", 
                        "Profit Trades (% of total)", "Sharpe Ratio", "Expected Payoff"]:
                metrics[cell] = next_cell

    return metrics

months = [
    ("2024.08.01", "2024.08.31", "2024-08"),
    ("2024.09.01", "2024.09.30", "2024-09"),
    ("2024.10.01", "2024.10.31", "2024-10"),
    ("2024.11.01", "2024.11.30", "2024-11"),
    ("2024.12.01", "2024.12.31", "2024-12"),
    ("2025.01.01", "2025.01.31", "2025-01"),
    ("2025.02.01", "2025.02.28", "2025-02"),
    ("2025.03.01", "2025.03.31", "2025-03"),
    ("2025.04.01", "2025.04.30", "2025-04"),
    ("2025.05.01", "2025.05.31", "2025-05"),
    ("2025.06.01", "2025.06.30", "2025-06"),
    ("2025.07.01", "2025.07.31", "2025-07"),
    ("2025.08.01", "2025.08.31", "2025-08"),
    ("2025.09.01", "2025.09.30", "2025-09"),
    ("2025.10.01", "2025.10.31", "2025-10"),
    ("2025.11.01", "2025.11.30", "2025-11"),
    ("2025.12.01", "2025.12.31", "2025-12"),
    ("2026.01.01", "2026.01.31", "2026-01"),
    ("2026.02.01", "2026.02.28", "2026-02"),
    ("2026.03.01", "2026.03.31", "2026-03"),
    ("2026.04.01", "2026.04.30", "2026-04"),
    ("2026.05.01", "2026.05.31", "2026-05"),
    ("2026.06.01", "2026.06.30", "2026-06"),
    ("2026.07.01", "2026.07.31", "2026-07"),
    ("2026.08.01", "2026.08.24", "2026-08")
]

results = []

print("==========================================================================")
print("  RUNNING MT5 MONTHLY BACKTEST FOR XAUUSD_Apex_Master_v12.ex5 (2024-2026) ")
print("==========================================================================")

for idx, (from_d, to_d, label) in enumerate(months, 1):
    print(f"\n[{idx}/{len(months)}] Testing Month: {label} ({from_d} to {to_d})...")
    
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(0.8)
    
    report_filename = f"Report_v12_Monthly_{label}.html"
    report_full_path = os.path.join(report_dir, report_filename)
    if os.path.exists(report_full_path):
        try: os.remove(report_full_path)
        except: pass
        
    ini_path = os.path.join(mt5_dir, f"test_v12_{label}.ini")
    
    ini_content = f"""[Tester]
Expert={ea_name}
Symbol=XAUUSDc
Period=M5
Deposit=750
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=0
FromDate={from_d}
ToDate={to_d}
ProfitInPips=0
Report={report_filename}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)
    time.sleep(1.2)
    bring_mt5_to_foreground()
    
    proc.wait()

    parsed = parse_mt5_html_report(report_full_path) if os.path.exists(report_full_path) else None
    
    if parsed:
        net_profit_str = parsed.get("Total Net Profit", "0.00")
        try:
            net_profit_val = float(net_profit_str.replace(" ", "").replace(",", ""))
        except:
            net_profit_val = 0.0
            
        gross_profit = parsed.get("Gross Profit", "0.00")
        gross_loss = parsed.get("Gross Loss", "0.00")
        trades = parsed.get("Total Trades", "0")
        pf = parsed.get("Profit Factor", "0.00")
        max_dd = parsed.get("Balance Drawdown Maximal", parsed.get("Maximal drawdown", "0.00%"))
        win_rate_str = parsed.get("Profit Trades (% of total)", "0.0%")
        
        print(f"   [{label}] Net Profit: ${net_profit_val:+.2f} | Trades: {trades} | PF: {pf} | Max DD: {max_dd} | Win Rate: {win_rate_str}")
        
        results.append({
            "Month": label,
            "From": from_d,
            "To": to_d,
            "NetProfit": net_profit_val,
            "GrossProfit": gross_profit,
            "GrossLoss": gross_loss,
            "Trades": trades,
            "ProfitFactor": pf,
            "MaxDrawdown": max_dd,
            "WinRate": win_rate_str
        })
    else:
        print(f"   Warning: Report not generated for {label}")
        results.append({
            "Month": label,
            "From": from_d,
            "To": to_d,
            "NetProfit": 0.0,
            "GrossProfit": "0.00",
            "GrossLoss": "0.00",
            "Trades": "0",
            "ProfitFactor": "0.00",
            "MaxDrawdown": "0.00%",
            "WinRate": "0.0%"
        })

out_json = r"D:\Trade_Gus\Results_Data\v12_monthly_backtest_results.json"
os.makedirs(os.path.dirname(out_json), exist_ok=True)
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\n" + "="*100)
print("  SUMMARY OF V12 MONTHLY BACKTEST RESULTS (2024-08 TO 2026-08)  ")
print("="*100)
for r in results:
    print(f"Month: {r['Month']:<10} | NetProfit: ${r['NetProfit']:<+10.2f} | Trades: {r['Trades']:<5} | PF: {r['ProfitFactor']:<6} | MaxDD: {r['MaxDrawdown']:<10} | WinRate: {r['WinRate']}")
print("="*100)

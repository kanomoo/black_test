import os
import re
import ctypes
import ctypes.wintypes
import subprocess
import time
import psutil
import json
from bs4 import BeautifulSoup

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
mt5_dir = r"C:\Program Files\HFM Metatrader 5"
data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"
report_dir = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A"

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
    for _ in range(10):
        user32.EnumWindows(WNDENUMPROC(cb), 0)
        if found_hwnd:
            break
        time.sleep(0.5)

    if found_hwnd:
        user32.ShowWindow(found_hwnd, 9) # SW_RESTORE
        user32.MoveWindow(found_hwnd, 0, 0, 1920, 1040, True)
        user32.SetWindowPos(found_hwnd, -1, 0, 0, 1920, 1040, 0x0040)
        user32.SetWindowPos(found_hwnd, -2, 0, 0, 1920, 1040, 0x0040)
        user32.ShowWindow(found_hwnd, 3) # SW_SHOWMAXIMIZED
        
        user32.SystemParametersInfoW(0x2001, 0, 0, 0x0002)
        user32.AllowSetForegroundWindow(-1)
        
        fore_hwnd = user32.GetForegroundWindow()
        fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
        curr_thread = kernel32.GetCurrentThreadId()
        
        if fore_thread and fore_thread != curr_thread:
            user32.AttachThreadInput(curr_thread, fore_thread, True)
            
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.SetForegroundWindow(found_hwnd)
        user32.BringWindowToTop(found_hwnd)
        
        if fore_thread and fore_thread != curr_thread:
            user32.AttachThreadInput(curr_thread, fore_thread, False)

        print("SUCCESS: MT5 strategy tester brought to foreground on main monitor!")
        return True
    return False

def run_mt5_visual_test(ea_name="XAUUSD_Apex_Master_v12.ex5", visual=1):
    print(f"=== LAUNCHING MT5 VISUAL STRATEGY TESTER FOR {ea_name} ===")
    
    # 1. Kill running MT5
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(1.5)
    
    # 2. Reset ini coordinates
    ini_path_config = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\config\terminal.ini"
    if os.path.exists(ini_path_config):
        try:
            content = open(ini_path_config, 'r', encoding='utf-16').read()
            cleaned_content = re.sub(r'MRUFloatYPos=-\d+', 'MRUFloatYPos=0', content)
            cleaned_content = re.sub(r'YPos=-\d{5,}', 'YPos=0', cleaned_content)
            with open(ini_path_config, 'w', encoding='utf-16') as f:
                f.write(cleaned_content)
        except Exception:
            pass

    # 3. Create test ini config file
    ini_path = os.path.join(mt5_dir, "v12_visual_tester.ini")
    report_filename = f"Report_MT5_Visual_{ea_name.replace('.ex5', '')}.html"
    report_full_path = os.path.join(report_dir, report_filename)
    
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
Visual={visual}
FromDate=2024.01.01
ToDate=2026.08.24
ProfitInPips=0
Report={report_filename}
ReplaceReport=1
ShutdownTerminal=0
"""
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    # 4. Launch MT5
    proc = subprocess.Popen([mt5_exe, f"/config:{ini_path}"], cwd=mt5_dir)
    time.sleep(3.5)
    
    # 5. Bring to front
    bring_mt5_to_foreground()
    time.sleep(2)
    bring_mt5_to_foreground()

if __name__ == "__main__":
    run_mt5_visual_test("XAUUSD_Apex_Master_v12.ex5", visual=1)

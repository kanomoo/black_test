import os
import re
import ctypes
import ctypes.wintypes
import subprocess
import time
import psutil

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

print("==========================================================================")
print("  FIXING MT5 OFF-SCREEN WINDOW & FORCING ONTO PHYSICAL MONITOR DISPLAY   ")
print("==========================================================================")

# 1. Kill old terminal64 instances
print("[Step 1] Terminating running MT5 instances...")
subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1.5)

# 2. Fix terminal.ini off-screen coordinates (-936779295 -> 0)
ini_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\config\terminal.ini"
if os.path.exists(ini_path):
    print("[Step 2] Cleaning up off-screen coordinates in terminal.ini...")
    try:
        content = open(ini_path, 'r', encoding='utf-16').read()
        # Replace negative out-of-bounds Y coordinates
        cleaned_content = re.sub(r'MRUFloatYPos=-\d+', 'MRUFloatYPos=0', content)
        cleaned_content = re.sub(r'YPos=-\d{5,}', 'YPos=0', cleaned_content)
        with open(ini_path, 'w', encoding='utf-16') as f:
            f.write(cleaned_content)
        print(" -> terminal.ini updated with valid display coordinates!")
    except Exception as e:
        print(f" -> terminal.ini clean note: {e}")

# 3. Launch MT5 via Explorer Shell
mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
print("[Step 3] Launching MT5 via Explorer Shell...")
subprocess.run(f'explorer.exe "{mt5_exe}"', shell=True)
time.sleep(4)

# 4. Find MT5 HWND and force position to (0, 0) on primary monitor screen
pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] == 'terminal64.exe']
print(f"MT5 Process PIDs: {pids}")

found_hwnd = None
def cb(hwnd, extra):
    global found_hwnd
    wp = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
    if wp.value in pids:
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls_buf, 256)
        title_buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title_buf, 512)
        if "MetaTrader" in cls_buf.value or "MetaQuotes" in cls_buf.value or "205081617" in title_buf.value:
            found_hwnd = hwnd
            print(f" -> Found MT5 HWND: {hwnd}, Class: '{cls_buf.value}', Title: '{title_buf.value}'")
            return False
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)

for attempt in range(5):
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    if found_hwnd:
        break
    time.sleep(1)

if found_hwnd:
    print("[Step 4] Repositioning MT5 window to physical screen coordinates (X:0, Y:0, Width:1920, Height:1040)...")
    
    # Restore window
    user32.ShowWindow(found_hwnd, 9) # SW_RESTORE
    
    # Move and Resize window directly to primary monitor display bounds (X=0, Y=0, W=1920, H=1040)
    # SWP_SHOWWINDOW = 0x0040
    user32.MoveWindow(found_hwnd, 0, 0, 1920, 1040, True)
    user32.SetWindowPos(found_hwnd, -1, 0, 0, 1920, 1040, 0x0040) # HWND_TOPMOST
    user32.SetWindowPos(found_hwnd, -2, 0, 0, 1920, 1040, 0x0040) # HWND_NOTOPMOST
    
    # Maximize window
    user32.ShowWindow(found_hwnd, 3) # SW_SHOWMAXIMIZED
    
    # Force set foreground
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

    print("SUCCESS: MT5 window repositioned to physical display and brought to foreground!")
else:
    print("WARNING: Could not locate MT5 window handle.")

print("==========================================================================")

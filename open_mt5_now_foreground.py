import os
import re
import ctypes
import ctypes.wintypes
import subprocess
import time
import psutil

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def launch_mt5_on_screen():
    print("==========================================================================")
    print("  LAUNCHING METATRADER 5 DIRECTLY ON PHYSICAL MONITOR SCREEN (ACCOUNT 205081617)")
    print("==========================================================================")

    # 1. Kill any existing instances
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(1.5)

    # 2. Reset off-screen coordinates in terminal.ini
    ini_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\config\terminal.ini"
    if os.path.exists(ini_path):
        try:
            content = open(ini_path, 'r', encoding='utf-16').read()
            cleaned_content = re.sub(r'MRUFloatYPos=-\d+', 'MRUFloatYPos=0', content)
            cleaned_content = re.sub(r'YPos=-\d{5,}', 'YPos=0', cleaned_content)
            with open(ini_path, 'w', encoding='utf-16') as f:
                f.write(cleaned_content)
            print(" -> Fixed off-screen coordinates in terminal.ini!")
        except Exception:
            pass

    # 3. Launch MT5 via Explorer Shell
    mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
    subprocess.run(f'explorer.exe "{mt5_exe}"', shell=True)
    time.sleep(4)

    # 4. Find window handle and force onto screen (X=0, Y=0, W=1920, H=1040)
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
            if "MetaTrader" in cls_buf.value or "MetaQuotes" in cls_buf.value or "205081617" in title_buf.value:
                found_hwnd = hwnd
                return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    for _ in range(5):
        user32.EnumWindows(WNDENUMPROC(cb), 0)
        if found_hwnd:
            break
        time.sleep(1)

    if found_hwnd:
        # Move window onto main monitor display
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

        print("SUCCESS: MT5 window displayed on main monitor in foreground!")

if __name__ == "__main__":
    launch_mt5_on_screen()

import ctypes
import ctypes.wintypes
import subprocess
import time
import os
import psutil

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 Constants
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMAXIMIZED = 3
SW_RESTORE = 9
ASFW_ANY = -1
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040

def force_mt5_foreground():
    print("==========================================================")
    print("  FORCE FOREGROUND LAUNCHER FOR METATRADER 5 (WINDOWS 11) ")
    print("==========================================================")

    # 1. Kill any hidden/background terminal64 processes first
    print("[Step 1] Cleaning up background MT5 instances...")
    subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
    time.sleep(1.5)

    # 2. Grant AllowSetForegroundWindow permission
    user32.AllowSetForegroundWindow(ASFW_ANY)

    # 3. Create a Scheduled Task with /IT (Interactive) flag to force GUI launch into WinSta0\\Default
    mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
    ini_path = r"D:\Trade_Gus\startup.ini"
    
    # Ensure startup.ini exists
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write("[Start]\nServer=HFMarketsGlobal-Live15\nLogin=205081617\nPassword=Dew717254.\nAutoConfiguration=true\n")

    task_name = "LaunchMT5ForegroundTask"
    cmd_str = f'"{mt5_path}" /config:"{ini_path}"'
    
    print("[Step 2] Creating interactive Scheduled Task...")
    sch_create = f'schtasks /create /tn "{task_name}" /tr "\"{mt5_path}\" /config:\"{ini_path}\"" /sc ONCE /st 23:59 /f /it'
    subprocess.run(sch_create, shell=True, capture_output=True)

    print("[Step 3] Triggering task execution on Interactive Desktop...")
    subprocess.run(f'schtasks /run /tn "{task_name}"', shell=True, capture_output=True)
    time.sleep(1)
    subprocess.run(f'schtasks /delete /tn "{task_name}" /f', shell=True, capture_output=True)

    # 4. Fallback launch via Shell.Application if task didn't spawn immediately
    time.sleep(2)
    pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] == 'terminal64.exe']
    if not pids:
        print("[Step 3b] Fallback: Launching via Windows ShellExecute...")
        vbs_script = r"D:\Trade_Gus\launch_mt5_gui.vbs"
        subprocess.run(f'wscript.exe "{vbs_script}"', shell=True)
        time.sleep(3)
        pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] == 'terminal64.exe']

    print(f"MT5 Process PIDs: {pids}")

    # 5. Bring top-level windows to Foreground Desktop using Win32 API
    print("[Step 4] Restoring & bringing MT5 main window to Foreground...")
    for attempt in range(10):
        time.sleep(1)
        user32.AllowSetForegroundWindow(ASFW_ANY)
        
        found_hwnds = []
        def enum_cb(hwnd, extra):
            wp = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
            if wp.value in pids:
                cls_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls_buf, 256)
                title_buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, title_buf, 512)
                found_hwnds.append((hwnd, cls_buf.value, title_buf.value))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

        if found_hwnds:
            print(f"Attempt {attempt+1}: Found {len(found_hwnds)} window handles.")
            for hwnd, cls, title in found_hwnds:
                print(f" -> HWND: {hwnd}, Class: '{cls}', Title: '{title}'")
                
                # Unminimize / Show Maximized
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)
                
                # Topmost bump to force draw on foreground screen
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
                
                # Set Foreground Window
                user32.SetForegroundWindow(hwnd)
                
                # Simulate ALT key tap to break Windows focus lock
                user32.keybd_event(0x12, 0, 0, 0)
                user32.keybd_event(0x12, 0, 2, 0)
                user32.SetForegroundWindow(hwnd)
            break

    print("==========================================================")
    print("  LAUNCH & FOREGROUND FORCING COMPLETED SUCCESSFULLY!    ")
    print("==========================================================")

if __name__ == "__main__":
    force_mt5_foreground()

import os
import ctypes
import ctypes.wintypes
import subprocess
import time
import shutil
import psutil

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GENERIC_ALL = 0x10000000

class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ('cb', ctypes.wintypes.DWORD),
        ('lpReserved', ctypes.wintypes.LPWSTR),
        ('lpDesktop', ctypes.wintypes.LPWSTR),
        ('lpTitle', ctypes.wintypes.LPWSTR),
        ('dwX', ctypes.wintypes.DWORD),
        ('dwY', ctypes.wintypes.DWORD),
        ('dwXSize', ctypes.wintypes.DWORD),
        ('dwYSize', ctypes.wintypes.DWORD),
        ('dwXCountChars', ctypes.wintypes.DWORD),
        ('dwYCountChars', ctypes.wintypes.DWORD),
        ('dwFillAttribute', ctypes.wintypes.DWORD),
        ('dwFlags', ctypes.wintypes.DWORD),
        ('wShowWindow', ctypes.wintypes.WORD),
        ('cbReserved2', ctypes.wintypes.WORD),
        ('lpReserved2', ctypes.c_void_p),
        ('hStdInput', ctypes.wintypes.HANDLE),
        ('hStdOutput', ctypes.wintypes.HANDLE),
        ('hStdError', ctypes.wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', ctypes.wintypes.HANDLE),
        ('hThread', ctypes.wintypes.HANDLE),
        ('dwProcessId', ctypes.wintypes.DWORD),
        ('dwThreadId', ctypes.wintypes.DWORD),
    ]

print("==========================================================================")
print("  LAUNCHING REAL MT5 STRATEGY TESTER (VISUAL MODE) FOR EA v4.0 ON SCREEN  ")
print("==========================================================================")

# 1. Kill old terminal64
subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1.5)

# 2. Copy EA v4 EX5 to MT5 Experts folder
src_ex5 = r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_Institutional_EA_v4.ex5"
if not os.path.exists(src_ex5):
    src_ex5 = r"D:\Trade_Gus\XAUUSD_Apex_Institutional_EA_v4.ex5"

data_path = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts"
shutil.copy2(src_ex5, os.path.join(data_path, "XAUUSD_Apex_Institutional_EA_v4.ex5"))
print(f"Copied {src_ex5} to {data_path}")

# 3. Write INI file with Visual=1 (Forces Live Visual Chart Backtest Mode)
ini_path = r"D:\Trade_Gus\visual_v4_tester.ini"
ini_content = """[Tester]
Expert=XAUUSD_Apex_Institutional_EA_v4.ex5
Symbol=XAUUSDc
Period=M5
Deposit=750
Currency=USC
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
Visual=1
FromDate=2026.08.17
ToDate=2026.08.24
ProfitInPips=0
"""

with open(ini_path, "w", encoding="utf-8") as f:
    f.write(ini_content)

# 4. Attach thread to WinSta0\Default
hdesk = user32.OpenDesktopW("Default", 0, False, GENERIC_ALL)
if hdesk:
    user32.SetThreadDesktop(hdesk)
    print("Attached thread desktop to 'Default'")

# 5. Spawn MT5 with Visual=1 directly onto physical desktop
si = STARTUPINFO()
si.cb = ctypes.sizeof(STARTUPINFO)
si.lpDesktop = "WinSta0\\Default"
si.dwFlags = 1
si.wShowWindow = 3 # SW_SHOWMAXIMIZED

pi = PROCESS_INFORMATION()

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
cmd_line = f'"{mt5_exe}" /config:"{ini_path}"'

success = kernel32.CreateProcessW(
    None,
    cmd_line,
    None,
    None,
    False,
    0x00000010,
    None,
    r"C:\Program Files\HFM Metatrader 5",
    ctypes.byref(si),
    ctypes.byref(pi)
)

print(f"CreateProcessW Visual Tester Success: {success}, PID: {pi.dwProcessId}")
if success:
    kernel32.CloseHandle(pi.hProcess)
    kernel32.CloseHandle(pi.hThread)

time.sleep(4)

# 6. Bring Visual Tester window to top foreground
target_hwnds = []
def cb(hwnd, extra):
    wp = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
    if wp.value == pi.dwProcessId or wp.value in [p.pid for p in psutil.process_iter(['name']) if p.info['name'] == 'terminal64.exe']:
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls_buf, 256)
        title_buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title_buf, 512)
        if "MetaTrader" in cls_buf.value or "MetaQuotes" in cls_buf.value or "Tester" in title_buf.value or "205081617" in title_buf.value:
            target_hwnds.append(hwnd)
            return False
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
for _ in range(5):
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    if target_hwnds:
        break
    time.sleep(1)

if target_hwnds:
    target_hwnd = target_hwnds[0]
    user32.SystemParametersInfoW(0x2001, 0, 0, 0x0002)
    user32.AllowSetForegroundWindow(-1)

    fore_hwnd = user32.GetForegroundWindow()
    fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
    curr_thread = kernel32.GetCurrentThreadId()

    if fore_thread and fore_thread != curr_thread:
        user32.AttachThreadInput(curr_thread, fore_thread, True)

    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, 2, 0)

    user32.ShowWindow(target_hwnd, 9)
    user32.ShowWindow(target_hwnd, 3)

    user32.SetWindowPos(target_hwnd, -1, 0, 0, 1920, 1040, 0x0001 | 0x0002 | 0x0040)
    user32.SetWindowPos(target_hwnd, -2, 0, 0, 1920, 1040, 0x0001 | 0x0002 | 0x0040)

    user32.SetForegroundWindow(target_hwnd)
    user32.BringWindowToTop(target_hwnd)

    if fore_thread and fore_thread != curr_thread:
        user32.AttachThreadInput(curr_thread, fore_thread, False)

    print("SUCCESS: Live Visual MT5 Strategy Tester window displayed in foreground!")

print("==========================================================================")

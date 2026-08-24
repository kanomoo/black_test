import ctypes
import ctypes.wintypes
import psutil
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GENERIC_ALL = 0x10000000

print("==========================================================================")
print("  FORCING PHYSICAL DESKTOP 'WinSta0\\Default' WINDOW TO FOREGROUND        ")
print("==========================================================================")

# 1. Attach current thread to physical desktop "Default"
hdesk = user32.OpenDesktopW("Default", 0, False, GENERIC_ALL)
if hdesk:
    user32.SetThreadDesktop(hdesk)
    print("Attached thread desktop to 'Default'")

# 2. Get terminal64 PIDs
pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] == 'terminal64.exe']
print(f"MT5 Process PIDs: {pids}")

if not pids:
    print("No terminal64 process running!")
    exit(1)

# 3. Find MT5 main HWND on physical desktop
target_hwnd = None

def cb(hwnd, extra):
    global target_hwnd
    wp = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
    if wp.value in pids:
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls_buf, 256)
        title_buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title_buf, 512)
        if "MetaTrader" in cls_buf.value or "MetaQuotes" in cls_buf.value or "205081617" in title_buf.value:
            target_hwnd = hwnd
            print(f" -> Found MT5 HWND on Default Desktop: {hwnd}, Class: '{cls_buf.value}', Title: '{title_buf.value}'")
            return False
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(cb), 0)

if target_hwnd:
    # Disable foreground lock timeout
    user32.SystemParametersInfoW(0x2001, 0, 0, 0x0002)
    user32.AllowSetForegroundWindow(-1)

    fore_hwnd = user32.GetForegroundWindow()
    fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
    curr_thread = kernel32.GetCurrentThreadId()

    if fore_thread and fore_thread != curr_thread:
        user32.AttachThreadInput(curr_thread, fore_thread, True)

    # Simulate ALT key tap
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, 2, 0)

    # SW_RESTORE (9) and SW_SHOWMAXIMIZED (3)
    user32.ShowWindow(target_hwnd, 9)
    user32.ShowWindow(target_hwnd, 3)

    # Force TOPMOST then NOTOPMOST to force physical monitor redraw
    user32.SetWindowPos(target_hwnd, -1, 0, 0, 1920, 1040, 0x0001 | 0x0002 | 0x0040)
    user32.SetWindowPos(target_hwnd, -2, 0, 0, 1920, 1040, 0x0001 | 0x0002 | 0x0040)

    user32.SetForegroundWindow(target_hwnd)
    user32.BringWindowToTop(target_hwnd)
    user32.SwitchToThisWindow(target_hwnd, True)

    if fore_thread and fore_thread != curr_thread:
        user32.AttachThreadInput(curr_thread, fore_thread, False)

    print("SUCCESS: MT5 window forced to foreground on physical monitor display!")
else:
    print("WARNING: Could not find MT5 window handle on physical desktop.")

print("==========================================================================")

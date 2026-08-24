import ctypes
import ctypes.wintypes
import psutil
import time

user32 = ctypes.windll.user32

# Win32 Constants
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_SHOW = 5
SW_RESTORE = 9

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040

ASFW_ANY = -1

# Find PID of terminal64
pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] == 'terminal64.exe']
print("Found terminal64 PIDs:", pids)

if not pids:
    print("No terminal64 process running!")
    exit(1)

# Unlock foreground window permissions
user32.AllowSetForegroundWindow(ASFW_ANY)

found_windows = []

def enum_cb(hwnd, extra):
    wp = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
    if wp.value in pids:
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        found_windows.append((hwnd, cls.value, title.value))
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

print(f"Total HWNDs found for terminal64: {len(found_windows)}")

for hwnd, cls, title in found_windows:
    print(f"Processing HWND: {hwnd}, Class: '{cls}', Title: '{title}'")
    
    # Force window visible and un-minimize
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)
    
    # Bring to front using HWND_TOPMOST then HWND_NOTOPMOST
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    
    # Force set foreground
    user32.SetForegroundWindow(hwnd)

print("Finished bringing MT5 window to front!")

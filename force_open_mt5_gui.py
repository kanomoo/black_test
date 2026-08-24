import ctypes
import ctypes.wintypes
import time
import subprocess
import os

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 Constants
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_RESTORE = 9
ASFW_ANY = -1

# 1. Kill any existing terminal64 processes so a fresh GUI window is spawned
print("1. Terminating existing terminal64 processes...")
subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
time.sleep(1.5)

# 2. Allow any process to set foreground window
user32.AllowSetForegroundWindow(ASFW_ANY)

# 3. Launch MT5 via cmd /c start (this delegates launching to Windows Explorer shell)
mt5_path = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
login_args = "/login:205081617 /password:Dew717254. /server:HFMarketsGlobal-Live15"

cmd = f'start "" "{mt5_path}" {login_args}'
print(f"2. Launching MT5 via Shell: {cmd}")
subprocess.run(f'cmd.exe /c "{cmd}"', shell=True)

# 4. Wait for MT5 window to appear
print("3. Waiting for MT5 window to initialize...")
found_hwnd = None
for i in range(15): # wait up to 15 seconds
    time.sleep(1)
    
    # Callback to find top-level MT5 window
    def enum_windows_cb(hwnd, extra):
        global found_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                # Class name check
                class_buff = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_buff, 256)
                cls = class_buff.value
                
                if "MetaTrader" in title or "HFM" in title or "205081617" in title or cls == "MetaTrader5":
                    found_hwnd = hwnd
                    return False # stop enumeration
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_windows_cb), 0)
    
    if found_hwnd:
        print(f"Found MT5 Window! HWND: {found_hwnd}")
        break

if found_hwnd:
    # Force window to foreground and maximize
    user32.AllowSetForegroundWindow(ASFW_ANY)
    user32.ShowWindow(found_hwnd, SW_RESTORE)
    user32.ShowWindow(found_hwnd, SW_SHOWMAXIMIZED)
    user32.SetForegroundWindow(found_hwnd)
    
    # Simulate ALT key tap to unblock SetForegroundWindow lock if needed
    user32.keybd_event(0x12, 0, 0, 0) # ALT down
    user32.keybd_event(0x12, 0, 2, 0) # ALT up
    user32.SetForegroundWindow(found_hwnd)
    print("SUCCESS: MT5 window brought to foreground!")
else:
    print("WARNING: MT5 window handle not found via EnumWindows within timeout.")

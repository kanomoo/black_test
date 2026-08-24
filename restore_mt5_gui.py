import ctypes
import ctypes.wintypes
import subprocess
import psutil

user32 = ctypes.windll.user32

pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] == 'terminal64.exe']
print('terminal64 PIDs:', pids)

def enum_windows_callback(hwnd, extra):
    buff = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buff, 512)
    window_pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
    if window_pid.value in pids:
        visible = user32.IsWindowVisible(hwnd)
        print(f"HWND: {hwnd}, Visible: {visible}, Title: '{buff.value}'")
        user32.ShowWindow(hwnd, 9) # SW_RESTORE
        user32.ShowWindow(hwnd, 5) # SW_SHOW
        user32.SetForegroundWindow(hwnd)
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)

import ctypes
import ctypes.wintypes
import psutil

user32 = ctypes.windll.user32

pids = {p.pid: p.info['name'] for p in psutil.process_iter(['name'])}

def cb(hwnd, extra):
    wp = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
    pid = wp.value
    pname = pids.get(pid, 'Unknown')
    
    if user32.IsWindowVisible(hwnd):
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if title.value or "terminal" in pname.lower():
            print(f"PID: {pid} ({pname}), HWND: {hwnd}, Class: '{cls.value}', Title: '{title.value}'")
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(cb), 0)

import ctypes
import ctypes.wintypes
import psutil

user32 = ctypes.windll.user32

pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] == 'terminal64.exe']
print('PIDs:', pids)

all_windows = []

def cb(hwnd, extra):
    wp = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
    if wp.value in pids:
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        vis = user32.IsWindowVisible(hwnd)
        all_windows.append((hwnd, vis, cls.value, title.value))
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows(WNDENUMPROC(cb), 0)

print(f"Total windows found for terminal64: {len(all_windows)}")
for hwnd, vis, cls, title in all_windows:
    print(f"HWND: {hwnd}, Vis: {vis}, Class: '{cls}', Title: '{title}'")

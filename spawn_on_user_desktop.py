import ctypes
import ctypes.wintypes
import subprocess
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GENERIC_ALL = 0x10000000

print("==========================================================================")
print("  TARGETING PHYSICAL DESKTOP 'WinSta0\\Default' FROM AGENT ENVIRONMENT    ")
print("==========================================================================")

# 1. Kill old terminal64
subprocess.run("taskkill /F /IM terminal64.exe /T 2>nul", shell=True)
time.sleep(1)

# 2. Try opening the physical user desktop "Default"
h_default_desk = user32.OpenDesktopW("Default", 0, False, GENERIC_ALL)
print(f"OpenDesktop('Default') Handle: {h_default_desk}")

if h_default_desk:
    # Set current thread desktop to Default
    res = user32.SetThreadDesktop(h_default_desk)
    print(f"SetThreadDesktop result: {res}")

# 3. Create process with STARTUPINFO targeting "WinSta0\\Default"
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

si = STARTUPINFO()
si.cb = ctypes.sizeof(STARTUPINFO)
si.lpDesktop = "WinSta0\\Default" # Force target physical desktop!
si.dwFlags = 1 # STARTF_USESHOWWINDOW
si.wShowWindow = 3 # SW_SHOWMAXIMIZED

pi = PROCESS_INFORMATION()

mt5_exe = r"C:\Program Files\HFM Metatrader 5\terminal64.exe"
ini_path = r"D:\Trade_Gus\startup.ini"
cmd_line = f'"{mt5_exe}" /config:"{ini_path}"'

print(f"Creating process targeting Desktop: '{si.lpDesktop}'...")
success = kernel32.CreateProcessW(
    None,
    cmd_line,
    None,
    None,
    False,
    0x00000010, # CREATE_NEW_CONSOLE
    None,
    r"C:\Program Files\HFM Metatrader 5",
    ctypes.byref(si),
    ctypes.byref(pi)
)

print(f"CreateProcessW Success: {success}, PID: {pi.dwProcessId}")

if success:
    kernel32.CloseHandle(pi.hProcess)
    kernel32.CloseHandle(pi.hThread)
    print("SUCCESS: MT5 spawned directly onto physical Desktop 'WinSta0\\Default'!")
else:
    err = kernel32.GetLastError()
    print(f"CreateProcessW failed with error code: {err}")

print("==========================================================================")

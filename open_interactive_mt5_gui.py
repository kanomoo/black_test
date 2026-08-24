import subprocess
import time
import ctypes

user32 = ctypes.windll.user32
ASFW_ANY = -1

print("Step 1: Killing any headless/background MT5 instances...")
subprocess.run("taskkill /F /IM terminal64.exe /T", shell=True, capture_output=True)
time.sleep(2)

print("Step 2: Launching interactive MT5 GUI via Windows Shell...")
user32.AllowSetForegroundWindow(ASFW_ANY)

# Use cmd.exe start to run MT5 directly in user desktop session
mt5_cmd = r'start "" "C:\Program Files\HFM Metatrader 5\terminal64.exe" /login:205081617 /password:Dew717254. /server:HFMarketsGlobal-Live15'
subprocess.run(f'cmd.exe /c "{mt5_cmd}"', shell=True)

time.sleep(3)

print("Step 3: Checking process status...")
proc_out = subprocess.check_output(['pwsh', '-Command', 'Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, MainWindowHandle, MainWindowTitle | Format-List']).decode()
print(proc_out)

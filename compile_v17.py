import subprocess
import time
import os
import shutil

mq5_path = r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_Grandmaster_v17.mq5"
ex5_path = r"D:\Trade_Gus\EA_Source\XAUUSD_Apex_Grandmaster_v17.ex5"
log_path = r"D:\Trade_Gus\compile_v17.log"
editor = r"C:\Program Files\HFM Metatrader 5\metaeditor64.exe"

print(f"Compiling {mq5_path} using MetaEditor...")
cmd = f'"{editor}" /compile:"{mq5_path}" /log:"{log_path}"'
subprocess.run(cmd, shell=True)
time.sleep(3)

if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-16", errors="ignore") as f:
        print("--- MetaEditor Log ---")
        print(f.read())

if os.path.exists(ex5_path):
    print("SUCCESS: XAUUSD_Apex_Grandmaster_v17.ex5 compiled successfully!")
    dst1 = r"D:\Trade_Gus\XAUUSD_Apex_Grandmaster_v17.ex5"
    dst2 = r"C:\Users\PC\AppData\Roaming\MetaQuotes\Terminal\E3E3B02889D32F38295D39BF94B6AD4A\MQL5\Experts\XAUUSD_Apex_Grandmaster_v17.ex5"
    shutil.copy2(ex5_path, dst1)
    shutil.copy2(ex5_path, dst2)
    print("Copied .ex5 to workspace and MT5 Experts directory.")
else:
    print("ERROR: Compilation failed, ex5 not found.")

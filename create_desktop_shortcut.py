import os
import subprocess

vbs_code = """
Set WshShell = CreateObject("WScript.Shell")
desktop = WshShell.SpecialFolders("Desktop")
Set shortcut = WshShell.CreateShortcut(desktop & "\\Start_MT5_Foreground.lnk")
shortcut.TargetPath = "D:\\Trade_Gus\\Open_MT5.bat"
shortcut.WorkingDirectory = "D:\\Trade_Gus"
shortcut.WindowStyle = 1
shortcut.Description = "Launch MT5 GUI in Foreground"
shortcut.Save
"""

vbs_path = r"D:\Trade_Gus\create_shortcut.vbs"
with open(vbs_path, "w") as f:
    f.write(vbs_code)

subprocess.run(f'wscript.exe "{vbs_path}"', shell=True)
print("Desktop shortcut created successfully!")

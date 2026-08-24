
Set WshShell = CreateObject("WScript.Shell")
desktop = WshShell.SpecialFolders("Desktop")
Set shortcut = WshShell.CreateShortcut(desktop & "\Start_MT5_Foreground.lnk")
shortcut.TargetPath = "D:\Trade_Gus\Open_MT5.bat"
shortcut.WorkingDirectory = "D:\Trade_Gus"
shortcut.WindowStyle = 1
shortcut.Description = "Launch MT5 GUI in Foreground"
shortcut.Save

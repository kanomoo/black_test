Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
$code = @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
Add-Type -TypeDefinition $code -ErrorAction SilentlyContinue

Stop-Process -Name "terminal64" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Launch MT5 directly into active Windows Shell session
$cmd = '/c start "" "C:\Program Files\HFM Metatrader 5\terminal64.exe" /login:205081617 /password:Dew717254. /server:HFMarketsGlobal-Live15'
Start-Process "cmd.exe" -ArgumentList $cmd -WindowStyle Normal
Start-Sleep -Seconds 5

$proc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue
if ($proc) {
    $hwnd = $proc.MainWindowHandle
    if ($hwnd -ne 0) {
        [Win32]::ShowWindow($hwnd, 3)
        [Win32]::SetForegroundWindow($hwnd)
    }
}

Get-Process -Name "terminal64" | Select-Object Id, ProcessName, MainWindowHandle, MainWindowTitle

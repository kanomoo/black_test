Stop-Process -Name "terminal64" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$shell = New-Object -ComObject "Shell.Application"
$shell.ShellExecute("C:\Program Files\HFM Metatrader 5\terminal64.exe", "/login:205081617 /password:Dew717254. /server:HFMarketsGlobal-Live15", "", "open", 1)

Start-Sleep -Seconds 4

$proc = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "MT5 Process started successfully! Process ID: $($proc.Id)"
    Write-Host "MainWindowHandle: $($proc.MainWindowHandle)"
    Write-Host "MainWindowTitle: $($proc.MainWindowTitle)"
} else {
    Write-Host "Failed to start MT5 process."
}

for ($i = 0; $i -lt 10; $i++) {
    $p = Get-Process -Name terminal64 -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host "Sec $i - PID: $($p.Id), HWND: $($p.MainWindowHandle), Title: '$($p.MainWindowTitle)'"
    } else {
        Write-Host "Sec $i - No terminal64 process"
    }
    Start-Sleep -Seconds 1
}

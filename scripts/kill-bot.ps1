# Stop all bot-related processes (Python, uvicorn)
# Run: .\scripts\kill-bot.ps1

$processes = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -match '^python|^uvicorn' -or
    ($_.ProcessName -eq 'python' -and $_.MainWindowTitle -match 'iqromax|main\.py')
}

if ($processes) {
    $processes | ForEach-Object {
        Write-Host "Stopping: $($_.ProcessName) (PID: $($_.Id))"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Done. Stopped $($processes.Count) process(es)."
} else {
    Write-Host "No bot processes found."
}

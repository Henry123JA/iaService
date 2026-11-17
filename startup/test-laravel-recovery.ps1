$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$backend = Join-Path (Split-Path $root -Parent) 'sw-scala'
$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object -First 1
$server = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
if ($server.Name -ne 'php.exe' -or $server.CommandLine -notlike "*$backend*") {
    throw 'El proceso del puerto 8000 no coincide con Laravel; no se detuvo.'
}
$parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($server.ParentProcessId)"
if ($parent.Name -eq 'php.exe' -and $parent.CommandLine -match 'artisan\s+serve') {
    Stop-Process -Id $parent.ProcessId -ErrorAction SilentlyContinue
}
Stop-Process -Id $server.ProcessId -ErrorAction SilentlyContinue
Write-Output 'Laravel detenido para comprobar recuperacion automatica.'

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$script = Join-Path $PSScriptRoot 'supervisor.py'
$config = Join-Path $PSScriptRoot 'config.json'

foreach ($path in @($pythonw, $script, $config)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Falta archivo requerido: $path. Ejecuta startup/install.ps1 primero." }
}

$process = Start-Process -FilePath $pythonw -ArgumentList ('"' + $script + '"') `
    -WorkingDirectory $root -WindowStyle Hidden -PassThru
Write-Output "Supervisor iniciado manualmente (PID $($process.Id)). Revisa data/startup/supervisor.log."

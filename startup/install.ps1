$ErrorActionPreference = 'Stop'
# Configura las rutas locales, pero no registra ni inicia tareas automaticas.
$root = Split-Path $PSScriptRoot -Parent
$backend = Join-Path (Split-Path $root -Parent) 'sw-scala'
$python = Join-Path $root '.venv\Scripts\python.exe'
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$script = Join-Path $PSScriptRoot 'supervisor.py'
$php = (Get-Command php.exe -ErrorAction Stop).Source
$docker = (Get-Command docker.exe -ErrorAction Stop).Source
$postgres = Get-Service | Where-Object { $_.Name -like 'postgresql*' } | Select-Object -First 1
if (-not $postgres) { throw 'No se encontro el servicio PostgreSQL.' }
foreach ($path in @($python, $pythonw, $script, (Join-Path $backend 'artisan'))) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Falta archivo requerido: $path" }
}
$config = @{php=$php;docker=$docker;python=$python;laravel=$backend;postgres_service=$postgres.Name;postgres_port=5432}
$config | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'config.json') -Encoding UTF8

foreach ($taskName in @('Scala-Servicios', 'Scala-Preparar-Seguimiento')) {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        if ($task.State -eq 'Running') { Stop-ScheduledTask -TaskName $taskName }
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Output "Tarea automatica eliminada: $taskName"
    }
}

$postgresManual = $false
try {
    Set-Service -Name $postgres.Name -StartupType Manual
    $postgresManual = $true
    Write-Output "PostgreSQL configurado para inicio manual: $($postgres.Name)"
} catch {
    Write-Warning "No se pudo cambiar el inicio de PostgreSQL. Ejecuta este script como administrador para evitar su arranque automatico. $($_.Exception.Message)"
}

if ($postgresManual) {
    Write-Output 'Configuracion lista. Inicia los servicios manualmente con startup/start-manual.ps1.'
} else {
    Write-Output 'Las tareas automaticas fueron eliminadas. PostgreSQL aun puede iniciar con Windows; ejecuta este script como administrador para desactivarlo.'
}

$ErrorActionPreference = 'Stop'
$taskNames = @('Scala-Servicios', 'Scala-Preparar-Seguimiento')
$tasks = @($taskNames | ForEach-Object {
    Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue
} | Where-Object { $_ })
$postgres = Get-Service | Where-Object { $_.Name -like 'postgresql*' } | Select-Object -First 1
$postgresState = $null
if ($postgres) { $postgresState = [pscustomobject]@{Name=$postgres.Name;Status=$postgres.Status;StartType=$postgres.StartType} }

[pscustomobject]@{
    AutomaticTasks = @($tasks | ForEach-Object { $_.TaskName })
    PostgreSQL = $postgresState
} | ConvertTo-Json -Depth 3

if ($tasks.Count -gt 0) { throw 'Aun hay tareas programadas de arranque del proyecto.' }
if (-not $postgres -or $postgres.StartType -ne 'Manual') {
    throw 'PostgreSQL debe configurarse como inicio Manual; ejecuta startup/install.ps1 como administrador.'
}

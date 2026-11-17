$ErrorActionPreference = 'Stop'
$services = @(Get-Service | Where-Object { $_.Name -match 'postgres|docker' } | Select-Object Name, Status, StartType)
$listeners = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 8000,8001,5678 } | Select-Object LocalPort,OwningProcess)
$tasks = @(Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like 'Scala-*' } | Select-Object TaskName, State)
[pscustomobject]@{User=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name;TimeZone=(Get-TimeZone).Id;Services=$services;Listeners=$listeners;Tasks=$tasks} | ConvertTo-Json -Depth 5

# Plakzicht Mail-server als achtergronddienst (Windows Taakplanner), gebruikt door het installatieprogramma.
# Draait als SYSTEM: start bij het opstarten van de pc (ook zonder ingelogde gebruiker) en opnieuw als hij stopt.
# Gegevens staan in C:\ProgramData\Plakzicht Mail.
param([string]$Actie = "installeer", [string]$Exe = "")
$ErrorActionPreference = "Stop"
$naam = "Plakzicht Mail server"

if ($Actie -eq "verwijder" -or $Actie -eq "stop") {
    Stop-ScheduledTask -TaskName $naam -ErrorAction SilentlyContinue
    Get-Process -Name "Plakzicht Mail server" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    if ($Actie -eq "verwijder") {
        Unregister-ScheduledTask -TaskName $naam -Confirm:$false -ErrorAction SilentlyContinue
        netsh advfirewall firewall delete rule name="$naam" | Out-Null
    }
    exit 0
}

if (-not $Exe) { $Exe = Join-Path $PSScriptRoot "Plakzicht Mail server.exe" }
$action = New-ScheduledTaskAction -Execute $Exe -Argument "--server --log" -WorkingDirectory (Split-Path -Parent $Exe)
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $naam -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $naam

if ($Actie -eq "installeer-firewall") {
    netsh advfirewall firewall delete rule name="$naam" | Out-Null
    netsh advfirewall firewall add rule name="$naam" dir=in action=allow protocol=TCP localport=8765 profile=private,domain | Out-Null
}

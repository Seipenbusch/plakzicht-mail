# Plakzicht Mail server als achtergronddienst (Windows Taakplanner): start bij het opstarten van de pc,
# ook zonder ingelogde gebruiker, en start opnieuw als hij onverwacht stopt.
param([string]$Actie = "installeer")
$ErrorActionPreference = "Stop"
$naam = "Plakzicht Mail server"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" $Actie"
    exit
}

try {
    if ($Actie -eq "verwijder") {
        Stop-ScheduledTask -TaskName $naam -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $naam -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "De dienst is verwijderd. De server draait niet meer op de achtergrond." -ForegroundColor Green
    } else {
        $pyw = (Get-Command pythonw.exe -ErrorAction Stop).Source
        $user = "$env:USERDOMAIN\$env:USERNAME"
        Write-Host "De server gaat draaien onder je Windows-account $user."
        Write-Host "Vul het WACHTWOORD van dat account in (een pincode werkt hier niet)."
        $cred = Get-Credential -UserName $user -Message "Wachtwoord van je Windows-account voor de Plakzicht Mail server"
        if (-not $cred) { throw "Geannuleerd." }
        $action = New-ScheduledTaskAction -Execute $pyw -Argument "`"$dir\app.py`" --server --log" -WorkingDirectory $dir
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 `
            -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        Register-ScheduledTask -TaskName $naam -Action $action -Trigger $trigger -Settings $settings `
            -User $user -Password $cred.GetNetworkCredential().Password -RunLevel Highest -Force | Out-Null
        Start-ScheduledTask -TaskName $naam
        Write-Host ""
        Write-Host "Klaar. De server draait nu op de achtergrond en start voortaan automatisch met de pc." -ForegroundColor Green
        Write-Host "Meldingen staan in $dir\server.log"
        Write-Host "Sluit eventueel een open 'Start server'-venster: er kan maar een server tegelijk draaien."
    }
} catch {
    Write-Host "Mislukt: $($_.Exception.Message)" -ForegroundColor Red
}
Read-Host "Druk op Enter om te sluiten"

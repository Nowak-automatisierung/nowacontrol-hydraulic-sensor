<#
.SYNOPSIS
    Flash Bootloader + Zigbee-HA Firmware auf XIAO MG24 (EFR32MG24B220F1536IM48)

.DESCRIPTION
    Standardisierter Flash-Prozess fuer nowaControl Hydraulic Sensor.
    Reihenfolge: Chip loeschen -> Bootloader -> Anwendung -> Reset

.PARAMETER Target
    pyOCD Target-ID (default: efr32mg24b220f1536im48)

.PARAMETER SkipErase
    Chip-Erase ueberspringen (nur wenn Bootloader bereits korrekt geflasht ist)

.EXAMPLE
    .\scripts\flash-sensor.ps1
    .\scripts\flash-sensor.ps1 -SkipErase
#>

param(
    [string]$Target = "efr32mg24b220f1536im48",
    [switch]$SkipErase = $false
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

$bootloader = Join-Path $repoRoot "sensor-platform\firmware\bootloader\nowacontrol_bootloader_nwc_hyd_001.hex"
$app        = Join-Path $repoRoot "sensor-platform\firmware\applications\zigbee-ha\cmake_gcc\build\base\nowacontrol-zigbee-ha.hex"

Write-Host "=== nowaControl Hydraulic Sensor - Flash Script ===" -ForegroundColor Cyan
Write-Host "Target  : $Target"
Write-Host "Bootloader: $bootloader"
Write-Host "App       : $app"
Write-Host ""

if (-not (Test-Path $bootloader)) { throw "Bootloader nicht gefunden: $bootloader" }
if (-not (Test-Path $app))        { throw "Applikation nicht gefunden: $app" }

if (-not $SkipErase) {
    Write-Host "[1/4] Chip erase..." -ForegroundColor Yellow
    pyocd erase -t $Target --chip
}

Write-Host "[2/4] Flash Bootloader..." -ForegroundColor Yellow
pyocd flash -t $Target $bootloader

Write-Host "[3/4] Flash Application..." -ForegroundColor Yellow
pyocd flash -t $Target $app

Write-Host "[4/4] Reset..." -ForegroundColor Yellow
pyocd reset -t $Target

Write-Host ""
Write-Host "=== Flash erfolgreich! ===" -ForegroundColor Green
Write-Host "Das Geraet startet jetzt. LED sollte blinken (500ms = sucht Netzwerk)."

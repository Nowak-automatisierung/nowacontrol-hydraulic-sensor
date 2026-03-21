$project = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$repoName = Split-Path -Path $project -Leaf
$OverwriteCoreFiles = $false

if ($repoName -ne 'nowacontrol-hydraulic-sensor') {
    throw "Falsches Verzeichnis: $project"
}

if (-not (Test-Path -LiteralPath "$project\CLAUDE.md")) {
    throw "CLAUDE.md fehlt. Das sieht nicht nach dem erwarteten Repo-Root aus: $project"
}

if (-not (Test-Path -LiteralPath "$project\.claude")) {
    throw ".claude fehlt. Das sieht nicht nach dem erwarteten Repo-Root aus: $project"
}

function Ensure-Dir {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Move-DirIfExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$From,

        [Parameter(Mandatory = $true)]
        [string]$To
    )

    if (Test-Path -LiteralPath $From) {
        $parent = Split-Path -Path $To -Parent
        Ensure-Dir -Path $parent

        if (-not (Test-Path -LiteralPath $To)) {
            Move-Item -LiteralPath $From -Destination $To
            Write-Host "Verschoben: $From -> $To" -ForegroundColor Yellow
        }
        else {
            Write-Host "Übersprungen, Ziel existiert bereits: $To" -ForegroundColor DarkYellow
        }
    }
}

function Write-NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Write-NoBomIfMissing {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    if (Test-Path -LiteralPath $Path) {
        Write-Host "Übersprungen, Datei existiert bereits: $Path" -ForegroundColor DarkYellow
        return
    }

    Write-NoBom -Path $Path -Content $Content
}

function Write-CoreFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    if ($OverwriteCoreFiles) {
        Write-NoBom -Path $Path -Content $Content
    }
    else {
        Write-NoBomIfMissing -Path $Path -Content $Content
    }
}

# 1) Basisordner sicherstellen
$baseDirs = @(
    "$project\docs",
    "$project\docs\integrations",
    "$project\sensor-platform",
    "$project\device-cloud",
    "$project\admin-portal",
    "$project\marketing-site",
    "$project\infra",
    "$project\.claude\agents",
    "$project\.claude\skills",
    "$project\.github\workflows"
)

foreach ($dir in $baseDirs) {
    Ensure-Dir -Path $dir
}

# 2) Bestehende generische Struktur in neue Zielstruktur verschieben
Move-DirIfExists -From "$project\firmware"     -To "$project\sensor-platform\firmware"
Move-DirIfExists -From "$project\hardware"     -To "$project\sensor-platform\hardware"
Move-DirIfExists -From "$project\integrations" -To "$project\sensor-platform\integrations"
Move-DirIfExists -From "$project\ota"          -To "$project\sensor-platform\ota"
Move-DirIfExists -From "$project\tests"        -To "$project\sensor-platform\tests"
Move-DirIfExists -From "$project\tools"        -To "$project\sensor-platform\tools"
Move-DirIfExists -From "$project\cloud"        -To "$project\device-cloud\services"

Move-DirIfExists -From "$project\docs\home-assistant" -To "$project\docs\integrations\home-assistant"
Move-DirIfExists -From "$project\docs\matter"         -To "$project\docs\integrations\matter"

# 3) Zielstruktur vervollständigen
$dirs = @(
    "$project\docs\product",
    "$project\docs\architecture",
    "$project\docs\hardware",
    "$project\docs\protocols",
    "$project\docs\integrations\home-assistant",
    "$project\docs\integrations\matter",
    "$project\docs\release",
    "$project\docs\adr",

    "$project\sensor-platform\firmware\board\xiao-mg24",
    "$project\sensor-platform\firmware\applications\zigbee-ha",
    "$project\sensor-platform\firmware\applications\matter-thread",
    "$project\sensor-platform\firmware\applications\ble-diagnostics",
    "$project\sensor-platform\firmware\bootloader",
    "$project\sensor-platform\firmware\hal\sensor-interface",
    "$project\sensor-platform\firmware\shared",
    "$project\sensor-platform\firmware\config",

    "$project\sensor-platform\hardware\sensor-interface",
    "$project\sensor-platform\hardware\power",
    "$project\sensor-platform\hardware\pcb",
    "$project\sensor-platform\hardware\enclosure",

    "$project\sensor-platform\integrations\home-assistant\zha",
    "$project\sensor-platform\integrations\home-assistant\zigbee2mqtt",
    "$project\sensor-platform\integrations\matter",

    "$project\sensor-platform\ota\manifests",
    "$project\sensor-platform\ota\channels",
    "$project\sensor-platform\ota\release-notes",
    "$project\sensor-platform\ota\rollback",

    "$project\sensor-platform\tests\unit",
    "$project\sensor-platform\tests\integration",
    "$project\sensor-platform\tests\hil",
    "$project\sensor-platform\tests\pairing",
    "$project\sensor-platform\tests\protocol",

    "$project\sensor-platform\tools\flash",
    "$project\sensor-platform\tools\sniffer",
    "$project\sensor-platform\tools\provisioning",
    "$project\sensor-platform\tools\release",

    "$project\device-cloud\services\device-api",
    "$project\device-cloud\services\telemetry",
    "$project\device-cloud\services\provisioning",
    "$project\device-cloud\services\update-service",
    "$project\device-cloud\contracts",
    "$project\device-cloud\storage",
    "$project\device-cloud\tests",
    "$project\device-cloud\tools",

    "$project\admin-portal\app",
    "$project\admin-portal\shared",
    "$project\admin-portal\tests",

    "$project\marketing-site\site",
    "$project\marketing-site\content",
    "$project\marketing-site\assets",

    "$project\infra\dev",
    "$project\infra\stage",
    "$project\infra\prod"
)

foreach ($dir in $dirs) {
    Ensure-Dir -Path $dir
}

# 4) Kern-Dateien nur schreiben, wenn sie noch nicht existieren
Write-CoreFile -Path "$project\README.md" -Content @'
# nowacontrol-hydraulic-sensor

Monorepo für das Produkt nowaControl Hydraulik-Sensor.

## Produktbereiche
- sensor-platform: Embedded-Gerät, Firmware, Hardware, OTA, Protokoll-Integration
- device-cloud: Geräte-API, Telemetrie, Provisioning, Update-Service
- admin-portal: internes/operatorisches Web-Frontend
- marketing-site: öffentliche Website / Produktdarstellung

## Architekturprinzip
Ein Produkt, ein Repository, klar getrennte Domänen.
'@

Write-CoreFile -Path "$project\CLAUDE.md" -Content @'
# CLAUDE.md

## Projektkontext
Dieses Repository ist der Produkt-Workspace für den nowaControl Hydraulik-Sensor.

## Domänen
- sensor-platform
- device-cloud
- admin-portal
- marketing-site

## Arbeitsprinzipien
- Änderungen zuerst analysieren, dann planen, dann umsetzen
- Domänengrenzen respektieren
- Keine Secrets oder privaten Schlüssel im Repository
- OTA, Rollback und Release-Auswirkungen immer mitdenken
- Home-Assistant-Kompatibilität dokumentieren und testbar halten

## Priorität
V1 priorisiert sensor-platform mit Zigbee-HA-Pfad.
Matter/Thread bleibt separater App-Pfad.
BLE dient Provisioning und Diagnose.
'@

Write-CoreFile -Path "$project\docs\architecture\repo-map.md" -Content @'
# Repo Map

## Oberste Produktbereiche
- sensor-platform: Gerät, Firmware, Hardware, Tests, OTA
- device-cloud: Backend- und Geräte-Services
- admin-portal: Bedien- und Verwaltungsoberfläche
- marketing-site: öffentliche Produktseite

## Grundsatz
Jeder Bereich ist eigenständig entwickelbar, aber Teil desselben Produkt-Repositories.
'@

Write-CoreFile -Path "$project\sensor-platform\README.md" -Content @'
# sensor-platform

Embedded- und Hardware-Bereich des Produkts.

## Inhalt
- firmware
- hardware
- integrations
- ota
- tests
- tools

## V1-Fokus
- XIAO MG24 Board-Basis
- Zigbee für Home Assistant
- OTA-fähige Grundarchitektur
'@

Write-CoreFile -Path "$project\device-cloud\README.md" -Content @'
# device-cloud

Backend- und Cloud-Bereich für Geräteverwaltung, Telemetrie, Provisioning und Update-Steuerung.
'@

Write-CoreFile -Path "$project\admin-portal\README.md" -Content @'
# admin-portal

Interne/operatorische Oberfläche für Geräteübersicht, Status, Konfiguration und spätere Servicefunktionen.
'@

Write-CoreFile -Path "$project\marketing-site\README.md" -Content @'
# marketing-site

Öffentliche Website für Produktdarstellung, Inhalte, Kommunikation und spätere Dokumentations-/Support-Einstiegspunkte.
'@

if (-not (Test-Path -LiteralPath "$project\.mcp.json")) {
    Write-NoBom -Path "$project\.mcp.json" -Content @'
{
  "mcpServers": {}
}
'@
}
else {
    Write-Host "Übersprungen, Datei existiert bereits: $project\.mcp.json" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Bereinigte Produktstruktur erstellt." -ForegroundColor Green
Write-Host "Projekt: $project" -ForegroundColor Green
Write-Host "OverwriteCoreFiles: $OverwriteCoreFiles" -ForegroundColor Green
Write-Host ""
Write-Host "Bitte jetzt prüfen mit:" -ForegroundColor Cyan
Write-Host "  Get-ChildItem . -Force"
Write-Host "  Get-ChildItem .\sensor-platform -Force"
Write-Host "  Get-ChildItem .\device-cloud -Force"
Write-Host "  Get-ChildItem .\admin-portal -Force"
Write-Host "  Get-ChildItem .\marketing-site -Force"
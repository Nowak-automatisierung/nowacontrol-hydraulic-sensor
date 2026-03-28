# MG24 Bootloader Baseline

Baseline-Notizen fuer die spaetere Bootloader- und OTA-Struktur auf Basis des Seeed Studio XIAO MG24 (EFR32MG24).

## Zweck

Dieses Verzeichnis dient als Einstiegspunkt fuer die Bootloader-Konfiguration der V1-Firmware.

## Geplanter Inhalt

- Gecko-Bootloader-Konfiguration fuer MG24
- Slot-Layout fuer OTA-Images
- Signatur- und Integrationshinweise
- Fallback- und Recovery-Strategie

## Aktueller Status

Aktuell ist noch keine produktionsreife Bootloader-Konfiguration committed.

Der OTA-Slot-Fallback ist noch nicht verifiziert und muss spaeter mit echter Konfiguration und Testnachweisen validiert werden.

## Abhaengigkeiten

- Flash-Partitionierung
- Signing-Workflow
- OTA-Update-Pfad
- Zigbee-V1-Release-Strategie
# MG24 Firmware Device Baseline

Geraetespezifische Firmware-Baseline fuer den Seeed Studio XIAO MG24 (EFR32MG24).

## Rolle innerhalb der Firmware-Struktur

Dieses Verzeichnis ist der geraetespezifische Einstiegspunkt fuer den MG24.

Die uebergeordnete Firmware-Struktur ist bereits angelegt:

- `../applications/zigbee-ha/` - V1-Applikation (Zigbee/ZHA)
- `../board/xiao-mg24/`        - Board-/Pin-Konfiguration
- `../config/`                 - Build- und Stack-Konfiguration
- `../hal/sensor-interface/`   - Sensor-HAL
- `../bootloader/`             - Bootloader-Konfiguration (M4)

## Status

Strukturelle Baseline. Implementierung folgt ab M0 (Hardware alive).
# ADR 0001 - Zigbee-only V1 Protocol Scope

## Status

Accepted

## Context

Das Produkt nowaControl Hydraulic Sensor basiert auf dem Seeed Studio XIAO MG24 (EFR32MG24) und soll in V1 mit Home Assistant ueber ZHA integriert werden.

Die aktuelle Produkt- und Compliance-Lage macht deutlich, dass die Protokollreichweite von V1 explizit festgelegt werden muss. Unter RED besitzen Zigbee, BLE und Thread unterschiedliche regulatorische und testrelevante Auswirkungen. Eine spaetere OTA-Aktivierung weiterer Funkmodi kann eine erneute Bewertung ausloesen.

## Decision

V1 wird als **Zigbee-only** Produkt definiert.

Fuer V1 gilt:

- Aktiviertes Funkprotokoll: Zigbee (IEEE 802.15.4)
- Zielintegration: Home Assistant ueber ZHA
- Nicht Teil von V1: BLE, Thread, Matter
- Diese Protokolle duerfen in V1 weder produktseitig aktiviert noch ueber OTA nachtraeglich freigeschaltet werden, ohne dass zuvor eine formale Re-Assessment-Entscheidung getroffen wurde

## Consequences

### Positiv

- Geringerer Zertifizierungsumfang fuer V1
- Klarere Test- und Release-Grenzen
- Weniger Risiko bei RF-, RED- und Produktfreigabe

### Negativ

- Roadmap-Protokolle bleiben fuer V1 gesperrt
- Zukuenftige Aktivierung von BLE oder Matter/Thread erfordert gesonderte Architektur-, Compliance- und Release-Pruefung

## Re-assessment trigger

Die folgende Aenderung gilt als expliziter Re-Assessment-Trigger und darf nicht ohne neue Entscheidung freigegeben werden:

- Aktivierung von BLE in Produktionsfirmware
- Aktivierung von Thread oder Matter in Produktionsfirmware
- OTA-Rollout, der einen bisher deaktivierten Funkmodus fuer Feldgeraete einschaltet

## Follow-up

- RF- und Compliance-Dokumente muessen V1 konsistent als Zigbee-only fuehren
- Firmware- und OTA-Policies muessen verhindern, dass zusaetzliche Funkmodi unbeabsichtigt aktiviert werden
- Spaetere Multi-Protocol-Optionen werden in einem separaten ADR bewertet
# Home Assistant Instanz-Setup

## Ziel
Dieses Runbook beschreibt den praktisch nutzbaren Installationspfad fuer die aktuelle Home-Assistant-Instanz.

## Aktueller Installationspfad
Das Repository ist jetzt oeffentlich und HACS-faehig. Der bevorzugte Weg ist deshalb:

1. Repository in HACS als `Integration` hinzufuegen
2. Paket aus HACS installieren
3. Integration ueber `Einstellungen -> Geraete & Dienste -> Integration hinzufuegen -> nowaControl Hydraulic Sensor` einrichten
4. nur den ZHA-Basis-Pfad in `configuration.yaml` setzen

## Pfad A - HACS + UI-first

### 1. HACS Custom Repository
- Repository URL:
  `https://github.com/Nowak-automatisierung/nowacontrol-hydraulic-sensor`
- Typ: `Integration`

### 2. Integration installieren
Danach das Paket in HACS installieren.

### 3. Integration im UI einrichten
In Home Assistant:

- `Einstellungen`
- `Geraete & Dienste`
- `Integration hinzufuegen`
- `nowaControl Hydraulic Sensor`

### 4. configuration.yaml ergaenzen

```yaml
zha:
  custom_quirks_path: /config/custom_zha_quirks
```

### 5. Home Assistant neu starten

### 6. Quirk-Status im UI pruefen
- Wenn Auto-Install aktiv ist, installiert die Integration den ZHA-Quirk selbst.
- Wenn ein Repair-Hinweis erscheint, diesen bestaetigen.
- Services bleiben nur als Fallback fuer Support/Wartung bestehen.

### 7. Home Assistant erneut neu starten

### 8. Sensor in ZHA loeschen und neu anlernen
Das ist wichtig, damit ZHA den Hersteller-Cluster `0xFC10` und den Delta-T-Endpoint neu interviewt.

## Pfad B - Lokaler Fallback
Falls HACS in einer Zielumgebung nicht verfuegbar ist, bleibt der lokale Installationspfad ueber `/config/custom_components/` als Fallback erhalten.

## Erwartete Entitaeten
- Vorlauf Temperatur
- Ruecklauf Temperatur
- Delta-T
- Measurement interval
- Vorlauf offset
- Ruecklauf offset
- 1-Wire sensor count
- 1-Wire error count
- last sensor status
- last update age
- antenna mode
- rescan button
- factory reset button

## Aktueller Realitaetscheck
- Temperaturwerte kommen bereits in HA an.
- Der zweite Fuehler wurde im laufenden Projekt inzwischen erkannt.
- Externe Antenne ist firmware-seitig aktiv erzwungen; final absichern sollten wir sie spaeter mit einem kontrollierten RSSI/LQI-A/B-Test.

# Home Assistant Instanz-Setup

## Ziel
Dieses Runbook beschreibt den praktisch nutzbaren Installationspfad fuer die aktuelle Home-Assistant-Instanz.

## Wichtiger HACS-Hinweis
HACS kann laut offizieller Dokumentation **keine privaten GitHub-Repositories** als Custom Repository verwenden. Solange `Nowak-automatisierung/nowacontrol-hydraulic-sensor` privat bleibt, ist fuer die aktuelle Instanz der **lokale Installationspfad** der verlaessliche Weg.

## Pfad A - Sofort nutzbar mit privatem Repository

### 1. Home-Assistant-Paket lokal kopieren
Kopiere aus dem Repository:

- `custom_components/nowacontrol_hydraulic_sensor/`

nach:

- `/config/custom_components/nowacontrol_hydraulic_sensor/`

### 2. configuration.yaml ergaenzen

```yaml
nowacontrol_hydraulic_sensor:

zha:
  custom_quirks_path: /config/custom_zha_quirks
```

### 3. Home Assistant neu starten

### 4. Service zum Installieren des Quirks ausfuehren
Nach dem Neustart in Home Assistant ausfuehren:

- `nowacontrol_hydraulic_sensor.install_zha_quirk`

Optional:
- `nowacontrol_hydraulic_sensor.show_quirk_status`

### 5. Home Assistant erneut neu starten

### 6. Sensor in ZHA loeschen und neu anlernen
Das ist wichtig, damit ZHA den Hersteller-Cluster `0xFC10` und den Delta-T-Endpoint neu interviewt.

## Pfad B - Spaeterer HACS-Rollout
Dieser Pfad ist erst sinnvoll, wenn das Repository oeffentlich ist oder in eine oeffentliche HACS-geeignete Release-Struktur ueberfuehrt wurde.

### HACS Custom Repository
- Repository URL eintragen
- Typ: `Integration`

Danach:
1. Integration ueber HACS installieren
2. `configuration.yaml` wie oben ergaenzen
3. Quirk ueber den Installationsservice deployen
4. Home Assistant neu starten
5. Sensor neu anlernen

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

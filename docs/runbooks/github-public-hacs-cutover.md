# GitHub Public + HACS Cutover

## Ziel
Den aktuell lokal funktionierenden nowaControl Hydraulic Sensor sauber nach GitHub bringen und danach professionell ueber HACS als Custom Repository installieren.

## Warum GitHub noch den alten Stand zeigt
- Die neuen Arbeiten liegen aktuell lokal im Repository.
- Sie sind noch nicht commitet und nicht nach GitHub gepusht.
- Zusaetzlich arbeitest du lokal auf `feat/dual-power-boot-detection`, waehrend der Screenshot auf GitHub `main` zeigt.
- Selbst ein Push auf den Feature-Branch aendert `main` noch nicht.

## Empfohlene Veroeffentlichungsstrategie

### Option A: Ein Repo fuer alles
- Das bestehende Repository `nowacontrol-hydraulic-sensor` wird oeffentlich.
- Firmware, Dokumentation, HACS-Paket und Release-Artefakte liegen zusammen in einem Monorepo.
- Vorteil: einfachster Ablauf.
- Nachteil: interne Projektstruktur, Firmwarequellen und Altlasten werden oeffentlich sichtbar.

### Option B: Professioneller Produktpfad
- Das bestehende Monorepo bleibt Source of Truth.
- Fuer HACS wird ein separates oeffentliches Distribution-Repository angelegt.
- Dieses Repo enthaelt nur:
  - `custom_components/nowacontrol_hydraulic_sensor/`
  - `hacs.json`
  - oeffentliche Installationsdoku
  - Releases fuer HACS
- Vorteil: sauberste Trennung zwischen Produktentwicklung und oeffentlicher Auslieferung.
- Nachteil: etwas mehr Pflegeaufwand.

## Empfehlung
Fuer einen professionellen Rollout ist **Option B** besser. Wenn du schnell testen willst, ist **Option A** der kuerzeste Weg.

## So machst du das bestehende GitHub-Repo oeffentlich
1. GitHub oeffnen.
2. Repository `nowacontrol-hydraulic-sensor` oeffnen.
3. `Settings` waehlen.
4. Ganz nach unten zum Bereich `Danger Zone`.
5. `Change repository visibility` waehlen.
6. `Change to public` bestaetigen.
7. Repository-Namen erneut eingeben und bestaetigen.

Hinweis:
- Vorher sicherstellen, dass keine geheimen Dateien, lokalen Dumps oder interne Altlasten mehr im Push landen.
- `.claude/worktrees/` und lokale ZAP-Backups sind jetzt per `.gitignore` ausgeschlossen.

## Sauberer GitHub-Rollout fuer dieses Projekt
1. Lokale Aenderungen pruefen und in einem Commit zusammenfassen.
2. Den Commit auf den aktiven Feature-Branch pushen.
3. Auf GitHub kontrollieren, dass der neue Branch sichtbar ist.
4. Pull Request nach `main` erstellen.
5. Erst nach Review/Verifikation `main` aktualisieren.
6. Danach entweder:
   - HACS direkt auf das nun oeffentliche Repo zeigen lassen, oder
   - aus `main` ein dediziertes HACS-Distributions-Repo ableiten.

## HACS-Testpfad mit dem bestehenden Repo
Voraussetzungen:
- Repo ist oeffentlich oder aus HACS erreichbar.
- `hacs.json` liegt am Root.
- `custom_components/nowacontrol_hydraulic_sensor/` liegt am Root.

Dann in Home Assistant:
1. HACS oeffnen.
2. `Benutzerdefinierte Repositories`.
3. Repository-URL eintragen.
4. Typ `Integration` waehlen.
5. HACS neu laden.
6. `nowaControl Hydraulic Sensor` installieren.
7. `configuration.yaml` ergaenzen:

```yaml
nowacontrol_hydraulic_sensor:

zha:
  custom_quirks_path: /config/custom_zha_quirks
```

8. Home Assistant neu starten.
9. Service `nowacontrol_hydraulic_sensor.install_zha_quirk` ausfuehren.
10. Home Assistant erneut neu starten.
11. Sensor in ZHA neu anlernen.

## Mehrere Sensoren sauber anlegen
- Jeder physische Sensor wird als eigenes Zigbee-Geraet angelernt.
- Keine Forks pro Liegenschaft.
- Standortunterschiede werden ueber Konfigurationswerte im Geraet bzw. spaeter ueber HA-Entitaeten gepflegt:
  - Messintervall
  - Vorlauf-Offset
  - Ruecklauf-Offset
  - Antennen-/Diagnosestatus
- Einheitliche Benennung:
  - `nowaControl Hydraulic Sensor V1 - Heizkreis EG`
  - `nowaControl Hydraulic Sensor V1 - Heizkreis OG`
  - `nowaControl Hydraulic Sensor V1 - Wohnung 3 VL/RL`

## Was vor dem Push noch geprueft werden muss
- Keine lokalen Geheimnisse
- Keine Build-Artefakte
- Keine `.claude/worktrees`
- Keine temporaeren ZAP-Sicherungen
- README und HACS-Doku konsistent
- GitHub Actions vorhanden
- Home-Assistant-Paket am Root vorhanden

## Finaler Profi-Pfad
1. Lokalen Stand committen und pushen
2. GitHub auf public oder Distribution-Repo umstellen
3. HACS-End-to-End testen
4. Releases fuer:
   - HA/HACS
   - Firmware
   - OTA
5. Erst danach weitere Sensorvarianten und Liegenschaften ausrollen

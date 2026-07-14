# 🏠 Simon's Home Assistant

Persönliche Home-Assistant-Konfiguration — kein Fremd-Tutorial-Setup, sondern über Zeit gewachsen und für genau eine Wohnung zugeschnitten. Dieses Repo ist das Backup/Versionsarchiv der Config, die live auf einem Raspberry Pi (Home Assistant OS) läuft.

## Was hier drinsteckt

- **Ein durchgestyltes Status-Dashboard** (`dashboards/status_dashboard.yaml`) im [Liquid-Glass-Theme](themes/liquid_glass.yaml) — Räume mit Klima/Licht/Rollo-Steuerung, Anwesenheit, Haushaltsgeräte-Live-Timer (inkl. iOS Live Activities), Auto-Status, Synology, Saugroboter, Müllabfuhr, Batteriestatus, Einkaufsliste, Wettervorhersage.
- **Drei selbstgeschriebene Custom Components**, weil es dafür nichts Fertiges gab:
  - [`paket_tracking`](custom_components/paket_tracking) — wertet Bestell-/Versand-/Zustellmails (DHL, UPS, Hermes, Amazon) per IMAP aus und pflegt drei Zähler (offen/unterwegs/heute) inkl. automatischem Ablauf hängengebliebener Einträge.
  - [`philips_sonicare_ble`](custom_components/philips_sonicare_ble) *(lokaler Fork/Patch)* — Debug-Instrumentierung für die BLE-Kopplung einer Sonicare-Zahnbürste.
  - `ha_mcp_tools` — vom [ha-mcp](https://github.com/homeassistant-ai/ha-mcp)-Add-on selbst verwaltet, gibt einem LLM-Client (z. B. Claude) kontrollierten Zugriff auf die Instanz.
- **31 Automationen** für Haushaltsgeräte-Benachrichtigungen, Rollo-Bewegungserkennung, Tür-/Schloss-Protokollierung, Ladesäulen-Parkzeit-Warnung und mehr.
- **HACS-Integrationen** für BYD-Fahrzeug, Meross, Xiaomi/Mi Home, DWD-Wetter und Müllabfuhr-Kalender.

## Struktur

```
configuration.yaml       Haupteinstiegspunkt, Helper (input_datetime, timer, template)
automations.yaml         Alle Automationen
scripts.yaml / scenes.yaml
dashboards/               Lovelace-Dashboard(s), YAML-Modus
custom_components/        Eigene + gepatchte Integrationen
themes/                   Liquid-Glass-Theme
blueprints/               Automation-/Script-Blueprints
```

## Sync-Workflow

`/Volumes/config` ist die SMB-Freigabe der laufenden Instanz — direkt darauf `git` laufen zu lassen ist unzuverlässig (Locking-Probleme über SMB). Stattdessen lebt dieses Repo lokal, und [`sync-and-push.sh`](sync-and-push.sh) synchronisiert per `rsync` von der Freigabe rein, bevor committed/gepusht wird:

```bash
./sync-and-push.sh "Commit-Message"
```

Bewusst ausgeschlossen: `.storage/` (enthält Secrets wie IMAP-App-Passwort, Lock-Zugangsdaten), `secrets.yaml`, Recorder-DB, Logs, `www/community/` (HACS-Assets, reproduzierbar).

## Nicht gedacht zum 1:1-Nachbauen

Vieles hier ist hart auf diese eine Wohnung gemünzt (Müllabfuhr-Zonen, ein bestimmtes Auto, eine bestimmte Zahnbürste, Parkplatz-Koordinaten) — eher Referenz/Inspiration als Copy-paste-Vorlage.

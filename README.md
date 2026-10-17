# 🏠 Simon's Home Assistant

Persönliche Home-Assistant-Konfiguration — kein Fremd-Tutorial-Setup, sondern über Zeit gewachsen und für genau eine Wohnung zugeschnitten. Dieses Repo ist das Backup/Versionsarchiv der Config, die live auf einem Raspberry Pi (Home Assistant OS) läuft.

Nebenbei ist das hier auch ein Experimentierfeld: über [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) bekommt ein LLM (Claude) direkten, kontrollierten Zugriff auf die laufende Instanz. Kleinere Änderungen macht Claude direkt per MCP, größere (z. B. Dashboard-Umbauten) lokal im Repo und spielt sie per `deploy.sh` ein (siehe [Sync-Workflow](#sync-workflow)). Vieles mache ich weiterhin von Hand — es geht darum, auszuprobieren, was sich im Smart-Home-Bereich sinnvoll mit KI-Unterstützung machen lässt (Dashboard-Änderungen, Automationen, Debugging) und wo die Grenzen liegen.

## Was hier drinsteckt

- **Ein durchgestyltes Status-Dashboard** (`dashboards/status_dashboard.yaml`) im [Liquid-Glass-Theme](themes/liquid_glass.yaml) — Räume mit Klima/Licht/Rollo-Steuerung, Anwesenheit, Haushaltsgeräte-Live-Timer (inkl. iOS Live Activities), Auto-Status, Synology, Saugroboter, Müllabfuhr, Batteriestatus, Einkaufsliste, Wettervorhersage.
- **Bemerkenswerte Custom Components:**
  - [`paket_tracking`](custom_components/paket_tracking) *(selbstgeschrieben)* — wertet Bestell-/Versand-/Zustellmails (DHL, UPS, Hermes, Amazon) per IMAP aus und pflegt drei Zähler (offen/unterwegs/heute) inkl. automatischem Ablauf hängengebliebener Einträge.
  - [`philips_sonicare_ble`](https://github.com/mtheli/philips_sonicare_ble) *(reguläre HACS-Integration)* — BLE-Anbindung einer Sonicare-Zahnbürste; ein hartnäckiger Pairing-Bug (BlueZ verweigerte die Just-Works-Bestätigung mangels registriertem D-Bus-Agent) wurde gemeinsam mit dem Maintainer diagnostiziert, Integration läuft jetzt sauber (Akkustand, Bürstenkopf-Verschleiß, Putz-Historie).
  - `ha_mcp_tools` — vom [ha-mcp](https://github.com/homeassistant-ai/ha-mcp)-Add-on selbst verwaltet, gibt einem LLM-Client (z. B. Claude) kontrollierten Zugriff auf die Instanz.
- **37 Automationen** für Haushaltsgeräte-Benachrichtigungen, Rollo-Bewegungserkennung, Tür-/Schloss-Protokollierung, Ladesäulen-Parkzeit-Warnung, Bürstenkopf-Verschleiß, Müllabfuhr-Erinnerungen (Vorabend + selber Tag) und mehr.
- **Broadlink-Fernbedienung Wohnzimmer** — per IR angelernte Befehle (Power-Toggle, TV-Eingang, Lauter/Leiser, Stumm) für den Receiver, gebündelt in einem virtuellen `media_player` (Toggle-Skripte erkennen den echten An/Aus-Zustand über den Stromverbrauch der Steckdose), gekoppelt an Apple TV und via HomeKit-Accessory für Siri-Sprachsteuerung freigegeben.
- **HACS-Integrationen** für [BYD-Fahrzeug](https://github.com/jkaberg/hass-byd-vehicle), [Meross](https://github.com/krahabb/meross_lan), [Xiaomi/Mi Home](https://github.com/XiaoMi/ha_xiaomi_home), [DWD-Wetter](https://github.com/FL550/dwd_weather), [Müllabfuhr-Kalender](https://github.com/mampfes/hacs_waste_collection_schedule), [WashData](https://github.com/3dg1luk43/ha_washdata) und [NeonPlan 3D](https://mastershort.de/en/neonplan3d/manual/) (installiert, noch nicht im Dashboard). Ihr Code liegt nicht in diesem Repo, sondern kommt über HACS.

## Automatische Dashboard-Tests

Das Dashboard ist der Kern des Projekts. Damit eine umbenannte Entität, ein Tippfehler im Template oder eine fehlende Custom Card nicht erst auffällt, wenn man die betroffene Ansicht öffnet, wird es in drei Stufen geprüft ([`tests/dashboard/`](tests/dashboard)):

1. **Statisch** (bei jedem Push im CI): YAML, Syntax aller Jinja- und button-card-JS-Templates, ob jede `custom:`-Karte installiert ist ([`installed_cards.yaml`](tests/dashboard/installed_cards.yaml)), ob Pop-up- und View-Links ins Leere zeigen.
2. **Gegen die laufende Instanz** (lokal): Gibt es jede referenzierte Entität, und rendern alle Templates in HA ohne Fehler?
3. **Rendertest** (lokal): Ein unsichtbarer Browser öffnet jede Ansicht und jedes Pop-up, einmal als iPhone (WebKit, wie die HA-App) und einmal am Desktop. Er schlägt bei Fehlerkarten und JS-Fehlern an und legt Screenshots zum Vorher-Nachher-Vergleich ab. Die Screenshots zeigen echte Daten und bleiben deshalb lokal.

`deploy.sh` führt Stufe 1 und 2 vor dem Kopieren aus und bricht bei Fehlern ab, nach dem Kopieren läuft Stufe 3. Von Hand:

```bash
tests/dashboard/run.sh            # alle Stufen
tests/dashboard/run.sh static     # nur Stufe 1
```

Für Stufe 2 und 3 liegt ein langlebiger HA-Token im macOS-Schlüsselbund (`security add-generic-password -U -s ha-dashboard-tests -a homeassistant -w "$(pbpaste)"`, Token vorher in die Zwischenablage kopieren; die interaktive Abfrage von `security` schneidet nach 128 Zeichen ab), nie im Repo.

## Struktur

```
configuration.yaml       Haupteinstiegspunkt, Helper (input_datetime, timer, template)
automations.yaml         Alle Automationen
scripts.yaml / scenes.yaml
dashboards/               Lovelace-Dashboard(s), YAML-Modus
custom_components/        Nur eigene Integrationen (paket_tracking)
themes/                   Liquid-Glass-Theme
blueprints/               Automation-/Script-Blueprints
tests/dashboard/          Dashboard-Tests (statisch, live, Rendertest)
```

## Sync-Workflow

`/Volumes/config` ist die SMB-Freigabe der laufenden Instanz — direkt darauf `git` laufen zu lassen ist unzuverlässig (Locking-Probleme über SMB). Stattdessen lebt dieses Repo lokal, und [`sync-and-push.sh`](sync-and-push.sh) synchronisiert per `rsync` von der Freigabe rein, bevor committed/gepusht wird:

```bash
./sync-and-push.sh "Commit-Message"
```

Der Rückweg für lokal (z. B. von Claude) bearbeitete Dateien ist [`deploy.sh`](deploy.sh): Es kopiert die geänderten Dateien auf die Freigabe und bricht ab, wenn eine davon seit dem letzten Sync live in der UI oder per MCP geändert wurde. Danach landet der Stand wie gewohnt per `sync-and-push.sh` in Git. Damit bleibt die laufende Instanz die Quelle der Wahrheit, und jeder Commit entspricht einem echten Live-Stand. Die Details für Claude stehen in [`CLAUDE.md`](CLAUDE.md).

```bash
./deploy.sh --dry-run   # zeigt, was live gehen würde
./deploy.sh
./sync-and-push.sh "Commit-Message"
```

Bewusst ausgeschlossen: `.storage/` (enthält Secrets wie IMAP-App-Passwort, Lock-Zugangsdaten), `secrets.yaml`, Recorder-DB, Logs, `www/community/` (HACS-Assets, reproduzierbar) und alle Fremd-Integrationen unter `custom_components/` (über HACS reproduzierbar; sie enthalten teils öffentliche API-Keys der Anbieter, die GitHubs Push Protection blockiert).

**Öffentliches Repo:** Es liegen bewusst keine Zugangsdaten, Tokens oder exakten Standortdaten in diesem Repo — die liegen ausschließlich in `.storage/`, das nie synchronisiert wird.

## Nicht gedacht zum 1:1-Nachbauen

Vieles hier ist hart auf diese eine Wohnung gemünzt (Müllabfuhr-Zonen, ein bestimmtes Auto, eine bestimmte Zahnbürste, Parkplatz-Koordinaten) — eher Referenz/Inspiration als Copy-paste-Vorlage.

# 🏠 Simon's Home Assistant

Persönliche Home-Assistant-Konfiguration — kein Fremd-Tutorial-Setup, sondern über Zeit gewachsen und für genau eine Wohnung zugeschnitten. Dieses Repo ist das Backup/Versionsarchiv der Config, die live auf einem Raspberry Pi (Home Assistant OS) läuft.

Nebenbei ist das hier auch ein Experimentierfeld: über [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) bekommt ein LLM (Claude) direkten, kontrollierten Zugriff auf die laufende Instanz. Kleinere Änderungen macht Claude direkt per MCP, größere (z. B. Dashboard-Umbauten) lokal im Repo und spielt sie per `deploy.sh` ein (siehe [Sync-Workflow](#sync-workflow)). Vieles mache ich weiterhin von Hand — es geht darum, auszuprobieren, was sich im Smart-Home-Bereich sinnvoll mit KI-Unterstützung machen lässt (Dashboard-Änderungen, Automationen, Debugging) und wo die Grenzen liegen.

## Was hier drinsteckt

- **Ein durchgestyltes Status-Dashboard** (`dashboards/status_dashboard.yaml`) im [Liquid-Glass-Theme](themes/liquid_glass.yaml) nach dem Vorbild von iOS 26, optimiert fürs iPhone: Glaskarten mit Unschärfe und Lichtkante auf einem farbigen Verlauf, innen ruhige Kacheln mit konzentrischen Ecken statt Kästen in Kästen, Pop-ups als Sheets, iOS-Systemfarben und -Schrift, eigener heller und dunkler Modus. Das Theme hängt an jeder Ansicht und gilt damit auf allen Geräten. Inhalt: „Heute“-Leiste ganz oben (Wetter, fällige Mülltonnen, Pakete, laufende Haushaltsgeräte mit Fertig-Uhrzeit, Lüften-Hinweis, Einkaufsliste, Stromkosten heute; jeder Hinweis erscheint nur, wenn er ansteht); Netzwerk-Tab (Internet-Status, Auslastung, nächtlicher Speedtest, Geräte im Netz, WLAN, Fritz!Box/Repeater, Werbeblocker, Synology); Hinweis „Internet getrennt“ ganz oben, sobald die Fritz!Box die Verbindung verliert; Anwesenheit mit aktuellem Raum je Person (NeonPlan-Ortung über zwei ESP32-Bluetooth-Proxys und den Pi); Haushaltsgeräte und Saugroboter mit Linien-Icons aus dem mastershort-Icon-Pack, die sich je nach Zustand einfärben (aus: Textfarbe, läuft: Cyan, fertig: Lime); Räume mit Klima/Licht/Rollo-Steuerung (Ist-/Solltemperatur, Heizstatus, Luftfeuchte mit Hinweis „lüften“ ab 65 %), Anwesenheit, Haushaltsgeräte-Live-Timer (inkl. iOS Live Activities), Auto-Status, Synology, Saugroboter (3D-Grundriss statt Kartenbild, Knöpfe „Gezielt reinigen“ pro Raum mit Rückfrage, Status wie „Reinigt Küche“ und Fortschrittsbalken für den Werktagslauf auf Basis der gelernten Fläche), Laufband-Tab (Start/Pause/Stopp, Tempo per Plus/Minus und Schnellwahl 2–6 km/h, aktuelle Einheit, Strecke/Zeit/Schritte/Kalorien heute, Woche und Monat, Balkendiagramme über 7/30 Tage oder 12 Monate) mit kleiner Statuskachel im Büro, die per Tipp dorthin springt, Müllabfuhr, Batteriestatus (weitere Geräte füllen sich per auto-entities selbst, Zählung „fast leer“ / „nicht erreichbar“), Einkaufsliste, Wettervorhersage, Energie-Ansicht mit Stromkosten heute/Monat (Arbeitspreis als Helfer einstellbar) und gemessenen Geräten und geschätztem Hue-Lichtverbrauch je Raum (Powercalc-Gruppen).
- **Bemerkenswerte Custom Components:**
  - [`paket_tracking`](custom_components/paket_tracking) *(selbstgeschrieben)* — wertet Bestell-/Versand-/Zustellmails (DHL, UPS, Hermes, Amazon) per IMAP aus und pflegt drei Zähler (offen/unterwegs/heute) inkl. automatischem Ablauf hängengebliebener Einträge.
  - [`philips_sonicare_ble`](https://github.com/mtheli/philips_sonicare_ble) *(reguläre HACS-Integration)* — BLE-Anbindung einer Sonicare-Zahnbürste; ein hartnäckiger Pairing-Bug (BlueZ verweigerte die Just-Works-Bestätigung mangels registriertem D-Bus-Agent) wurde gemeinsam mit dem Maintainer diagnostiziert, Integration läuft jetzt sauber (Akkustand, Bürstenkopf-Verschleiß, Putz-Historie).
  - [`neonplan-follow-card`](www/neonplan-follow.js) *(selbstgeschrieben)*: zeigt den 3D-Grundriss aus [NeonPlan 3D](https://mastershort.de/en/neonplan3d/manual/) und zoomt automatisch in den Raum, den der Saugroboter gerade reinigt (mit Namenszuordnung, z. B. Roborock „Arbeitszimmer“ → NeonPlan „Büro“). Danach geht die Ansicht zurück zur Gesamtansicht. NeonPlan hat dafür keine offizielle Schnittstelle, die Karte setzt dieselbe interne Raumauswahl wie ein Tipp.
  - `ha_mcp_tools` — vom [ha-mcp](https://github.com/homeassistant-ai/ha-mcp)-Add-on selbst verwaltet, gibt einem LLM-Client (z. B. Claude) kontrollierten Zugriff auf die Instanz.
- **40 Automationen** für Haushaltsgeräte-Benachrichtigungen, Rollo-Bewegungserkennung, Tür-/Schloss-Protokollierung, Ladesäulen-Parkzeit-Warnung, Bürstenkopf-Verschleiß, Müllabfuhr-Erinnerungen (Vorabend + selber Tag), Heizung im Schlafzimmer aus bei offenem Fenster (mit Mitteilung, beim Schließen sofort wieder an), Klingel-Mitteilung mit Face-ID-geschütztem Türöffner und Meldung bei jedem Öffnen der Haustür (mit Angabe, ob über HA oder Ring) und mehr.
- **AdGuard Home** als DNS-Werbe- und Trackerblocker fürs ganze Netz, im Dashboard mit „heute blockiert“, Schutz-Schalter und Balkendiagramm (Heute/7/30 Tage/12 Monate, eigene fortlaufende Zähler mit Langzeitstatistik) (Fritz!Box leitet DNS an den Pi weiter, öffentlicher DNS als Rückfallebene, falls HA neu startet).
- **ESPHome Device Builder** für eigene ESP32-Geräte (Sensoren, Bluetooth-Proxy): Firmware wird auf dem Pi gebaut und per WLAN aufgespielt, Geräte erscheinen automatisch in HA. Die Geräte-Konfigurationen liegen bewusst nicht hier, weil sie Schlüssel enthalten.
- **Türen per iPhone**: Skripte „Haustür öffnen“ (Ring Intercom), „Wohnungstür öffnen / aufschließen / abschließen“ (Nuki über Matter) für Kontrollzentrum, Sperrbildschirm und Action Button der HA-App.
- **Broadlink-Fernbedienung Wohnzimmer** — per IR angelernte Befehle (Power-Toggle, TV-Eingang, Lauter/Leiser, Stumm) für den Receiver, gebündelt in einem virtuellen `media_player` (Toggle-Skripte erkennen den echten An/Aus-Zustand über den Stromverbrauch der Steckdose), gekoppelt an den LG-TV statt an den Apple TV (der schläft ein, während z. B. die Switch läuft; der LG meldet beim Ausschalten erst `off`, dann `unavailable`, beides zählt als aus) und via HomeKit-Accessory für Siri-Sprachsteuerung freigegeben.
- **HACS-Integrationen** für [BYD-Fahrzeug](https://github.com/jkaberg/hass-byd-vehicle), [Meross](https://github.com/krahabb/meross_lan), [Xiaomi/Mi Home](https://github.com/XiaoMi/ha_xiaomi_home), [DWD-Wetter](https://github.com/FL550/dwd_weather), [Müllabfuhr-Kalender](https://github.com/mampfes/hacs_waste_collection_schedule), [WashData](https://github.com/3dg1luk43/ha_washdata) und [NeonPlan 3D](https://mastershort.de/en/neonplan3d/manual/) (installiert, noch nicht im Dashboard). Dazu [Spook](https://github.com/frenck/spook) (meldet Verweise auf nicht existierende Entitäten, etwa in HomeKit-Bridges) und [Powercalc](https://github.com/bramstroker/homeassistant-powercalc) (geschätzter Verbrauch für 19 Geräte ohne Messstecker: Hue-Lampen, HomePods, Hue Bridge, Fritz-Repeater; anonyme Nutzungsstatistik abgeschaltet). Außerdem [FTMS](https://github.com/dudanov/hassio-ftms) für das Walking Pad (Sportstech sWalk Lite Plus) über den Bluetooth-Standard für Fitnessgeräte: Tempo, Strecke, Zeit, Schritte und Kalorien als Sensoren, Start/Pause/Stopp und Geschwindigkeit steuerbar. Das Laufband nennt seine FTMS-Kennung nur auf Nachfrage, deshalb scannen Pi und Wohnzimmer-Proxy aktiv. Weil die Werte nach jeder Einheit auf 0 springen, sammeln Tageszähler (Verbrauchszähler-Helfer) Strecke, Zeit, Schritte und Kalorien für die Auswertung. In HomeKit erscheint das Laufband als Ventilator in der Büro-Bridge: An/Aus startet und stoppt, der Regler stellt 0–6 km/h ein. Ihr Code liegt nicht in diesem Repo, sondern kommt über HACS.

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

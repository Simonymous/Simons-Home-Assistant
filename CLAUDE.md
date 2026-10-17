# Arbeitsweise in diesem Repo

Live-Instanz: Home Assistant OS auf einem Raspberry Pi, `http://homeassistant.local:8123`.
Die **laufende Instanz ist die Quelle der Wahrheit**, dieses Repo ist ihr Versionsarchiv.
`HEAD` entspricht immer dem zuletzt synchronisierten Live-Stand.

## Zwei Wege, Änderungen zu machen

1. **Per MCP (ha-mcp) direkt live**: für Automationen, Skripte, Helper, Entitäts-Recherche,
   Traces/Logs beim Debuggen. Danach `./sync-and-push.sh "…"`, damit Git den Stand hat.
2. **Lokal in den YAML-Dateien**: für größere Umbauten, v. a. `dashboards/status_dashboard.yaml`
   (YAML-Modus) und `themes/`. Ablauf:
   1. Dateien bearbeiten, **nicht committen**
   2. `./deploy.sh` (vorher gern `--dry-run`): kopiert nach `/Volumes/config`, bricht ab,
      wenn die Live-Datei seit dem letzten Sync in der UI/per MCP geändert wurde. Bei
      Dashboard-Dateien laufen vorher die Dashboard-Tests (Stufe 1+2), danach der Rendertest
   3. in HA neu laden (Reload-Service per MCP, Dashboard über Menü > Aktualisieren) und prüfen
   4. `./sync-and-push.sh "Commit-Message"`: holt den Live-Stand und committet/pusht

Commits laufen nur über `sync-and-push.sh`. Ein Commit von Hand würde `HEAD` vom Live-Stand
lösen und die Konfliktprüfung in `deploy.sh` aushebeln.

`sync-and-push.sh` überschreibt per `rsync --delete` alles mit dem Live-Stand: **niemals mit
nicht deployten lokalen Änderungen laufen lassen** (vorher deployen oder `git stash`).

## Voraussetzungen

- SMB-Freigabe gemountet: `smb://homeassistant.local/config` → `/Volumes/config`
- MCP-Server `home-assistant` in Claude Code eingetragen (Webhook-URL aus dem ha-mcp-Panel in HA;
  die URL ist ein Geheimnis und gehört nicht ins Repo)

## Dashboard-Tests (`tests/dashboard/`)

- `tests/dashboard/run.sh [static] [live] [render]`; ohne Argumente alle Stufen. Exit 2 heißt:
  live/render mangels Token übersprungen, das ist kein Erfolg.
- Nach jeder Dashboard-Änderung laufen lassen und die Screenshots unter
  `tests/dashboard/.screenshots/` (iPhone + Desktop, Vorlauf unter `previous/`) ansehen.
  Das iPhone ist das Hauptgerät.
- Neue `custom:`-Karte: erst in HA als Ressource installieren, dann in
  `tests/dashboard/installed_cards.yaml` eintragen.
- Screenshots enthalten echte Daten: nie committen oder in die README übernehmen.

## Regeln

- Öffentliches Repo: keine Tokens, Passwörter, Koordinaten, Webhook-IDs. `.storage/` und
  `secrets.yaml` bleiben draußen; Zugangsdaten über `!secret`.
- Neue `!secret`-Schlüssel auch als Dummy in `.github/workflows/ha-ci.yaml` ergänzen, sonst
  scheitert der Config-Check im CI.
- Vor Änderungen an `configuration.yaml` per MCP die Konfiguration prüfen lassen, bevor neu
  gestartet wird.
- Automationen in `automations.yaml` brauchen eine eindeutige `id` (wie die UI sie vergibt),
  sonst sind sie in der UI nicht editierbar.
- Im Repo liegt nur die eigene Komponente `custom_components/paket_tracking`. HACS- und
  Add-on-Komponenten (z. B. `ha_mcp_tools`) sind per `.gitignore` und Sync-Ausschluss
  draußen und werden nicht von Hand geändert; neue eigene Komponenten in beiden Ausnahmen
  (`.gitignore`, `sync-and-push.sh`) freischalten.
- Skripte, die mit `rsync --delete` oder ähnlich arbeiten, nie aus einer Kopie an anderem
  Ort starten: sie wechseln per `dirname "$0"` in ihr eigenes Verzeichnis.
- Spürbare neue Funktionen (Dashboard-Bereiche, Automationsgruppen, Komponenten) gehören in
  denselben Commit wie ein Update der `README.md`, inkl. Automationen-Zahl.

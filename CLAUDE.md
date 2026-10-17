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
      wenn die Live-Datei seit dem letzten Sync in der UI/per MCP geändert wurde
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

## Regeln

- Öffentliches Repo: keine Tokens, Passwörter, Koordinaten, Webhook-IDs. `.storage/` und
  `secrets.yaml` bleiben draußen; Zugangsdaten über `!secret`.
- Neue `!secret`-Schlüssel auch als Dummy in `.github/workflows/ha-ci.yaml` ergänzen, sonst
  scheitert der Config-Check im CI.
- Vor Änderungen an `configuration.yaml` per MCP die Konfiguration prüfen lassen, bevor neu
  gestartet wird.
- Automationen in `automations.yaml` brauchen eine eindeutige `id` (wie die UI sie vergibt),
  sonst sind sie in der UI nicht editierbar.
- `custom_components/ha_mcp_tools` und HACS-Komponenten nicht von Hand ändern (werden vom
  Add-on bzw. HACS verwaltet). Eigene Komponente: `paket_tracking`.
- Spürbare neue Funktionen (Dashboard-Bereiche, Automationsgruppen, Komponenten) gehören in
  denselben Commit wie ein Update der `README.md`, inkl. Automationen-Zahl.

#!/bin/bash
# Gegenstueck zu sync-and-push.sh: kopiert lokal geaenderte Dateien aus
# diesem Repo auf die SMB-Freigabe der laufenden Instanz.
#
# Grundregel: HEAD entspricht immer dem zuletzt synchronisierten Live-Stand,
# weil nur sync-and-push.sh committet. Der Ablauf ist daher:
#
#   1. Dateien lokal bearbeiten (NICHT committen)
#   2. ./deploy.sh            -> Aenderungen gehen live
#   3. in HA testen / neu laden
#   4. ./sync-and-push.sh "…" -> Live-Stand wird committet und gepusht
#
# Bevor etwas ueberschrieben wird, prueft das Skript, ob die Live-Datei
# noch dem HEAD-Stand entspricht. Wurde sie zwischenzeitlich in der HA-UI
# oder per MCP geaendert, bricht es ab, statt diese Aenderung zu verlieren.
#
# Bei Dashboard-Dateien laufen vorher die Dashboard-Tests (statisch + gegen
# die Live-Instanz) und nach dem Kopieren der Rendertest, siehe tests/dashboard/.
#
# Usage: ./deploy.sh [--dry-run] [--no-tests] [pfad ...]
#   ohne Pfade: alle lokal geaenderten/neuen Dateien

set -euo pipefail
cd "$(dirname "$0")"

TARGET="${HA_CONFIG_DIR:-/Volumes/config}"
DRY_RUN=0
TESTS=1
while [ "${1:-}" = "--dry-run" ] || [ "${1:-}" = "--no-tests" ]; do
  [ "$1" = "--dry-run" ] && DRY_RUN=1
  [ "$1" = "--no-tests" ] && TESTS=0
  shift
done

if [ ! -d "$TARGET" ] || [ ! -f "$TARGET/configuration.yaml" ]; then
  echo "$TARGET ist nicht gemountet (Finder: Gehe zu > Mit Server verbinden > smb://homeassistant.local/config)."
  exit 1
fi

# Dateien, die nur im Repo leben und nie nach HA gehoeren.
is_repo_only() {
  case "$1" in
    README.md|CLAUDE.md|deploy.sh|sync-and-push.sh|.gitignore|.github/*|.claude/*|tests/*) return 0 ;;
    *) return 1 ;;
  esac
}

if [ "$#" -gt 0 ]; then
  CANDIDATES=("$@")
else
  CANDIDATES=()
  while IFS= read -r f; do CANDIDATES+=("$f"); done < <(
    { git diff --name-only HEAD; git ls-files --others --exclude-standard; } | sort -u
  )
fi

DEPLOY=()
CONFLICTS=()
for f in ${CANDIDATES[@]+"${CANDIDATES[@]}"}; do
  is_repo_only "$f" && continue
  if [ ! -f "$f" ]; then
    echo "Uebersprungen (lokal geloescht, live bitte von Hand entfernen): $f"
    continue
  fi
  live="$TARGET/$f"
  if [ -f "$live" ] && cmp -s "$f" "$live"; then
    continue  # live schon identisch
  fi
  if git cat-file -e "HEAD:$f" 2>/dev/null; then
    # Datei existiert im letzten Sync: live muss noch diesem Stand entsprechen.
    if [ -f "$live" ] && ! git show "HEAD:$f" | cmp -s - "$live"; then
      CONFLICTS+=("$f")
      continue
    fi
  elif [ -f "$live" ]; then
    # Neue Datei lokal, aber live existiert schon eine andere.
    CONFLICTS+=("$f")
    continue
  fi
  DEPLOY+=("$f")
done

if [ "${#CONFLICTS[@]}" -gt 0 ]; then
  echo "Abbruch: diese Dateien wurden live seit dem letzten Sync geaendert:"
  printf '  %s\n' "${CONFLICTS[@]}"
  echo "Erst lokale Aenderungen sichern (git stash), ./sync-and-push.sh laufen lassen,"
  echo "dann Aenderungen wieder anwenden (git stash pop) und erneut deployen."
  exit 1
fi

if [ "${#DEPLOY[@]}" -eq 0 ]; then
  echo "Nichts zu deployen."
  exit 0
fi

DASHBOARD=0
for f in "${DEPLOY[@]}"; do
  case "$f" in dashboards/*) DASHBOARD=1 ;; esac
done

if [ "$DASHBOARD" -eq 1 ] && [ "$TESTS" -eq 1 ]; then
  set +e
  tests/dashboard/run.sh static live
  rc=$?
  set -e
  if [ "$rc" -eq 1 ]; then
    echo "Abbruch: Dashboard-Tests fehlgeschlagen (ueberspringen mit --no-tests)."
    exit 1
  fi
fi

for f in "${DEPLOY[@]}"; do
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[dry-run] $f"
  else
    mkdir -p "$TARGET/$(dirname "$f")"
    cp "$f" "$TARGET/$f"
    echo "deployed: $f"
  fi
done

[ "$DRY_RUN" -eq 1 ] && exit 0

if [ "$DASHBOARD" -eq 1 ] && [ "$TESTS" -eq 1 ]; then
  set +e
  tests/dashboard/run.sh render
  rc=$?
  set -e
  if [ "$rc" -eq 1 ]; then
    echo
    echo "Rendertest fehlgeschlagen. Zuruecksetzen auf den letzten Sync-Stand:"
    for f in "${DEPLOY[@]}"; do
      case "$f" in dashboards/*) echo "  git show HEAD:$f > \"$TARGET/$f\"" ;; esac
    done
  fi
fi

cat <<'EOF'

Jetzt in HA neu laden (oder per MCP):
  automations.yaml   -> automation.reload
  scripts.yaml       -> script.reload
  configuration.yaml -> Konfiguration pruefen, dann passenden Reload oder Neustart
  dashboards/*.yaml  -> Dashboard-Menue > Aktualisieren
Danach: ./sync-and-push.sh "Commit-Message"
EOF

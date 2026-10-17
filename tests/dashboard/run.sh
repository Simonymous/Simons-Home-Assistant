#!/bin/bash
# Dashboard-Tests. Usage: tests/dashboard/run.sh [static] [live] [render]
#   ohne Argumente: alle drei Stufen
#   static  YAML/Jinja/JS-Syntax, Karten, Navigation (auch im CI)
#   live    Entitaeten + Templates gegen die laufende Instanz
#   render  Views und Pop-ups im Browser rendern, Screenshots
#
# Token einmalig im Schluesselbund ablegen (HA: Profil > Sicherheit > Langlebige Tokens):
#   security add-generic-password -U -s ha-dashboard-tests -a homeassistant -w "$(pbpaste)"
# (Token in der Zwischenablage; die interaktive Abfrage schneidet nach 128 Zeichen ab)
# Exit 0 = ok, 1 = Fehler, 2 = Live-Stufen mangels Token/Verbindung uebersprungen.

set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
STAGES="${*:-static live render}"
export HA_URL="${HA_URL:-http://homeassistant.local:8123}"
rc=0

stage() { case " $STAGES " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

if stage static; then
  echo "### Stufe 1: statisch"
  python3 "$HERE/check_static.py" || rc=1
fi

if stage live || stage render; then
  if [ -z "${HA_TOKEN:-}" ]; then
    HA_TOKEN="$(security find-generic-password -s ha-dashboard-tests -w 2>/dev/null || true)"
  fi
  if [ -z "$HA_TOKEN" ]; then
    echo "Kein HA-Token im Schluesselbund (ha-dashboard-tests): live/render uebersprungen."
    [ "$rc" -eq 0 ] && rc=2
    exit "$rc"
  fi
  export HA_TOKEN
fi

if stage live; then
  echo "### Stufe 2: gegen laufende Instanz"
  python3 "$HERE/check_live.py"
  r=$?; [ "$r" -eq 1 ] && rc=1; [ "$r" -eq 2 ] && [ "$rc" -eq 0 ] && rc=2
fi

if stage render; then
  echo "### Stufe 3: Rendertest"
  if [ ! -d "$HERE/node_modules/playwright" ]; then
    (cd "$HERE" && npm install --silent && npx playwright install chromium webkit) || exit 1
  fi
  MANIFEST="$(mktemp)"
  python3 "$HERE/dashboard_lib.py" > "$MANIFEST"
  MANIFEST="$MANIFEST" node "$HERE/render.mjs" || rc=1
  rm -f "$MANIFEST"
fi

exit "$rc"

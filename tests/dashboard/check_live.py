#!/usr/bin/env python3
"""Stufe 2: Dashboard gegen die laufende Instanz pruefen (lokal, nicht im CI).

  - jede referenzierte Entitaet existiert (Fehler) und ist nicht unavailable (Warnung)
  - jedes Jinja-Template rendert in HA ohne Fehler (mit entity/config/user wie in
    mushroom-template-card und card_mod)

Token: Umgebungsvariable HA_TOKEN, sonst macOS-Schluesselbund
  (security add-generic-password -U -s ha-dashboard-tests -a homeassistant -w "$(pbpaste)")
Adresse: HA_URL, Standard http://homeassistant.local:8123
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dashboard_lib as dl  # noqa: E402

HA_URL = os.environ.get("HA_URL", "http://homeassistant.local:8123").rstrip("/")
KEYCHAIN_SERVICE = "ha-dashboard-tests"


def token():
    if os.environ.get("HA_TOKEN"):
        return os.environ["HA_TOKEN"]
    try:
        return subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def api(tok, path, body=None):
    req = urllib.request.Request(
        HA_URL + path, method="POST" if body is not None else "GET",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode()


def plain(obj):
    return json.loads(json.dumps(obj))


def main():
    tok = token()
    if not tok:
        print(f"Kein Token (HA_TOKEN oder Schluesselbund-Eintrag '{KEYCHAIN_SERVICE}'), "
              "Live-Check uebersprungen.")
        return 2
    try:
        states = {s["entity_id"]: s["state"] for s in json.loads(api(tok, "/api/states"))}
    except (urllib.error.URLError, OSError) as e:
        print(f"{HA_URL} nicht erreichbar oder Token ungueltig: {e}")
        return 2

    errors, warnings, n_tpl = [], [], 0
    for f in dl.dashboard_files():
        rel = f.relative_to(dl.DASHBOARD_DIR.parent)
        doc = dl.load(f)

        for eid, line in sorted(dl.entities(doc).items(), key=lambda x: x[1]):
            if eid not in states:
                errors.append(f"{rel}:{line}: Entitaet {eid} existiert nicht")
            elif states[eid] == "unavailable":
                warnings.append(f"{rel}:{line}: {eid} ist unavailable")

        for path, s, card in dl.walk(doc):
            if not dl.is_jinja(s):
                continue
            n_tpl += 1
            variables = {"config": plain(card or {}), "user": "Test",
                         "entity": str((card or {}).get("entity", ""))}
            try:
                api(tok, "/api/template", {"template": s, "variables": variables})
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace").strip()
                errors.append(f"{rel}:{dl.line_of(s, card)} ({'.'.join(map(str, path[-3:]))}): "
                              f"Template-Fehler: {msg[:300]}")

    print(f"{len(states)} Entitaeten in HA, {n_tpl} Templates gerendert")
    for w in warnings:
        print("WARNUNG", w)
    for e in errors:
        print("FEHLER", e)
    print("OK" if not errors else f"{len(errors)} Fehler")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

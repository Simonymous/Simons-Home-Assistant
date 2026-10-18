#!/usr/bin/env python3
"""Stufe 1: statische Dashboard-Pruefung, braucht keine laufende HA-Instanz.

Prueft fuer jede YAML-Datei in dashboards/:
  - YAML laedt, jede Karte in einer cards-Liste hat einen type
  - jede custom:-Karte ist in installed_cards.yaml freigegeben
  - jedes Jinja-Template ist syntaktisch korrekt
  - jedes button-card-JS-Template ([[[ ... ]]]) ist syntaktisch korrekt (via node)
  - Pop-up-Hashes sind eindeutig, Navigationsziele (#hash, Views) existieren
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import jinja2
import yaml

sys.path.insert(0, str(Path(__file__).parent))
import dashboard_lib as dl  # noqa: E402

HERE = Path(__file__).parent
JS_CHECK = """
let src = '';
process.stdin.on('data', d => src += d).on('end', () => {
  const bad = [];
  for (const [i, body] of JSON.parse(src).entries()) {
    try { new Function('states', 'entity', 'user', 'hass', 'variables', 'html', 'helpers', body); }
    catch (e) { bad.push([i, e.message]); }
  }
  console.log(JSON.stringify(bad));
});
"""


def main():
    installed = yaml.safe_load((HERE / "installed_cards.yaml").read_text())
    allowed = {t for types in installed.values() for t in types}
    env = jinja2.Environment(extensions=["jinja2.ext.loopcontrols", "jinja2.ext.do"])
    errors, n_jinja, n_js = [], 0, 0

    for f in dl.dashboard_files():
        rel = f.relative_to(dl.DASHBOARD_DIR.parent)
        try:
            doc = dl.load(f)
        except yaml.YAMLError as e:
            errors.append(f"{rel}: YAML-Fehler: {e}")
            continue

        for card in dl.cards(doc):
            for key in ("cards", "card"):
                sub = card.get(key)
                for c in sub if isinstance(sub, list) else [sub] if isinstance(sub, dict) else []:
                    if isinstance(c, dict) and not c.get("type"):
                        errors.append(f"{rel}:{c.line}: Karte ohne type")
            t = str(card.get("type", ""))
            if t.startswith("custom:") and t not in allowed:
                errors.append(f"{rel}:{card.line}: {t} ist nicht installiert "
                              f"(installed_cards.yaml)")

        js = []
        for path, s, card in dl.walk(doc):
            where = f"{rel}:{dl.line_of(s, card)} ({'.'.join(map(str, path[-3:]))})"
            if dl.is_jinja(s):
                n_jinja += 1
                try:
                    env.parse(s)
                except jinja2.TemplateSyntaxError as e:
                    errors.append(f"{where}: Jinja-Fehler: {e.message}")
            m = dl.JS_RE.match(s)
            if m:
                js.append((where, m.group(1)))
        n_js += len(js)
        if js:
            if not shutil.which("node"):
                print("WARNUNG: node fehlt, JS-Templates ungeprueft")
            else:
                out = subprocess.run(["node", "-e", JS_CHECK], input=json.dumps([b for _, b in js]),
                                     capture_output=True, text=True, check=True).stdout
                for i, msg in json.loads(out):
                    errors.append(f"{js[i][0]}: JS-Fehler: {msg}")

        # Pop-ups muessen eigene Karten der View sein: in einer Karte mit Glas-Unschaerfe
        # (backdrop-filter) wird ihr position: fixed auf die Kartengroesse beschnitten.
        def nested_popups(node, inside=None):
            if isinstance(node, dict):
                if node.get("card_type") == "pop-up" and inside:
                    errors.append(f"{rel}:{node.line}: Pop-up {node.get('hash')} steckt in {inside} "
                                  "(als eigene Karte der View anlegen)")
                kind = node.get("type") if "type" in node and node is not doc else None
                for v in node.values():
                    nested_popups(v, inside or (kind if kind and str(kind) != "None" and node.get("card_type") != "pop-up" else None))
            elif isinstance(node, list):
                for v in node:
                    nested_popups(v, inside)
        for view in doc.get("views", []):
            for card in view.get("cards", []):
                for v in card.values():
                    nested_popups(v, card.get("type") if card.get("card_type") != "pop-up" else None)

        views = dl.views(doc)
        hashes = [h for v in views for h in v["hashes"]]
        for h in {h for h in hashes if hashes.count(h) > 1}:
            errors.append(f"{rel}: Pop-up-Hash {h} mehrfach vergeben")
        view_paths = {f"/{dl.DASHBOARD_URL_PATH}/{v['path']}" for v in views}
        for path, s, card in dl.walk(doc):
            if path and path[-1] == "navigation_path":
                if s.startswith("#") and s not in hashes:
                    errors.append(f"{rel}:{dl.line_of(s, card)}: Pop-up {s} existiert nicht")
                if s.startswith(f"/{dl.DASHBOARD_URL_PATH}/") and s.split("#")[0] not in view_paths:
                    errors.append(f"{rel}:{dl.line_of(s, card)}: View {s} existiert nicht")

        print(f"{rel}: {len(views)} Views, {len(hashes)} Pop-ups, "
              f"{len(dl.entities(doc))} Entitaeten")

    print(f"{n_jinja} Jinja-Templates, {n_js} JS-Templates geprueft")
    for e in errors:
        print("FEHLER", e)
    print("OK" if not errors else f"{len(errors)} Fehler")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

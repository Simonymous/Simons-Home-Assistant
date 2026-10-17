"""Gemeinsame Helfer fuer die Dashboard-Tests: YAML laden (mit Zeilennummern),
Karten durchlaufen, Entitaeten / Jinja-Templates / JS-Templates einsammeln."""

import os
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = Path(os.environ.get("DASHBOARD_DIR", REPO / "dashboards"))
DASHBOARD_URL_PATH = "dashboard-reinigung"  # aus configuration.yaml (lovelace.dashboards)

ENTITY_DOMAINS = (
    "automation binary_sensor button calendar camera climate counter cover device_tracker "
    "event fan image input_boolean input_button input_datetime input_number input_select "
    "input_text light lock media_player number person remote scene script select sensor "
    "siren switch text timer todo update vacuum valve water_heater weather zone"
).split()
ENTITY_RE = re.compile(
    r"(?<!\w)(" + "|".join(ENTITY_DOMAINS) + r")\.([a-z0-9_]+)(?![a-z0-9_{$(])"
)
JS_RE = re.compile(r"^\s*\[\[\[(.*)\]\]\]\s*$", re.S)


class Node(dict):
    line = 0


class Str(str):
    line = 0


class _Loader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    d = Node(loader.construct_mapping(node, deep=True))
    d.line = node.start_mark.line + 1
    return d


def _scalar(loader, node):
    v = loader.construct_scalar(node)
    s = Str(v)
    s.line = node.start_mark.line + 1
    return s


def _ha_tag(loader, suffix, node):
    # !include, !secret usw. existieren nur in HA; fuer die Tests ein Platzhalter.
    return Str(f"<{suffix} {getattr(node, 'value', '')}>")


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)
_Loader.add_constructor("tag:yaml.org,2002:str", _scalar)
_Loader.add_multi_constructor("!", _ha_tag)


def load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Loader)


def dashboard_files():
    return sorted(DASHBOARD_DIR.glob("*.yaml"))


def walk(obj, path=(), card=None):
    """Liefert (path, wert, naechste_umgebende_karte) fuer jeden String-Wert."""
    if isinstance(obj, dict):
        if "type" in obj:
            card = obj
        for k, v in obj.items():
            yield from walk(v, path + (str(k),), card)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + (i,), card)
    elif isinstance(obj, str):
        yield path, obj, card


def cards(obj):
    """Alle Dicts mit 'type' (Karten, Badges, Aktionen) inkl. Zeile."""
    if isinstance(obj, dict):
        if "type" in obj:
            yield obj
        for v in obj.values():
            yield from cards(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from cards(v)


def line_of(value, fallback=None):
    return getattr(value, "line", 0) or getattr(fallback, "line", 0)


def is_jinja(s):
    return ("{{" in s or "{%" in s) and not JS_RE.match(s)


def entities(doc):
    """{entity_id: erste Zeile} aus expliziten Feldern und Templates."""
    found = {}
    for path, s, card in walk(doc):
        if path and path[-1] in ("service", "action", "perform_action"):
            continue  # light.turn_on ist ein Dienst, keine Entitaet
        for m in ENTITY_RE.finditer(s):
            found.setdefault(m.group(0), line_of(s, card))
    return found


def views(doc):
    out = []
    for i, v in enumerate(doc.get("views", [])):
        out.append({"title": v.get("title", f"view {i}"), "path": str(v.get("path", i)),
                    "hashes": sorted({str(c["hash"]) for c in cards(v)
                                      if c.get("card_type") == "pop-up" and c.get("hash")})})
    return out


if __name__ == "__main__":
    # Manifest fuer den Rendertest: Views und Pop-ups je Dashboard-Datei
    import json
    print(json.dumps({"url_path": DASHBOARD_URL_PATH,
                      "views": [v for f in dashboard_files() for v in views(load(f))]}))

// neonplan-follow-card: zeigt eine NeonPlan-3D-Karte und oeffnet automatisch den Raum,
// den ein Sensor meldet, solange ein Geraet aktiv ist (z. B. der Saugroboter beim Reinigen).
// Danach geht die Ansicht zurueck zur Gesamtansicht.
//
//   type: custom:neonplan-follow-card
//   room_entity: sensor.bob_aktueller_raum      # Zustand = Raumname wie in NeonPlan
//   active_entity: vacuum.bob
//   active_states: [cleaning, paused]
//   room_aliases:                                # Sensor-Name -> NeonPlan-Raumname
//     Arbeitszimmer: Büro
//   card:                                        # normale neonplan3d-card-Optionen
//     height: 380
//
// NeonPlan bietet dafuer keine offizielle Schnittstelle. Die Raum-IDs kommen ueber die
// offizielle Websocket-API (neonplan3d/building/get); geoeffnet wird ueber die interne,
// reaktive Eigenschaft _roomId der Karte - dieselbe, die ein Tipp auf den Raum setzt.
// Aendert NeonPlan das, faellt nur das automatische Oeffnen weg, die Karte bleibt.
// Eingegriffen wird nur bei einem Raumwechsel, damit ein Tipp dazwischen stehen bleibt.

class NeonplanFollowCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      room_entity: "sensor.bob_aktueller_raum",
      active_entity: "vacuum.bob",
      active_states: ["cleaning", "paused"],
      room_aliases: {},
      ...config,
    };
    this._lastRoom = undefined;
    this._card = undefined;
    customElements.whenDefined("neonplan3d-card").then(() => {
      const card = document.createElement("neonplan3d-card");
      card.setConfig({ ...(this._config.card || {}), type: "custom:neonplan3d-card" });
      if (this._hass) card.hass = this._hass;
      this.replaceChildren(card);
      this._card = card;
      this._follow();
    });
  }

  set hass(hass) {
    this._hass = hass;
    if (this._card) this._card.hass = hass;
    this._follow();
  }

  async _roomIds() {
    if (!this._rooms) {
      this._rooms = this._hass
        .callWS({ type: "neonplan3d/building/get" })
        .then(({ building }) => {
          const map = new Map();
          for (const floor of building.floors) {
            for (const room of floor.rooms || []) {
              map.set(String(room.name).trim().toLowerCase(), { floorId: floor.id, roomId: room.id });
            }
          }
          return { map, floors: building.floors.length };
        })
        .catch(() => (this._rooms = undefined));
    }
    return this._rooms;
  }

  async _follow() {
    if (!this._hass || !this._card) return;
    const c = this._config;
    const active = c.active_states.includes(this._hass.states[c.active_entity]?.state);
    const raw = active ? this._hass.states[c.room_entity]?.state : null;
    const roomName = (raw && c.room_aliases[raw]) || raw;
    // Der Raumsensor meldet beim Fahren kurz unknown: dann Ansicht einfach stehen lassen
    if (active && ["unknown", "unavailable", "", undefined].includes(roomName)) return;
    if (roomName === this._lastRoom) return;
    this._lastRoom = roomName;

    const rooms = await this._roomIds();
    if (!rooms || roomName !== this._lastRoom) return; // inzwischen erneut gewechselt
    const target = roomName ? rooms.map.get(String(roomName).trim().toLowerCase()) : null;
    if (target) {
      if (rooms.floors > 1) this._card._floorId = target.floorId;
      this._card._roomId = target.roomId;
      this._following = true;
    } else if (this._following) {
      this._card._roomId = null; // fertig oder unbekannter Raum: zur Gesamtansicht
      this._following = false;
    }
  }

  getCardSize() {
    return this._card?.getCardSize?.() ?? Math.ceil((this._config?.card?.height ?? 420) / 50);
  }

  getGridOptions() {
    return this._card?.getGridOptions?.() ?? { columns: "full", min_rows: 4 };
  }
}

if (!customElements.get("neonplan-follow-card")) {
  customElements.define("neonplan-follow-card", NeonplanFollowCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "neonplan-follow-card",
    name: "NeonPlan Follow",
    description: "NeonPlan-3D-Karte, die dem Raum eines Sensors folgt (z. B. Saugroboter)",
  });
}

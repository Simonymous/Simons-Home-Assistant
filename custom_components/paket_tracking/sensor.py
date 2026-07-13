from __future__ import annotations

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN


class PaketBucketSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, manager, status: str, name: str, icon: str) -> None:
        self.manager = manager
        self.status = status
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{DOMAIN}_{status}"
        self.entity_id = f"sensor.pakete_{status}"

    @property
    def native_value(self) -> int:
        return len(self.manager.packages_for(self.status))

    @property
    def extra_state_attributes(self) -> dict:
        pakete = [
            {
                "carrier": p.get("carrier"),
                "beschreibung": p.get("description"),
                "erwartet": p.get("expected"),
                "aktualisiert": p.get("updated_at"),
            }
            for p in self.manager.packages_for(self.status)
        ]
        return {"pakete": pakete}

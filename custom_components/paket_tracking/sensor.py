from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import BUCKETS, DOMAIN, SENSOR_ICONS, SENSOR_NAMES


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    manager = hass.data[DOMAIN]
    entities = [
        PaketBucketSensor(manager, status, SENSOR_NAMES[status], SENSOR_ICONS[status])
        for status in BUCKETS
    ]
    for entity in entities:
        manager.entities[entity.status] = entity
    async_add_entities(entities)


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

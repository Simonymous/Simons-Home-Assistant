from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    EVENT_IMAP_CONTENT,
    HEUTE_MAX_AGE_DAYS,
    MAX_AGE_DAYS,
    STATUS_HEUTE,
    STATUS_ZUGESTELLT,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .parsers import parse_email

_LOGGER = logging.getLogger(__name__)

SERVICE_REMOVE_PACKAGE = "remove_package"
REMOVE_PACKAGE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("key"): cv.string,
            vol.Optional("query"): cv.string,
        }
    ),
    cv.has_at_least_one_key("key", "query"),
)


class PaketTrackingManager:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.packages: dict[str, dict] = {}
        self.entities: dict[str, Any] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load()
        self.packages = (data or {}).get("packages", {})

    def async_save(self) -> None:
        self._store.async_delay_save(lambda: {"packages": self.packages}, 5)

    def packages_for(self, status: str) -> list[dict]:
        return [
            {**pkg, "key": key}
            for key, pkg in self.packages.items()
            if pkg["status"] == status
        ]

    def remove_package(self, key: str | None, query: str | None) -> list[str]:
        removed: list[str] = []
        if key and self.packages.pop(key, None) is not None:
            removed.append(key)
        if query:
            needle = query.strip().lower()
            for pkg_key, pkg in list(self.packages.items()):
                if needle in (pkg.get("description") or "").lower():
                    self.packages.pop(pkg_key, None)
                    removed.append(pkg_key)
        if removed:
            self._notify_and_save()
        return removed

    @callback
    def handle_event(self, event: Event) -> None:
        data = event.data
        sender = data.get("sender") or data.get("from") or ""
        subject = data.get("subject") or ""
        text = data.get("text") or ""

        _LOGGER.debug(
            "imap_content empfangen: sender=%r subject=%r text_len=%d",
            sender,
            subject,
            len(text),
        )

        parsed = parse_email(sender, subject, text)
        if parsed is None:
            _LOGGER.debug("Keine passende Regel für sender=%r subject=%r", sender, subject)
            return

        if parsed.status == STATUS_ZUGESTELLT:
            if self.packages.pop(parsed.key, None) is not None:
                _LOGGER.debug("Paket %s als zugestellt entfernt", parsed.key)
                self._notify_and_save()
            return

        existing = self.packages.get(parsed.key, {})
        self.packages[parsed.key] = {
            "carrier": parsed.carrier,
            "status": parsed.status,
            "description": parsed.description or existing.get("description"),
            "expected": parsed.expected or existing.get("expected"),
            "updated_at": dt_util.now().isoformat(),
        }
        _LOGGER.debug("Paket %s -> %s (%s)", parsed.key, parsed.status, parsed.carrier)
        self._notify_and_save()

    def _notify_and_save(self) -> None:
        self.async_save()
        for entity in self.entities.values():
            entity.async_write_ha_state()

    @callback
    def async_prune_stale(self, _now=None) -> None:
        # Safety net for missed/unmatched "zugestellt" emails, so a parser gap
        # can't leave a package stuck in a bucket forever. "Heute" gets a much
        # tighter cutoff than the other buckets - an entry stuck there for days
        # means the delivery email was missed, not that it's still "today".
        now = dt_util.now()
        cutoff = now - timedelta(days=MAX_AGE_DAYS)
        heute_cutoff = now - timedelta(days=HEUTE_MAX_AGE_DAYS)
        stale = [
            key
            for key, pkg in self.packages.items()
            if (dt_util.parse_datetime(pkg.get("updated_at", "")) or now)
            < (heute_cutoff if pkg.get("status") == STATUS_HEUTE else cutoff)
        ]
        if not stale:
            return
        for key in stale:
            self.packages.pop(key, None)
        _LOGGER.debug("Entfernt %d veraltete Pakete (>%d Tage)", len(stale), MAX_AGE_DAYS)
        self._notify_and_save()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    manager = PaketTrackingManager(hass)
    await manager.async_load()
    hass.data[DOMAIN] = manager

    hass.async_create_task(
        discovery.async_load_platform(hass, Platform.SENSOR, DOMAIN, {}, config)
    )

    hass.bus.async_listen(EVENT_IMAP_CONTENT, manager.handle_event)
    async_track_time_interval(hass, manager.async_prune_stale, timedelta(hours=6))

    async def async_handle_remove_package(call: ServiceCall) -> None:
        key = call.data.get("key")
        query = call.data.get("query")
        removed = manager.remove_package(key, query)
        if removed:
            _LOGGER.info("Manuell entfernt (Service remove_package): %s", removed)
        else:
            _LOGGER.warning(
                "remove_package: kein Paket gefunden für key=%r query=%r", key, query
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_PACKAGE,
        async_handle_remove_package,
        schema=REMOVE_PACKAGE_SCHEMA,
    )

    return True

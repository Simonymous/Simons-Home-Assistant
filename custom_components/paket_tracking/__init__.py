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
    STATUS_UNTERWEGS,
    STATUS_ZUGESTELLT,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .parsers import ParsedEmail, parse_email

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

        if parsed.via_amazon and self._handle_amazon_via_dhl(parsed):
            return

        keys = (parsed.key, *parsed.extra_keys)
        if parsed.status == STATUS_ZUGESTELLT:
            # The delivery mail may name only the first order of a shared shipment,
            # the "In Zustellung" mail before it recorded the whole group.
            grouped = [k for k, pkg in self.packages.items() if parsed.key in pkg.get("group", ())]
            removed = [key for key in (*keys, *grouped) if self.packages.pop(key, None) is not None]
            if removed:
                _LOGGER.debug("Pakete %s als zugestellt entfernt", removed)
                self._notify_and_save()
            return

        # Other orders in the same shipment follow its status, but only if they
        # are already tracked - an extra number alone never creates an entry.
        group = [key for key in keys if key in self.packages or key == parsed.key]
        for key in parsed.extra_keys:
            if key in self.packages:
                self.packages[key]["status"] = parsed.status
                self.packages[key]["updated_at"] = dt_util.now().isoformat()
                self.packages[key]["group"] = group

        existing = self.packages.get(parsed.key, {})
        self.packages[parsed.key] = {
            "carrier": parsed.carrier,
            "status": parsed.status,
            "description": parsed.description or existing.get("description"),
            "expected": parsed.expected or existing.get("expected"),
            "updated_at": dt_util.now().isoformat(),
            **({"dhl": existing["dhl"]} if existing.get("dhl") else {}),
            **({"group": existing["group"]} if existing.get("group") else {}),
        }
        if parsed.extra_keys and len(group) > 1:
            self.packages[parsed.key]["group"] = group
        _LOGGER.debug("Paket %s -> %s (%s)", parsed.key, parsed.status, parsed.carrier)
        self._notify_and_save()

    def _handle_amazon_via_dhl(self, parsed: ParsedEmail) -> bool:
        # Amazon sends no delivery mail of its own when DHL carries the order, and
        # the DHL mails don't name the order. So the first DHL announcement is
        # linked to the oldest unlinked Amazon order in transit, later DHL mails
        # move that order along instead of tracking the parcel a second time.
        keys = {parsed.key, *parsed.extra_keys}
        amazon = {
            key: pkg
            for key, pkg in self.packages.items()
            if key.startswith("amazon:") and pkg["status"] in (STATUS_UNTERWEGS, STATUS_HEUTE)
        }
        target = next((key for key, pkg in amazon.items() if pkg.get("dhl") in keys), None)
        if target is None:
            linked = [key for key, pkg in amazon.items() if pkg.get("dhl")]
            unlinked = [key for key, pkg in amazon.items() if not pkg.get("dhl")]
            # A new announcement takes a fresh order. A "heute" or delivery mail
            # without a known number belongs to an order DHL already announced.
            if parsed.status == STATUS_UNTERWEGS:
                pool = unlinked
            else:
                pool = linked or unlinked
            if not pool:
                return False
            target = min(pool, key=lambda key: amazon[key].get("updated_at", ""))
            self.packages[target]["dhl"] = parsed.key

        if parsed.status == STATUS_ZUGESTELLT:
            self.packages.pop(target, None)
            _LOGGER.debug("Amazon-Paket %s per DHL zugestellt", target)
        else:
            self.packages[target]["status"] = parsed.status
            self.packages[target]["updated_at"] = dt_util.now().isoformat()
            _LOGGER.debug("Amazon-Paket %s per DHL -> %s", target, parsed.status)
        # A plain DHL entry for this parcel from before the link would hang otherwise.
        for key in keys:
            self.packages.pop(key, None)
        self._notify_and_save()
        return True

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

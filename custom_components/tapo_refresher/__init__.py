import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import CONF_PLUG_IP, DOMAIN
from .coordinator import TapoRebooterCoordinator

_LOGGER = logging.getLogger(__name__)

COORDINATORS: dict[str, TapoRebooterCoordinator] = {}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = TapoRebooterCoordinator(hass, entry.data)
    coordinator.start()
    COORDINATORS[entry.entry_id] = coordinator

    async def handle_clean_cache(call: ServiceCall) -> None:
        from tapo import ApiClient

        ip = call.data[CONF_PLUG_IP]
        action = call.data.get("action", "refresh_session")
        username = entry.data["username"]
        password = entry.data["password"]

        try:
            client = ApiClient(username, password)
            device = await client.p100(ip)
            if action == "reboot":
                await device.device_reboot(delay_s=1)
                _LOGGER.info("device_reboot() sent to %s", ip)
            else:
                await device.refresh_session()
                _LOGGER.info("refresh_session() succeeded on %s", ip)
        except Exception as e:
            _LOGGER.error("clean_cache failed on %s: %s", ip, e)

    hass.services.async_register(DOMAIN, "clean_cache", handle_clean_cache)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = COORDINATORS.pop(entry.entry_id, None)
    if coordinator:
        coordinator.stop()
    hass.services.async_remove(DOMAIN, "clean_cache")
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

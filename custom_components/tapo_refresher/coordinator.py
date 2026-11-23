import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval

from .const import (
    CONF_MOBILE_APP_DEVICE,
    CONF_NOTIFY_ON_SUCCESS,
    CONF_NOTIFY_SERVICE,
    CONF_PLUG_IP,
    CONF_PLUG_NAME,
    CONF_PLUGS,
    CONF_SCHEDULE_INTERVAL,
    CONF_SCHEDULE_TIME,
    CONF_SCHEDULE_UNIT,
    CONF_TELEGRAM_CHAT_ID,
    NOTIFY_MOBILE_APP,
    NOTIFY_TELEGRAM,
    SCHEDULE_UNIT_DAILY,
    SCHEDULE_UNIT_HOURS,
    SCHEDULE_UNIT_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


class TapoRebooterCoordinator:
    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self.hass = hass
        self._config = config
        self._cancel = None

    def start(self) -> None:
        unit = self._config[CONF_SCHEDULE_UNIT]
        interval = self._config.get(CONF_SCHEDULE_INTERVAL, 1)
        time_str = self._config.get(CONF_SCHEDULE_TIME, "03:00")

        if unit == SCHEDULE_UNIT_DAILY:
            hour, minute = (int(x) for x in time_str.split(":"))
            self._cancel = async_track_time_change(
                self.hass, self._handle_tick, hour=hour, minute=minute, second=0
            )
        else:
            delta = timedelta(
                minutes=interval if unit == SCHEDULE_UNIT_MINUTES else 0,
                hours=interval if unit == SCHEDULE_UNIT_HOURS else 0,
            )
            self._cancel = async_track_time_interval(self.hass, self._handle_tick, delta)

    def stop(self) -> None:
        if self._cancel:
            self._cancel()
            self._cancel = None

    @callback
    def _handle_tick(self, _now=None) -> None:
        self.hass.async_create_task(self._run())

    async def _run(self) -> None:
        from tapo import ApiClient

        username = self._config["username"]
        password = self._config["password"]
        plugs = self._config.get(CONF_PLUGS, [])
        notify_on_success = self._config.get(CONF_NOTIFY_ON_SUCCESS, False)

        results = []
        for plug in plugs:
            ip = plug[CONF_PLUG_IP]
            name = plug[CONF_PLUG_NAME]
            try:
                client = ApiClient(username, password)
                device = await client.p100(ip)
                await device.refresh_session()
                _LOGGER.info("refresh_session() succeeded on %s (%s)", name, ip)
                results.append((name, ip, None))
            except Exception as e:
                _LOGGER.error("refresh_session() failed on %s (%s): %s", name, ip, e)
                results.append((name, ip, str(e)))
                await self._notify(
                    f"Tapo plug '{name}' ({ip}) failed session refresh: {e}"
                )

        if notify_on_success:
            failed = [r for r in results if r[2] is not None]
            ok = [r for r in results if r[2] is None]
            if ok and not failed:
                await self._notify(
                    f"Tapo maintenance done: {len(ok)}/{len(results)} plugs refreshed successfully"
                )

    async def _notify(self, message: str) -> None:
        service = self._config.get(CONF_NOTIFY_SERVICE, NOTIFY_TELEGRAM)

        if service == NOTIFY_TELEGRAM:
            chat_id = self._config.get(CONF_TELEGRAM_CHAT_ID, "")
            await self.hass.services.async_call(
                "notify", "telegram",
                {"message": message, "data": {"chat_id": chat_id}},
            )
        elif service == NOTIFY_MOBILE_APP:
            device = self._config.get(CONF_MOBILE_APP_DEVICE, "")
            await self.hass.services.async_call(
                "notify", f"mobile_app_{device}",
                {"message": message},
            )

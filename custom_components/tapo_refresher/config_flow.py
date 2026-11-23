import ipaddress
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowResult

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
    DOMAIN,
    NOTIFY_MOBILE_APP,
    NOTIFY_TELEGRAM,
    SCHEDULE_UNIT_DAILY,
    SCHEDULE_UNIT_HOURS,
    SCHEDULE_UNIT_MINUTES,
)


def _validate_ip(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ValueError:
        return False


def _validate_time(t: str) -> bool:
    return bool(re.match(r"^\d{2}:\d{2}$", t))


class TapoRebooterConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._plugs: list[dict] = []

    async def async_step_user(self, user_input=None) -> FlowResult:
        return await self.async_step_credentials(user_input)

    async def async_step_credentials(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            # shortcut: we don't test auth here to keep install fast; coordinator will surface auth errors at runtime
            self._data["username"] = user_input["username"]
            self._data["password"] = user_input["password"]
            return await self.async_step_add_plug()

        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
            }),
            errors=errors,
        )

    async def async_step_add_plug(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            if not _validate_ip(user_input[CONF_PLUG_IP]):
                errors[CONF_PLUG_IP] = "invalid_ip"
            else:
                self._plugs.append({
                    CONF_PLUG_IP: user_input[CONF_PLUG_IP],
                    CONF_PLUG_NAME: user_input[CONF_PLUG_NAME],
                })
                return await self.async_step_add_another(user_input)

        return self.async_show_form(
            step_id="add_plug",
            data_schema=vol.Schema({
                vol.Required(CONF_PLUG_IP): str,
                vol.Required(CONF_PLUG_NAME): str,
            }),
            errors=errors,
        )

    async def async_step_add_another(self, last_plug=None) -> FlowResult:
        return self.async_show_menu(
            step_id="add_another",
            menu_options=["add_plug", "schedule"],
            description_placeholders={
                "name": last_plug[CONF_PLUG_NAME],
                "ip": last_plug[CONF_PLUG_IP],
            },
        )

    async def async_step_schedule(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            unit = user_input[CONF_SCHEDULE_UNIT]
            interval = user_input.get(CONF_SCHEDULE_INTERVAL, 1)
            time = user_input.get(CONF_SCHEDULE_TIME, "03:00")

            if unit == SCHEDULE_UNIT_MINUTES and interval < 5:
                errors[CONF_SCHEDULE_INTERVAL] = "minutes_min"
            elif unit != SCHEDULE_UNIT_DAILY and interval < 1:
                errors[CONF_SCHEDULE_INTERVAL] = "invalid_interval"
            elif unit == SCHEDULE_UNIT_DAILY and not _validate_time(time):
                errors[CONF_SCHEDULE_TIME] = "invalid_time"
            else:
                self._data[CONF_SCHEDULE_UNIT] = unit
                self._data[CONF_SCHEDULE_INTERVAL] = interval
                self._data[CONF_SCHEDULE_TIME] = time
                return await self.async_step_notifications()

        return self.async_show_form(
            step_id="schedule",
            data_schema=vol.Schema({
                vol.Required(CONF_SCHEDULE_UNIT, default=SCHEDULE_UNIT_DAILY): vol.In(
                    [SCHEDULE_UNIT_MINUTES, SCHEDULE_UNIT_HOURS, SCHEDULE_UNIT_DAILY]
                ),
                vol.Optional(CONF_SCHEDULE_INTERVAL, default=1): vol.Coerce(int),
                vol.Optional(CONF_SCHEDULE_TIME, default="03:00"): str,
            }),
            errors=errors,
        )

    async def async_step_notifications(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            self._data[CONF_NOTIFY_SERVICE] = user_input[CONF_NOTIFY_SERVICE]
            self._data[CONF_TELEGRAM_CHAT_ID] = user_input.get(CONF_TELEGRAM_CHAT_ID, "")
            self._data[CONF_MOBILE_APP_DEVICE] = user_input.get(CONF_MOBILE_APP_DEVICE, "")
            self._data[CONF_NOTIFY_ON_SUCCESS] = user_input.get(CONF_NOTIFY_ON_SUCCESS, False)
            self._data[CONF_PLUGS] = self._plugs

            return self.async_create_entry(title="Tapo Refresher", data=self._data)

        return self.async_show_form(
            step_id="notifications",
            data_schema=vol.Schema({
                vol.Required(CONF_NOTIFY_SERVICE, default=NOTIFY_TELEGRAM): vol.In(
                    [NOTIFY_TELEGRAM, NOTIFY_MOBILE_APP]
                ),
                vol.Optional(CONF_TELEGRAM_CHAT_ID, default=""): str,
                vol.Optional(CONF_MOBILE_APP_DEVICE, default=""): str,
                vol.Optional(CONF_NOTIFY_ON_SUCCESS, default=False): bool,
            }),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> "TapoRebooterOptionsFlow":
        return TapoRebooterOptionsFlow(config_entry)


class TapoRebooterOptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry
        self._plugs: list[dict] = list(config_entry.data.get(CONF_PLUGS, []))

    async def async_step_init(self, user_input=None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_plug", "remove_plug", "schedule", "notifications"],
        )

    async def async_step_add_plug(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            if not _validate_ip(user_input[CONF_PLUG_IP]):
                errors[CONF_PLUG_IP] = "invalid_ip"
            else:
                self._plugs.append({
                    CONF_PLUG_IP: user_input[CONF_PLUG_IP],
                    CONF_PLUG_NAME: user_input[CONF_PLUG_NAME],
                })
                return await self.async_step_add_another(user_input)

        return self.async_show_form(
            step_id="add_plug",
            data_schema=vol.Schema({
                vol.Required(CONF_PLUG_IP): str,
                vol.Required(CONF_PLUG_NAME): str,
            }),
            errors=errors,
        )

    async def async_step_add_another(self, last_plug=None) -> FlowResult:
        return self.async_show_menu(
            step_id="add_another",
            menu_options=["add_plug", "schedule"],
            description_placeholders={
                "name": last_plug[CONF_PLUG_NAME],
                "ip": last_plug[CONF_PLUG_IP],
            },
        )

    async def async_step_remove_plug(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._plugs = [p for p in self._plugs if p[CONF_PLUG_IP] != user_input["plug_to_remove"]]
            return self._save()

        options = {p[CONF_PLUG_IP]: f"{p[CONF_PLUG_NAME]} ({p[CONF_PLUG_IP]})" for p in self._plugs}
        return self.async_show_form(
            step_id="remove_plug",
            data_schema=vol.Schema({
                vol.Required("plug_to_remove"): vol.In(options),
            }),
        )

    async def async_step_schedule(self, user_input=None) -> FlowResult:
        errors = {}
        current = self._entry.data
        if user_input is not None:
            unit = user_input[CONF_SCHEDULE_UNIT]
            interval = user_input.get(CONF_SCHEDULE_INTERVAL, 1)
            time = user_input.get(CONF_SCHEDULE_TIME, "03:00")

            if unit == SCHEDULE_UNIT_MINUTES and interval < 5:
                errors[CONF_SCHEDULE_INTERVAL] = "minutes_min"
            elif unit != SCHEDULE_UNIT_DAILY and interval < 1:
                errors[CONF_SCHEDULE_INTERVAL] = "invalid_interval"
            elif unit == SCHEDULE_UNIT_DAILY and not _validate_time(time):
                errors[CONF_SCHEDULE_TIME] = "invalid_time"
            else:
                return self._save(schedule_unit=unit, schedule_interval=interval, schedule_time=time)

        return self.async_show_form(
            step_id="schedule",
            data_schema=vol.Schema({
                vol.Required(CONF_SCHEDULE_UNIT, default=current.get(CONF_SCHEDULE_UNIT, SCHEDULE_UNIT_DAILY)): vol.In(
                    [SCHEDULE_UNIT_MINUTES, SCHEDULE_UNIT_HOURS, SCHEDULE_UNIT_DAILY]
                ),
                vol.Optional(CONF_SCHEDULE_INTERVAL, default=current.get(CONF_SCHEDULE_INTERVAL, 1)): vol.Coerce(int),
                vol.Optional(CONF_SCHEDULE_TIME, default=current.get(CONF_SCHEDULE_TIME, "03:00")): str,
            }),
            errors=errors,
        )

    async def async_step_notifications(self, user_input=None) -> FlowResult:
        current = self._entry.data
        if user_input is not None:
            return self._save(
                notify_service=user_input[CONF_NOTIFY_SERVICE],
                telegram_chat_id=user_input.get(CONF_TELEGRAM_CHAT_ID, ""),
                mobile_app_device=user_input.get(CONF_MOBILE_APP_DEVICE, ""),
                notify_on_success=user_input.get(CONF_NOTIFY_ON_SUCCESS, False),
            )

        return self.async_show_form(
            step_id="notifications",
            data_schema=vol.Schema({
                vol.Required(CONF_NOTIFY_SERVICE, default=current.get(CONF_NOTIFY_SERVICE, NOTIFY_TELEGRAM)): vol.In(
                    [NOTIFY_TELEGRAM, NOTIFY_MOBILE_APP]
                ),
                vol.Optional(CONF_TELEGRAM_CHAT_ID, default=current.get(CONF_TELEGRAM_CHAT_ID, "")): str,
                vol.Optional(CONF_MOBILE_APP_DEVICE, default=current.get(CONF_MOBILE_APP_DEVICE, "")): str,
                vol.Optional(CONF_NOTIFY_ON_SUCCESS, default=current.get(CONF_NOTIFY_ON_SUCCESS, False)): bool,
            }),
        )

    def _save(self, **overrides) -> FlowResult:
        new_data = {**self._entry.data, CONF_PLUGS: self._plugs, **overrides}
        return self.async_create_entry(title="", data=new_data)

from homeassistant import config_entries, core
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityDescription,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
)
from .dirigera_lib_patch import HubX
from .const import DOMAIN
import logging
logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("COVER Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger.debug(config)

    hub = HubX(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    blinds = []

    hub_blinds = await hass.async_add_executor_job(hub.get_blinds)
    blinds = [ikea_blind(hub, light) for light in hub_blinds]

    logger.debug("Found {} light entities to setup...".format(len(blinds)))
    async_add_entities(blinds)
    logger.debug("BLIND Complete async_setup_entry")

class ikea_blind(CoverEntity):
    def __init__(self, hub, json_data) -> None:
        logger.debug("IKEA Cover Created")
        self._hub = hub
        self._json_data = json_data
        self.set_state()

    def set_state(self):
        can_receive = self._json_data.capabilities.can_receive
        logger.debug("Got can_receive in state")
        logger.debug(can_receive)
        for cap in can_receive:
            if cap == "lightLevel":
                color_modes.append(ColorMode.BRIGHTNESS)
            elif cap == "colorTemperature":
                color_modes.append(ColorMode.COLOR_TEMP)
            elif cap == "colorHue" or cap == "colorSaturation":
                color_modes.append(ColorMode.HS)

        self._supported_color_modes = color_modes
        logger.debug("supported color mode set to ")
        logger.debug(self._supported_color_modes)

    @property
    def unique_id(self):
        return self._json_data.id

    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform",self._json_data.id)},
            name = self._json_data.attributes.custom_name,
            manufacturer = self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model ,
            sw_version=self._json_data.attributes.firmware_version
        )

    @property
    def name(self):
        return self._json_data.attributes.custom_name

    @property
    def level(self):
        scaled = int(self._json_data.attributes.blinds_current_level)

    def update(self):
        try:
            self._json_data = self._hub.get_light_by_id(self._json_data.id)
            self.set_state()
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
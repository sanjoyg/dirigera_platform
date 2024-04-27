import logging

from dirigera import Hub
from dirigera.devices.outlet import Outlet

from homeassistant import config_entries, core
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .mocks.ikea_outlet_mock import ikea_outlet_mock
from .common_classes import ikea_base_device
logger = logging.getLogger("custom_components.dirigera_platform")


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("SWITCH Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    # hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    hub = Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    outlets = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":
        logger.warning("Setting up mock outlets...")
        mock_outlet1 = ikea_outlet_mock(hub, "mock_outlet1")
        outlets = [mock_outlet1]
    else:
        hub_outlets : list[Outlet]  = await hass.async_add_executor_job(hub.get_outlets)
        outlets = [ikea_outlet(hass, hub, outlet) for outlet in hub_outlets]

    logger.debug("Found {} outlet entities to setup...".format(len(outlets)))
    async_add_entities(outlets)
    logger.debug("SWITCH Complete async_setup_entry")

class ikea_outlet(ikea_base_device, SwitchEntity):
    def __init__(self, hass, hub, json_data):
        super().__init__(hass, hub, json_data, hub.get_outlet_by_id)

    async def async_turn_on(self):
        logger.debug("outlet turn_on")
        try:
            await self.hass.async_add_executor_job(self._json_data.set_on, True)
        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_turn_off(self):
        logger.debug("outlet turn_off")
        try:
            await self.hass.async_add_executor_job(self._json_data.set_on, False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")
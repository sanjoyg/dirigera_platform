from homeassistant.components.switch import SwitchEntity
from homeassistant import config_entries, core
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError

from .const import DOMAIN
from .mocks.ikea_outlet_mock import ikea_outlet_mock

import dirigera
import logging
logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry,async_add_entities,):
    logger.debug("SWITCH setup entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    outlets = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":   
        logger.warning("Setting up mock outlets...")
        mock_outlet1 = ikea_outlet_mock(hub,"sanjoy")
        mock_outlet2 = ikea_outlet_mock(hub,"ekta")
        outlets = [mock_outlet1,mock_outlet2] 
    else:
        hub_outlets = await hass.async_add_executor_job(hub.get_outlets)
        outlets = [ikea_outlet(hub, outlet) for outlet in hub_outlets]
    
    logger.debug("Found {} outlet entities to setup...".format(len(outlets)))
    async_add_entities(outlets)
    
class ikea_outlet(SwitchEntity):
    def __init__(self, hub, hub_outlet):
        self._hub = hub 
        self._hub_outlet = hub_outlet
    
    @property
    def name(self) -> str:
        return self._hub_outlet.attributes.custom_name
    
    @property
    def available(self):
        return self._hub_outlet.is_reachable
    
    @property
    def is_on(self):
        return self._hub_outlet.attributes.is_on
    
    def turn_on(self):
        logger.debug("outlet turn_on")
        try:
            self._hub_outlet.set_on(True)
        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
    
    def turn_off(self):
        try:
            self._hub_outlet.set_on(False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
    
    def update(self):
        logger.debug("outlet update...")
        try:
            self._hub_outlet = self._hub.get_outlet_by_id(self._hub_outlet.id)
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
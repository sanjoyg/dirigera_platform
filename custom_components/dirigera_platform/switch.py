from homeassistant.components.switch import SwitchEntity
from homeassistant import config_entries, core
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .mocks.ikea_outlet_mock import ikea_outlet_mock

import dirigera
from .dirigera_lib_patch import HubX

import logging
logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry,async_add_entities,):
    logger.debug("SWITCH Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    #hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    hub = HubX(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    
    outlets = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":   
        logger.warning("Setting up mock outlets...")
        mock_outlet1 = ikea_outlet_mock(hub,"mock_outlet1")
        mock_outlet2 = ikea_outlet_mock(hub,"mock_outlet2")
        outlets = [mock_outlet1,mock_outlet2] 
    else:
        hub_outlets = await hass.async_add_executor_job(hub.get_outlets)
        outlets = [ikea_outlet(hub, outlet) for outlet in hub_outlets]
    
    logger.debug("Found {} outlet entities to setup...".format(len(outlets)))
    async_add_entities(outlets)
    logger.debug("SWITCH Complete async_setup_entry")
    
class ikea_outlet(SwitchEntity):
    def __init__(self, hub, json_data):
        logger.debug("ikea_outlet ctor...")
        self._hub = hub 
        self._json_data = json_data

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
    def is_on(self):
        return self._json_data.attributes.is_on
    
    def turn_on(self):
        logger.debug("outlet turn_on")
        try:
            self._json_data.set_on(True)
        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
    
    def turn_off(self):
        logger.debug("outlet turn_off")
        try:
            self._json_data.set_on(False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
    
    def update(self):
        logger.debug("outlet update...")
        try:
            self._json_data = self._hub.get_outlet_by_id(self._json_data.id)
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
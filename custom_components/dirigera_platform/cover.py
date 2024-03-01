from homeassistant.components.cover import CoverEntity, CoverEntityFeature, CoverDeviceClass

from homeassistant import config_entries, core
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .mocks.ikea_blinds_mock import ikea_blinds_mock

from .dirigera_lib_patch import HubX

import logging
logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry,async_add_entities,):
    logger.debug("BLINDS Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    #hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    hub = HubX(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    
    blinds = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":   
        logger.warning("Setting up mock blinds...")
        mock_blind1 = ikea_blinds_mock(hub,"mock_blind1")
        blinds = [mock_blind1] 
    else:
        hub_blinds = await hass.async_add_executor_job(hub.get_blinds)
        blinds = [ikea_blinds(hub, blind) for blind in hub_blinds]
    
    logger.debug("Found {} blinds entities to setup...".format(len(blinds)))
    async_add_entities(blinds)
    logger.debug("BLINDS Complete async_setup_entry")
    
class ikea_blinds(CoverEntity):
    def __init__(self, hub, json_data):
        logger.debug("ikea_blinds ctor...")
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
    def device_class(self) -> str:
        return CoverDeviceClass.BLIND
    
    @property
    def supported_features(self):
        return CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION

    @property
    def name(self):
        return self._json_data.attributes.custom_name 
    
    @property
    def is_on(self):
        return self._json_data.attributes.is_on
    
    @property
    def current_cover_position(self):
        return self._json_data.attributes.blinds_current_level
    
    @property 
    def target_cover_position(self):
        return self._json_data.attributes.blinds_target_level
    
    @property
    def is_closed(self):
        if self.current_cover_position is None:
            return False 
        return self.current_cover_position == 100 
    
    @property
    def is_closing(self):
        if self.current_cover_position is None or self.target_cover_position is False:
            return False 
        
        if self.current_cover_position != 100 and self.target_cover_position == 100:
            return True
             
        return False 
    
    @property
    def is_opening(self):
        if self.current_cover_position is None or self.target_cover_position is False:
            return False 
        
        if self.current_cover_position != 0 and self.target_cover_position == 0:
            return True    
    
        return False 

    def open_cover(self, **kwargs):
        self._json_data.set_target_position(0)
        
    def close_cover(self, **kwargs):
        self._json_data.set_target_position(100)
    
    def set_cover_position(self, **kwargs):
        position = int(kwargs['position'])
        if position >= 0 and position <= 100:
            self._json_data.set_target_level(position)

    def update(self):
        logger.debug("cover update...")
        try:
            self._json_data = self._hub.get_blinds_by_id(self._json_data.id)
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")

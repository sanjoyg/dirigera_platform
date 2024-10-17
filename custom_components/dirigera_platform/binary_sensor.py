import logging

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from .const import DOMAIN, PLATFORM
from .base_classes import  ikea_starkvind_air_purifier_binary_sensor, ikea_motion_sensor, ikea_open_close_sensor, ikea_water_sensor
from .ikea_gateway import ikea_gateway

logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("Binary Sensor Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    platform : ikea_gateway  = hass.data[DOMAIN][PLATFORM]
    
    async_add_entities([ikea_motion_sensor(x) for x in platform.motion_sensors])
    async_add_entities([ikea_open_close_sensor(x) for x in platform.open_close_sensors])
    async_add_entities([ikea_water_sensor(x) for x in platform.water_sensors])
    
    async_add_entities([ 
                    ikea_starkvind_air_purifier_binary_sensor(
                            device,
                            BinarySensorDeviceClass.PROBLEM,
                            "Filter Alarm Status",
                            "filter_alarm_status",
                            "mdi:alarm-light-outline")
                    for device in platform.air_purifiers])
   
    logger.debug("Binary Sensor Complete async_setup_entry")
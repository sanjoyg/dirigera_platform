import logging

from dirigera import Hub

from homeassistant import config_entries, core

from .const import DOMAIN, PLATFORM
from .base_classes import ikea_starkvind_air_purifier_fan

logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,):
    
    logger.debug("FAN/AirPurifier Starting async_setup_entry")
    
    air_purifier_devices = hass.data[DOMAIN][PLATFORM].air_purifiers
    fan_sensors = [ikea_starkvind_air_purifier_fan(x) for x in air_purifier_devices]    
    logger.debug(f"Found {len(fan_sensors)} air purifier fan sensors to add...")
    
    async_add_entities(fan_sensors)
    logger.debug("FAN/AirPurifier Complete async_setup_entry")
    return 
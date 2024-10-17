import logging

from homeassistant import config_entries, core

from .const import DOMAIN, PLATFORM
from .base_classes import ikea_blinds_sensor

logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("BLINDS Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    
    devices = hass.data[DOMAIN][PLATFORM].blinds
    
    blinds_sensors = [ikea_blinds_sensor(x) for x in devices]        
    logger.debug(f"Found {len(blinds_sensors)} blinds sensors to setup...")
    
    async_add_entities(blinds_sensors)    
    logger.debug("BLINDS Complete async_setup_entry")
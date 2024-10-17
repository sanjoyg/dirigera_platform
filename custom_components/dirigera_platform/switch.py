import logging

from homeassistant import config_entries, core

from .const import DOMAIN, PLATFORM
from .base_classes import ikea_outlet_switch_sensor
from .ikea_gateway import ikea_gateway
from .base_classes import ikea_starkvind_air_purifier_switch_sensor

logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("SWITCH Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    platform : ikea_gateway  = hass.data[DOMAIN][PLATFORM]
    
    async_add_entities([ikea_outlet_switch_sensor(x) for x in platform.outlets])
    
    # Add the air_purifier switches
    air_purifier_entities = []
    for air_purifier in platform.air_purifiers:
        air_purifier_entities.append(
            ikea_starkvind_air_purifier_switch_sensor(
                air_purifier,
                "Child Lock",
                "child_lock",
                "async_set_child_lock",
                "mdi:account-lock-outline",
            )
        )
        air_purifier_entities.append(
            ikea_starkvind_air_purifier_switch_sensor(
                air_purifier,
                "Status Light",
                "status_light",
                "async_set_status_light",
                "mdi:lightbulb",
            )
        )
    
    logger.debug(f"Found {len(air_purifier_entities)} air_purifier switch sensors...")
    async_add_entities(air_purifier_entities)

    logger.debug("SWITCH Complete async_setup_entry")
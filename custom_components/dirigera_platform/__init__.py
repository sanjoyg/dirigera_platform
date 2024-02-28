"""Platform for IKEA dirigera hub integration."""
from __future__ import annotations
import voluptuous as vol
import asyncio

# Import the device class from the component that you want to support
from homeassistant.core import HomeAssistant
from homeassistant import config_entries, core
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import PLATFORM_SCHEMA
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

import logging
logger = logging.getLogger("custom_components.dirigera_platform")

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Required(CONF_TOKEN): cv.string,
})

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    logger.debug("Starting async_setup...")
    logger.debug(config)
    logger.debug("Complete async_setup...")

    def handle_dump_data(call):
        import dirigera
        logger.info("=== START Devices JSON ===")

        # we could have multiple hubs set up
        for key in hass.data[DOMAIN].keys():
            logger.info("--------------")
            config_data = hass.data[DOMAIN][key]
            ip = config_data[CONF_IP_ADDRESS]
            token = config_data[CONF_TOKEN]
            if ip == "mock":
                logger.info("{ MOCK JSON }")
            else:
                hub = dirigera.Hub(token, ip) 
                json_resp = hub.get("/devices")
                logger.info(json_resp)
            logger.info("--------------")
            
        logger.info("=== END Devices JSON ===")
    
    hass.services.async_register(DOMAIN, "dump_data", handle_dump_data)     
    return True

async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    logger.debug("Staring async_setup_entry in init...")
    logger.debug(dict(entry.data))

    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)

    logger.debug("hass_data")
    logger.debug(hass_data)
    
    ip = hass_data[CONF_IP_ADDRESS]
    
    # Registers update listener to update config entry when options are updated.
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    
    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    hass_data["unsub_options_update_listener"] = unsub_options_update_listener
    hass.data[DOMAIN][entry.entry_id] = hass_data
    
    # Setup the entities
    #hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "light"))
    #hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "switch"))
    #hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "binary_sensor"))
    #hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "sensor"))
    #hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "cover"))
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "fan"))
    
    logger.debug("Complete async_setup_entry...")

    return True

async def options_update_listener(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry):
    logger.debug("In options_update_listener")
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    logger.debug("Starting async_unload_entry")
    
    """Unload a config entry."""
    unload_ok = all(
        [await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, "light"),
              hass.config_entries.async_forward_entry_unload(entry, "switch"),
              hass.config_entries.async_forward_entry_unload(entry, "binary_sensor"),
              hass.config_entries.async_forward_entry_unload(entry, "sensor"),
              hass.config_entries.async_forward_entry_unload(entry, "cover"),
              hass.config_entries.async_forward_entry_unload(entry, "fan")
              ]
        )]
    )
    # Remove options_update_listener.
    hass.data[DOMAIN][entry.entry_id]["unsub_options_update_listener"]()
    hass.data[DOMAIN].pop(entry.entry_id)
    logger.debug("Successfully popped entry")
    logger.debug("Complete async_unload_entry")

    return unload_ok

async def async_remove_config_entry_device( hass: HomeAssistant, config_entry: config_entries.ConfigEntry, device_entry: config_entries.DeviceEntry) -> bool:
    logger.info("Got request to remove device")
    logger.info(config_entry)
    logger.info(device_entry)
    return True 
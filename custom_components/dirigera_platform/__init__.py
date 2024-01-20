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

from .const import DOMAIN

import logging
logger = logging.getLogger("custom_components.dirigera_platform")

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Required(CONF_TOKEN): cv.string,
})

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    logger.debug("In init asetup...")
    logger.debug(config)
    logger.debug("asetup complete...")
    return True

async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    logger.debug("Staring async_setup_entry...")

    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)

    logger.debug(hass_data)
    
    # Registers update listener to update config entry when options are updated.
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    
    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    hass_data["unsub_options_update_listener"] = unsub_options_update_listener
    hass.data[DOMAIN][entry.entry_id] = hass_data

    # Setup the entities
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "light"))
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "switch"))

    return True

async def options_update_listener(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry):
    logger.debug("Starting options_update_listener")
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    logger.debug("Starting async_unload_entry")
    """Unload a config entry."""
    unload_ok = all(
        [await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, "light"),
              hass.config_entries.async_forward_entry_unload(entry, "switch")]
        )]
    )
    # Remove options_update_listener.
    hass.data[DOMAIN][entry.entry_id]["unsub_options_update_listener"]()
    hass.data[DOMAIN].pop(entry.entry_id)
    logger.debug("successfully popped")
    return unload_ok
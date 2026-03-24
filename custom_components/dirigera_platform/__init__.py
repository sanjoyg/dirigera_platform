"""Platform for IKEA dirigera hub integration."""
from __future__ import annotations

import asyncio
import logging

from dirigera import Hub 
from .dirigera_lib_patch import HubX

from .ikea_gateway import ikea_gateway

import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.light import PLATFORM_SCHEMA
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN, Platform

# Import the device class from the component that you want to support
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_HIDE_DEVICE_SET_BULBS, PLATFORM, DISCOVERY_COORDINATOR
from .hub_event_listener import hub_event_listener
from .device_discovery import DeviceDiscoveryCoordinator, set_discovery_coordinator

PLATFORMS_TO_SETUP = [  Platform.SWITCH, 
                        Platform.BINARY_SENSOR, 
                        Platform.LIGHT, 
                        Platform.SENSOR, 
                        Platform.COVER, 
                        Platform.FAN,
                        Platform.SCENE]

logger = logging.getLogger("custom_components.dirigera_platform")

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_IP_ADDRESS): cv.string,
        vol.Required(CONF_TOKEN): cv.string,
        vol.Optional(CONF_HIDE_DEVICE_SET_BULBS, default=True): cv.boolean
    }
)

hub_events = None 

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    logger.debug("Starting async_setup...")
    #for k in config.keys():
    #    logger.debug(f"config key: {k} value: {config[k]}")
    logger.debug("Complete async_setup...")

    def handle_dump_data(call):
        import dirigera

        logger.info("=== START Devices JSON ===")
        key = list(hass.data[DOMAIN].keys())[0]
        
        config_data = hass.data[DOMAIN][key]
        ip = config_data[CONF_IP_ADDRESS]
        token = config_data[CONF_TOKEN]
        
        logger.info("--------------")
        if ip == "mock":
            logger.info("{ MOCK JSON }")
        else:
            hub = dirigera.Hub(token, ip)
            json_resp = hub.get("/devices")
            logger.debug(f"TYPE IS {type(json_resp)}")
            #import json 
            #devices_json = json.loads(json_resp)
            # Sanitize the dump
                    
            master_id_map = {}
            id_counter = 1
            for device_json in json_resp:
                if "id" in device_json:
                    id_value = device_json["id"]
                    id_to_replace = id_counter 
                    
                    if id_value in master_id_map:
                        id_to_replace = master_id_map[id_value]
                    else:
                        id_counter = id_counter + 1
                        master_id_map[id_value] = id_to_replace
                    
                    device_json["id"] = id_to_replace
                    
                if "relationId" in device_json:
                    id_value = device_json["relationId"]
                    id_to_replace = id_counter 
                    
                    if id_value in master_id_map:
                        id_to_replace = master_id_map[id_value]
                    else:
                        id_counter = id_counter + 1
                        master_id_map[id_value] = id_to_replace
                    
                    device_json["id"] = id_to_replace
                
                if "attributes" in device_json and "serialNumber" in device_json["attributes"]:
                    id_value = device_json["attributes"]["serialNumber"]
                    id_to_replace = id_counter 
                    
                    if id_value in master_id_map:
                        id_to_replace = master_id_map[id_value]
                    else:
                        id_counter = id_counter + 1
                        master_id_map[id_value] = id_to_replace
                    
                    device_json["attributes"]["serialNumber"] = id_to_replace
                
                if "room" in device_json and "id" in device_json["room"]:
                    id_value = device_json["room"]["id"]
                    id_to_replace = id_counter 
                    
                    if id_value in master_id_map:
                        id_to_replace = master_id_map[id_value]
                    else:
                        id_counter = id_counter + 1
                        master_id_map[id_value] = id_to_replace
                    
                    device_json["room"]["id"] = id_to_replace
                
                if "deviceSet" in device_json:
                    for device_set in device_json["deviceSet"]:
                        if "id" in device_set:
                            id_value = device_set["id"]
                            id_to_replace = id_counter 
                            
                            if id_value in master_id_map:
                                id_to_replace = master_id_map[id_value]
                            else:
                                id_counter = id_counter + 1
                                master_id_map[id_value] = id_to_replace
                            
                            device_set["id"]= id_to_replace
                
                if "remote_link" in device_json["remoteLinks"]:
                    for remote_link in device_json["remoteLinks"]:
                        id_value = device_set["id"]
                        id_to_replace = id_counter 
                        
                        if id_value in master_id_map:
                            id_to_replace = master_id_map[id_value]
                        else:
                            id_counter = id_counter + 1
                            master_id_map[id_value] = id_to_replace
                        
                        remote_link["id"]= id_to_replace
                
            logger.info(json_resp)
        logger.info("--------------")


    hass.services.async_register(DOMAIN, "dump_data", handle_dump_data)
    return True


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    global hub_events
    """Set up platform from a ConfigEntry."""
    logger.info("Staring async_setup_entry in init...")
    
    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)

    # for backward compatibility
    hide_device_set_bulbs : bool = True 
    if CONF_HIDE_DEVICE_SET_BULBS in hass_data:
         logger.debug("Found HIDE_DEVICE_SET *****  ")
         #logger.debug(hass_data)
         hide_device_set_bulbs = hass_data[CONF_HIDE_DEVICE_SET_BULBS]
    else:
        logger.debug("Not found HIDE_DEVICE_SET *****  ")
        # If its not with HASS update it
        hass_data[CONF_HIDE_DEVICE_SET_BULBS] = hide_device_set_bulbs

    ip = hass_data[CONF_IP_ADDRESS]
    # Registers update listener to update config entry when options are updated.
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    hass_data["unsub_options_update_listener"] = unsub_options_update_listener
    hass.data[DOMAIN][entry.entry_id] = hass_data

    hass_data = dict(entry.data)
    hub = HubX(hass_data[CONF_TOKEN], hass_data[CONF_IP_ADDRESS])
    
    # Lets get all kinds that we are interested in one go and create the devices
    # such that the platform can go ahead and add the associated sensors
    platform = ikea_gateway()
    hass.data[DOMAIN][PLATFORM] = platform 
    logger.debug("Starting make_devices...")
    try:
        await platform.make_devices(hass,hass_data[CONF_IP_ADDRESS], hass_data[CONF_TOKEN])
    except (ConnectionError, OSError) as err:
        raise ConfigEntryNotReady(
            f"Cannot connect to IKEA Dirigera hub at {hass_data[CONF_IP_ADDRESS]}: {err}"
        ) from err
    
    #await hass.async_add_executor_job(platform.make_devices,hass, hass_data[CONF_IP_ADDRESS], hass_data[CONF_TOKEN])

    # Initialize the discovery coordinator BEFORE platform setup
    # so platforms can register their callbacks during async_setup_entry
    discovery = DeviceDiscoveryCoordinator(hass, hub)
    hass.data[DOMAIN][DISCOVERY_COORDINATOR] = discovery
    set_discovery_coordinator(discovery)
    logger.debug("Device discovery coordinator initialized")

    # Setup the entities - each platform will register its callback with discovery coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_TO_SETUP)

    # Now lets start the event listener
    hub_basic = Hub(hass_data[CONF_TOKEN], hass_data[CONF_IP_ADDRESS])

    if hass_data[CONF_IP_ADDRESS] != "mock":
        hub_events = hub_event_listener(hub_basic, hass, discovery)
        hub_events.start()
        # Sync device areas from Dirigera rooms to HA device registry
        # This ensures areas are set correctly after HA restart
        await hub_events.sync_all_device_areas()

    logger.debug("Complete async_setup_entry...")

    return True

async def options_update_listener(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    logger.debug("**********In options_update_listener")
    logger.debug(config_entry)
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    global hub_events
    # Called during re-load and delete
    logger.debug("Starting async_unload_entry")

    #Stop the listener
    if hub_events is not None:
        hub_events.stop()
        hub_events = None 

    hass_data = dict(entry.data)
    hub = HubX(hass_data[CONF_TOKEN], hass_data[CONF_IP_ADDRESS])
    
    # For each controller if there is an empty scene delete it
    logger.debug("In unload so forcing delete of scenes...")
    await hass.async_add_executor_job(hub.delete_empty_scenes)
    logger.debug("Done deleting empty scenes....")
    
    """Unload a config entry."""
    unload_ok = all(
        [
            await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_unload(entry, "light"),
                    hass.config_entries.async_forward_entry_unload(entry, "switch"),
                    hass.config_entries.async_forward_entry_unload(entry, "binary_sensor"),
                    hass.config_entries.async_forward_entry_unload(entry, "sensor"),
                    hass.config_entries.async_forward_entry_unload(entry, "cover"),
                    hass.config_entries.async_forward_entry_unload(entry, "fan"),
                    hass.config_entries.async_forward_entry_unload(entry, "scene"),
                ]
            )
        ]
    )
    
    hass.data[DOMAIN][entry.entry_id]["unsub_options_update_listener"]()
    hass.data[DOMAIN].pop(entry.entry_id)
    logger.debug("Successfully popped entry")
    logger.debug("Complete async_unload_entry")

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    device_entry: config_entries.DeviceEntry,
) -> bool:

    logger.info("Got request to remove device")
    logger.info(config_entry)
    logger.info(device_entry)
    return True
from __future__ import annotations
import logging
import re
import voluptuous as vol
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity_registry as er

from homeassistant.const import CONF_TYPE, CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, ATTR_ENTITY_ID
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.components.homeassistant.triggers import state as state_trigger
from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA

from .const import DOMAIN
from .hub_event_listener import hub_event_listener

logger = logging.getLogger("custom_components.dirigera_platform")

CONTROLLER_TRIGGER_TYPES = ["single_click", "long_press", "double_click"]
LIGHT_TRIGGER_TYPES = ["turned_on", "turned_off"]
TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend({vol.Required(CONF_TYPE): cv.string, vol.Required(ATTR_ENTITY_ID): cv.string})

async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    logger.debug(f"Got to async get triggers device_id: {device_id}")
    
    triggers = []
    entity_registry = er.async_get(hass)
    
    for entity_entry in er.async_entries_for_device(entity_registry,device_id):
        logger.debug(f"Iterated to : {entity_entry}")
        entity_id = entity_entry.unique_id
        entity_name = entity_entry.entity_id
        
        registry_entry = hub_event_listener.get_registry_entry(entity_id)
        if registry_entry is None:
            logger.warning(f"entity_id: {entity_id}, not found in dirigera_platform registry. Not associating triggers")
            continue
        
        if registry_entry.__class__.__name__ != "registry_entry":
            logger.warning(f"entity_id: {entity_id} corresponding in dirigera_platform not a registry_entry")
            continue 
         
        registry_entity = registry_entry.entity
        
        if "identifiers" not in registry_entity.device_info or len(list(registry_entity.device_info["identifiers"])[0]) < 2:
            logger.warning(f"entity_id: {entity_id} corresponding in dirigera_platform entity doesnt have identifiers or isnt 2 entries long, device_info : {registry_entity.device_info}")
        logger.info(registry_entity.device_info["identifiers"])
        registry_entity_id = list(registry_entity.device_info["identifiers"])[0][1]
        
        if registry_entity_id != entity_id:
            logger.error(f"Found controller with entity id : {registry_entity_id} but doesnt match requested entity id: {entity_id}")
            continue
        
        logger.debug(f"Found controller to tag events to entity : {entity_name}")

        entity_domain = entity_name.split('.', 1)[0]
        if entity_domain == "light":
            for trigger_type in LIGHT_TRIGGER_TYPES:
                triggers.append(
                    {
                        CONF_DEVICE_ID: device_id,
                        CONF_DOMAIN: DOMAIN,
                        CONF_PLATFORM: "device",
                        CONF_TYPE: trigger_type,
                        ATTR_ENTITY_ID: entity_name,
                    }
                )
            break

        # Now we have an ikea_controller
        # Check if entity_id has _X suffix (like "xxx_1") - this pattern must match hub_event_listener.py
        # If it matches, we ALWAYS use buttonX_ prefix to be consistent with event firing
        pattern = r'(([0-9]|[a-z]|-)*)_([0-9])+'
        match = re.match(pattern, entity_id)

        use_prefix: bool = False
        if match:
            # Device ID has _X suffix - hub_event_listener will add buttonX_ prefix
            logger.debug(f"Entity ID {entity_id} matches multi-button pattern, will use prefix")
            use_prefix = True

        if not hasattr(registry_entity, "number_of_buttons"):
            logger.debug(f"Entity {entity_id} is not a controller and has no button triggers")
            break

        if registry_entity.number_of_buttons > 1:
            # Multiple buttons without _X suffix - also use prefix
            logger.debug("More than one button will use prefix")
            use_prefix = True

        for btn_idx in range(registry_entity.number_of_buttons):
            for trigger_type in CONTROLLER_TRIGGER_TYPES:
                if use_prefix:
                    trigger_name = f"button{btn_idx+1}_{trigger_type}"
                else:
                    trigger_name = trigger_type

                triggers.append(
                    {
                        CONF_DEVICE_ID: device_id,
                        CONF_DOMAIN: DOMAIN,
                        CONF_PLATFORM: "device",
                        CONF_TYPE: trigger_name,
                        ATTR_ENTITY_ID: entity_name,
                    }
                )
        
        break 
    
    logger.debug(f"Returning triggers : {triggers}")
    return triggers 

async def async_attach_trigger(hass, config, action, trigger_info):
    logger.debug(f"Got to async_attach_trigger config: {config}, action: {action}, trigger_info: {trigger_info}")

    if config[CONF_TYPE] in LIGHT_TRIGGER_TYPES:
        # Attach a HA state trigger for light on/off events
        state_config = state_trigger.TRIGGER_SCHEMA(
            {
                state_trigger.CONF_PLATFORM: "state",
                state_trigger.CONF_ENTITY_ID: config[ATTR_ENTITY_ID],
                state_trigger.CONF_TO: "on" if config[CONF_TYPE] == "turned_on" else "off",
            }
        )
        return await state_trigger.async_attach_trigger(
            hass, state_config, action, trigger_info, platform_type="device"
        )

    # Controller triggers (button presses) use the custom event bus path
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: f"{DOMAIN}_event",
            event_trigger.CONF_EVENT_DATA: {
                CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                CONF_TYPE: config[CONF_TYPE],
                ATTR_ENTITY_ID: config[ATTR_ENTITY_ID],
            },
        }
    )

    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
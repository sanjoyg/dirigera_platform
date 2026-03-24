import threading
import logging 
import time 
import json
import re 
import websocket
import ssl
import re
from typing import Any 
import datetime
from dateutil import parser
from dirigera import Hub
from dirigera.devices.device import Room

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.components.light import ColorMode
from homeassistant.helpers import device_registry as dr, entity_registry as er, area_registry as ar

logger = logging.getLogger("custom_components.dirigera_platform.hub_event_listener")

DATE_TIME_FORMAT:str =  "%Y-%m-%dT%H:%M:%S.%fZ"

process_events_from = {
    "motionSensor"    :     ["isDetected","isOn","batteryPercentage","customName"],
    "occupancySensor" :     ["isDetected","isOn","batteryPercentage","customName"],
    "outlet"          :     [   "isOn",
                                "currentAmps",
                                "currentActivePower",
                                "currentVoltage",
                                "totalEnergyConsumed",
                                "energyConsumedAtLastReset",
                                "timeOfLastEnergyReset",
                                "totalEnergyConsumedLastUpdated",
                                "customName"],
    "light"           :     ["isOn", "lightLevel", "colorTemperature", "colorHue", "colorSaturation", "customName"],
    "openCloseSensor" :     ["isOpen","batteryPercentage","customName"],
    "waterSensor"     :     ["waterLeakDetected","batteryPercentage","customName"],
    "blinds"          :     ["blindsCurrentLevel","batteryPercentage","customName"],
    "lightSensor"     :     ["illuminance","batteryPercentage","customName"],
    "environmentSensor":    [   "currentTemperature",
                                "currentRH",
                                "currentPM25",
                                "currentCO2",
                                "vocIndex",
                                "batteryPercentage",
                                "customName"]
}

controller_trigger_last_time_map = {}

def to_snake_case(name:str) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

class registry_entry:
    def __init__(self, entity:any, cascade_entity:any = None):
        self._entity = entity
        self._cascade_entity = cascade_entity 
    
    @property
    def entity(self):
        return self._entity
    
    @property
    def cascade_entity(self):
        return self._cascade_entity
    
    @cascade_entity.setter
    def cascade_entity(self, value):
        self._cascade_entity = value 

    def __str__(self):
        str =  f"registry_entry: id {self._entity.unique_id}, cascade_entry : "
        if self._cascade_entity is None :
            str = str +  "None"
        else:
            str = str + f"{self._cascade_entity}"
        return str

class hub_event_listener(threading.Thread):
    device_registry = {}

    def register(id: str, entry: registry_entry):
        if id in hub_event_listener.device_registry:
            return 
        hub_event_listener.device_registry[id] = entry 

    def get_registry_entry(id:str) -> registry_entry:
        if id not in hub_event_listener.device_registry:
            return None 
        return hub_event_listener.device_registry[id]
    
    def __init__(self, hub : Hub, hass, discovery_coordinator=None):
        super().__init__()
        self._hub : Hub = hub
        self._request_to_stop = False
        self._hass = hass
        self._discovery_coordinator = discovery_coordinator

    async def _update_device_area(self, device_id: str, room_name: str):
        """Update the device's area in Home Assistant's device registry if needed."""
        try:
            device_reg = dr.async_get(self._hass)
            area_reg = ar.async_get(self._hass)

            # Find the device entry
            device_entry = device_reg.async_get_device({("dirigera_platform", device_id)})
            if device_entry is None:
                logger.debug(f"Device {device_id} not found in HA device registry")
                return

            if room_name == "":
                # Remove area assignment if currently set
                if device_entry.area_id is not None:
                    logger.info(f"Removing area assignment from device {device_id}")
                    device_reg.async_update_device(device_entry.id, area_id=None)
            else:
                # Find or create the area
                area_entry = area_reg.async_get_area_by_name(room_name)
                if area_entry is None:
                    # Create the area if it doesn't exist
                    logger.info(f"Creating new area: {room_name}")
                    area_entry = area_reg.async_create(room_name)

                # Only update if different
                if device_entry.area_id != area_entry.id:
                    logger.info(f"Updating device {device_id} area to {room_name}")
                    device_reg.async_update_device(device_entry.id, area_id=area_entry.id)
                else:
                    logger.debug(f"Device {device_id} already in area {room_name}")
        except Exception as ex:
            logger.error(f"Failed to update device area for {device_id}: {ex}")

    async def _update_device_name(self, device_id: str, new_name: str):
        """Update the device's name in Home Assistant's device registry."""
        try:
            device_reg = dr.async_get(self._hass)

            # Find the device entry
            device_entry = device_reg.async_get_device({("dirigera_platform", device_id)})
            if device_entry is None:
                logger.debug(f"Device {device_id} not found in HA device registry for name update")
                return

            # Only update if user hasn't set a custom name
            if device_entry.name_by_user is not None:
                logger.debug(f"Device {device_id} has user-set name, skipping automatic name update")
                return

            # Update the device's name
            logger.info(f"Updating device {device_id} name to {new_name}")
            device_reg.async_update_device(device_entry.id, name=new_name)
        except Exception as ex:
            logger.error(f"Failed to update device name for {device_id}: {ex}")

    async def sync_all_device_areas(self):
        """Sync all device areas from Dirigera room info to HA device registry.

        This should be called at startup after all entities are registered,
        to ensure HA device areas match Dirigera rooms.
        """
        logger.info("Starting device area sync from Dirigera rooms")
        synced_count = 0
        for device_id, registry_entry in hub_event_listener.device_registry.items():
            try:
                entity = registry_entry.entity
                if hasattr(entity, '_json_data') and entity._json_data.room is not None:
                    room_name = entity._json_data.room.name
                    identifier = entity._json_data.relation_id or entity._json_data.id
                    await self._update_device_area(identifier, room_name)
                    synced_count += 1
            except Exception as ex:
                logger.error(f"Failed to sync area for device {device_id}: {ex}")
        logger.info(f"Device area sync complete, processed {synced_count} devices with rooms")

    def on_error(self, ws:Any, ws_msg:str):
        logger.debug(f"on_error hub event listener {ws_msg}")
    
    def parse_scene_update(self, msg):
        global controller_trigger_last_time_map
        # Verify that this is controller initiated
        if "data" not in msg:
            logger.warning(f"discarding message as key 'data' not found: {msg}")
            return 
        
        if "triggers" not in msg["data"]:
            logger.warning(f"discarding message as key 'data/triggers'")
            return 
        
        triggers = msg["data"]["triggers"]
        
        for trigger in triggers:
            if "type" not in trigger:
                logger.warning(f"key 'type' not in trigger json : {trigger}")
                continue
            
            if trigger["type"] != "controller":
                logger.debug(f"Trigger type : {trigger['type']} not controller ignoring...")
                continue
            
            if "trigger" not in trigger:
                logger.warning(f"key 'trigger' not found in trigger json: {trigger}")
                continue 
            
            details = trigger["trigger"]
            
            if "controllerType" not in details or "clickPattern" not in details or "deviceId" not in details:
                logger.debug(f"Required key controllerType/clickPattern/deviceId not in trigger json : {trigger}")
                continue  
            
            controller_type = details["controllerType"]
            click_pattern = details["clickPattern"]
            device_id = details["deviceId"]
            
            if controller_type != "shortcutController":
                logger.debug(f"controller type on message not compatible: {controller_type}, ignoring...")
                continue 
            
            if click_pattern == "singlePress":
                trigger_type = "single_click"
            elif click_pattern == "longPress":
                trigger_type = "long_press"
            elif click_pattern == "doublePress":
                trigger_type = "double_click"
            else:
                logger.debug(f"click_pattern : {click_pattern} not in list of types...ignoring")
                continue
            
            device_id_for_registry = device_id
             
            button_idx = 0
            pattern = '(([0-9]|[a-z]|-)*)_([0-9])+'
            match = re.search(pattern, device_id)
            if match is not None:
                device_id_for_registry = f"{match.groups()[0]}_1"
                button_idx = int(match.groups()[2])
                logger.debug(f"Multi button controller, device_id effective : {device_id_for_registry} with buttons : {button_idx}")
                
            if button_idx != 0:
                trigger_type =f"button{button_idx}_{trigger_type}"
            
            # Now look up the associated entity in our own registry
            registry_value = hub_event_listener.get_registry_entry(device_id_for_registry)
            
            if registry_value.__class__.__name__ != "registry_entry":
                logger.debug(f"id : {device_id_for_registry} listener registry is not correct : {registry_value.__class__.__name__}...")
                continue
            
            entity  = registry_value.entity
            
            unique_key = f"{entity.registry_entry.device_id}_{trigger_type}"
            last_fired = datetime.datetime.now() 
            if unique_key in controller_trigger_last_time_map:
                last_fired = controller_trigger_last_time_map[unique_key]
                logger.debug(f"Found date/time in map for controller : {last_fired}")
            
            controller_trigger_last_time_map[unique_key] = datetime.datetime.now()
                
            if "lastTriggered" in msg["data"]:
                current_triggered_str = msg["data"]["lastTriggered"]
                try: 
                    current_triggered = parser.parse(current_triggered_str)
                    one_second_delta = datetime.timedelta(seconds=1)
                    controller_trigger_last_time_map[unique_key] = current_triggered
                    logger.debug(f"Updated date/time in map for controller with : {current_triggered}")    
                    if last_fired is not None and one_second_delta > current_triggered - last_fired:
                        logger.debug("Will not let this event be fired, this is to get over bug IKEA bug of firing event twice for controller")
                        return 
                    
                except Exception as ex:
                    logger.warning(f"Failed to parse date/time for last_triggered from event : {current_triggered_str}, wont affect functionality...")
                    logger.warning(ex)
                    # Ignore and let event be fired
                    
            # Now raise the bus event
            event_data = {
                "type": trigger_type,
                "device_id": entity.registry_entry.device_id,
                ATTR_ENTITY_ID: entity.registry_entry.entity_id
            }    
            
            self._hass.bus.fire(event_type="dirigera_platform_event",event_data=event_data)
            logger.debug(f"Event fired.. {event_data}")

        # Apply scene action attributes to light entities
        # Some bulbs only send colorMode in deviceStateChanged after a scene,
        # without the actual color values. The sceneUpdated event contains the
        # full attributes in its actions, so we apply them here.
        self._apply_scene_actions(msg)

    def _apply_scene_actions(self, msg):
        """Apply attributes from scene actions to the corresponding entities."""
        if "data" not in msg or "actions" not in msg["data"]:
            return

        for action in msg["data"]["actions"]:
            if action.get("type") != "device":
                continue

            device_id = action.get("deviceId")
            attributes = action.get("attributes")

            if not device_id or not attributes:
                continue

            if device_id not in hub_event_listener.device_registry:
                logger.debug(f"Scene action device {device_id} not in registry, skipping")
                continue

            registry_value = hub_event_listener.get_registry_entry(device_id)
            if registry_value.__class__.__name__ != "registry_entry":
                continue

            entity = registry_value.entity

            # Only process light-relevant attributes from scene actions
            light_attrs = ["isOn", "lightLevel", "colorTemperature", "colorHue", "colorSaturation"]
            updated = False

            for key in attributes:
                if key not in light_attrs:
                    continue
                try:
                    key_attr = to_snake_case(key)
                    logger.debug(f"Scene action: setting {key_attr} to {attributes[key]} on {device_id}")
                    setattr(entity._json_data.attributes, key_attr, attributes[key])
                    updated = True
                except Exception as ex:
                    logger.warning(f"Scene action: failed to set {key} on {device_id}: {ex}")

            # Update color_mode based on scene attributes
            if updated and hasattr(entity, '_color_mode'):
                if "colorHue" in attributes or "colorSaturation" in attributes:
                    entity._color_mode = ColorMode.HS
                    logger.debug(f"Scene action: set color_mode to HS for {device_id}")
                elif "colorTemperature" in attributes:
                    entity._color_mode = ColorMode.COLOR_TEMP
                    logger.debug(f"Scene action: set color_mode to COLOR_TEMP for {device_id}")

            if updated:
                try:
                    entity.schedule_update_ha_state()
                    logger.debug(f"Scene action: scheduled HA state update for {device_id}")
                except Exception as ex:
                    logger.warning(f"Scene action: failed to schedule update for {device_id}: {ex}")

    def parse_remote_press_event(self, msg):
        """
        Parse remotePressEvent messages from lightController remotes like STYRBAR and RODRET.
        These remotes send direct press events without needing scene configuration.
        """
        global controller_trigger_last_time_map

        if "data" not in msg:
            logger.warning(f"discarding remotePressEvent: 'data' not found: {msg}")
            return

        data = msg["data"]
        if "id" not in data or "clickPattern" not in data:
            logger.warning(f"discarding remotePressEvent: 'id' or 'clickPattern' not found: {data}")
            return

        device_id = data["id"]
        click_pattern = data["clickPattern"]

        # Convert clickPattern to trigger_type
        if click_pattern == "singlePress":
            trigger_type = "single_click"
        elif click_pattern == "longPress":
            trigger_type = "long_press"
        elif click_pattern == "doublePress":
            trigger_type = "double_click"
        else:
            logger.debug(f"remotePressEvent: unknown clickPattern '{click_pattern}', ignoring...")
            return

        # Handle multi-button controllers (device_id like xxx_2 means button 2)
        device_id_for_registry = device_id
        button_idx = 0
        pattern = '(([0-9]|[a-z]|-)*)_([0-9])+'
        match = re.search(pattern, device_id)
        if match is not None:
            device_id_for_registry = f"{match.groups()[0]}_1"
            button_idx = int(match.groups()[2])
            logger.debug(f"remotePressEvent: Multi button controller, device_id effective: {device_id_for_registry} with button: {button_idx}")

        if button_idx != 0:
            trigger_type = f"button{button_idx}_{trigger_type}"

        # Look up entity in registry
        registry_value = hub_event_listener.get_registry_entry(device_id_for_registry)

        if registry_value is None:
            logger.debug(f"remotePressEvent: Controller {device_id_for_registry} not found in registry, ignoring...")
            return

        if registry_value.__class__.__name__ != "registry_entry":
            logger.debug(f"remotePressEvent: id {device_id_for_registry} registry is not correct: {registry_value.__class__.__name__}...")
            return

        entity = registry_value.entity

        # Debounce: prevent duplicate events within 1 second (IKEA bug workaround)
        unique_key = f"{entity.registry_entry.device_id}_{trigger_type}"
        now = datetime.datetime.now()
        if unique_key in controller_trigger_last_time_map:
            last_fired = controller_trigger_last_time_map[unique_key]
            if (now - last_fired).total_seconds() < 1.0:
                logger.debug(f"remotePressEvent: Debouncing duplicate event for {unique_key}")
                return

        controller_trigger_last_time_map[unique_key] = now

        # Fire Home Assistant event
        event_data = {
            "type": trigger_type,
            "device_id": entity.registry_entry.device_id,
            ATTR_ENTITY_ID: entity.registry_entry.entity_id
        }

        self._hass.bus.fire(event_type="dirigera_platform_event", event_data=event_data)
        logger.debug(f"remotePressEvent fired: {event_data}")

    def on_message(self, ws:Any, ws_msg:str):
        
        try:
            logger.debug(f"rcvd message : {ws_msg}")
            msg = json.loads(ws_msg)
            if "type" not in msg:
                logger.debug(f"'type' not found in incoming message, discarding : {msg}")
                return 
            
            if msg['type'] == "sceneUpdated":
                logger.debug(f"Found sceneUpdated message... ")
                return self.parse_scene_update(msg)

            if msg['type'] == "remotePressEvent":
                logger.debug(f"Found remotePressEvent message... ")
                return self.parse_remote_press_event(msg)

            # Handle deviceAdded events - trigger dynamic discovery
            if msg['type'] == "deviceAdded":
                if "data" in msg and "id" in msg['data']:
                    device_id = msg['data']['id']
                    device_type = msg['data'].get('deviceType', msg['data'].get('type'))
                    if device_type and self._discovery_coordinator is not None:
                        logger.info(f"Device added event received: {device_id} (type: {device_type})")
                        # Schedule discovery on the main event loop
                        self._hass.loop.call_soon_threadsafe(
                            lambda did=device_id, dt=device_type: self._hass.async_create_task(
                                self._discovery_coordinator.discover_device(did, dt)
                            )
                        )
                    else:
                        logger.debug(f"deviceAdded event without discovery coordinator or type: {msg}")
                return

            # Log deviceRemoved events for now (entities will become unavailable)
            if msg['type'] == "deviceRemoved":
                if "data" in msg and "id" in msg['data']:
                    device_id = msg['data']['id']
                    logger.info(f"Device removed event received: {device_id}")
                    # Note: The entity will remain in HA but become unavailable
                    # Full removal requires manual deletion in HA UI or a restart
                return

            if msg['type'] != "deviceStateChanged":
                logger.debug(f"discarding non state message: {msg}")
                return 

            if "data" not in msg or "id" not in msg['data']:
                logger.info(f"discarding message as  key 'data' or 'data/id' not found: {msg}")
                return  
            
            info = msg['data'] 
            id = info['id']

            device_type = None
            if "deviceType" in info:
                device_type = info["deviceType"]
            elif "type" in info:
                device_type = info["type"]
            else:
                logger.warn("expected type or deviceType in JSON, none found, ignoring...")
                return

            logger.debug(f"device type of message {device_type}")
            if device_type not in process_events_from:
                # To avoid issues been reported. If we dont have it in our list
                # then best to not process this event
                return

            if id not in hub_event_listener.device_registry:
                # Unknown device - try to discover it
                if self._discovery_coordinator is not None:
                    logger.info(f"Unknown device detected: {id} (type: {device_type}), triggering discovery")
                    # Schedule discovery on the main event loop
                    self._hass.loop.call_soon_threadsafe(
                        lambda: self._hass.async_create_task(
                            self._discovery_coordinator.discover_device(id, device_type)
                        )
                    )
                else:
                    logger.info(f"discarding message as device for id: {id} not found for msg: {msg}")
                return

            registry_value = hub_event_listener.get_registry_entry(id)
            entity = registry_value.entity 

            reachability_changed = False
            if "isReachable" in info:
                try:
                    logger.debug(f"Setting {id} reachable as {info['isReachable']}")
                    entity._json_data.is_reachable=info["isReachable"]
                    reachability_changed = True
                except Exception as ex:
                    logger.error(f"Failed to setattr is_reachable on device: {id} for msg: {msg}")
                    logger.error(ex)

            # Process room updates (room info comes as separate field, not in attributes)
            room_changed = False
            if "room" in info:
                try:
                    room_data = info["room"]
                    if room_data is not None:
                        new_room = Room(
                            id=room_data.get("id"),
                            name=room_data.get("name"),
                            color=room_data.get("color"),
                            icon=room_data.get("icon")
                        )
                        if entity._json_data.room is None or entity._json_data.room.id != new_room.id:
                            logger.debug(f"Setting {id} room to {new_room.name}")
                            entity._json_data.room = new_room
                            room_changed = True
                        # Always ensure HA device registry area matches (even if _json_data room didn't change)
                        # This handles the case where HA restarts and the room is already set in _json_data
                        # but not yet in the HA device registry
                        try:
                            self._hass.loop.call_soon_threadsafe(
                                lambda room=new_room.name, device_id=(entity._json_data.relation_id or id): self._hass.async_create_task(
                                    self._update_device_area(device_id, room)
                                )
                            )
                        except Exception as ex:
                            logger.error(f"Failed to schedule device area update for {id}: {ex}")
                    elif entity._json_data.room is not None:
                        # Room was removed
                        logger.debug(f"Removing room from {id}")
                        entity._json_data.room = None
                        room_changed = True
                        try:
                            self._hass.loop.call_soon_threadsafe(
                                lambda device_id=(entity._json_data.relation_id or id): self._hass.async_create_task(
                                    self._update_device_area(device_id, "")
                                )
                            )
                        except Exception as ex:
                            logger.error(f"Failed to schedule device area removal for {id}: {ex}")
                except Exception as ex:
                    logger.error(f"Failed to set room on device: {id} for msg: {msg}")
                    logger.error(ex)

            to_process_attr = process_events_from[device_type]
            turn_on_off = False
            has_attributes = "attributes" in info and info["attributes"] is not None
            name_changed = False
            new_name = None

            if has_attributes:
                attributes = info["attributes"]

                for key in attributes:
                    if key not in to_process_attr:
                        logger.debug(f"attribute {key} with value {attributes[key]} not in list of device type {device_type}, ignoring update...")
                        continue
                    try:
                        key_attr = to_snake_case(key)
                        # This is a hack need a better impl
                        if key_attr == "is_on":
                            turn_on_off = True
                        # Track name changes for device registry update
                        if key == "customName":
                            old_name = entity._json_data.attributes.custom_name
                            if old_name != attributes[key]:
                                name_changed = True
                                new_name = attributes[key]
                        logger.debug(f"setting {key_attr}  to {attributes[key]}")
                        logger.debug(f"Entity before setting: {entity._json_data}")

                        value_to_set = attributes[key]
                        #Need a hack for outlet with date/time entities
                        if key in ["timeOfLastEnergyReset","totalEnergyConsumedLastUpdated"]:
                            logger.debug(f"Got into date/time so will set the value accordingly...")
                            try :
                                value_to_set = parser.parse(attributes[key])
                            except:
                                #Ignore the exception
                                logger.warning(f"Failed to convert {attributes[key]} to date/time...")

                        setattr(entity._json_data.attributes,key_attr, value_to_set)
                        logger.debug(f"Entity after setting: {entity._json_data}")
                    except Exception as ex:
                        logger.warn(f"Failed to set attribute key: {key} converted to {key_attr} on device: {id}")
                        logger.warn(ex)
                                
                # Update color_mode for lights when color attributes change
                if device_type == "light" and hasattr(entity, '_color_mode'):
                    if "colorHue" in attributes or "colorSaturation" in attributes:
                        entity._color_mode = ColorMode.HS
                    elif "colorTemperature" in attributes:
                        entity._color_mode = ColorMode.COLOR_TEMP

                # Lights behave odd with hubs when setting attribute one event is generated which
                # causes brightness or other to toggle so put in a hack to fix that
                # if its is_on attribute then ignore this routine
                if device_type == "light" and entity.should_ignore_update and not turn_on_off:
                    entity.reset_ignore_update()
                    logger.debug("Ignoring calling update_ha_state as ignore_update is set")
                    return

                # Update HA device registry name if customName changed
                if name_changed and new_name is not None:
                    try:
                        self._hass.loop.call_soon_threadsafe(
                            lambda name=new_name, device_id=(entity._json_data.relation_id or id): self._hass.async_create_task(
                                self._update_device_name(device_id, name)
                            )
                        )
                    except Exception as ex:
                        logger.error(f"Failed to schedule device name update for {id}: {ex}")

            # Update HA state if attributes changed OR if reachability/room changed
            if has_attributes or reachability_changed or room_changed:
                entity.schedule_update_ha_state(False)

                if registry_value.cascade_entity is not None:
                    # Cascade the update
                    logger.debug(f"Cascading to cascade entity : {registry_value.cascade_entity.unique_id}")
                    registry_value.cascade_entity.schedule_update_ha_state(False)


        except Exception as ex:
            # Temp solution to not log entries
            logger.debug("error processing hub event")
            logger.debug(f"{ws_msg}")
            logger.debug(ex)

    def create_listener(self):
        try:
            logger.info("Starting dirigera hub event listener")
            self._wsapp = websocket.WebSocketApp(
                self._hub.websocket_base_url,
                header={"Authorization": f"Bearer {self._hub.token}"},
                on_message=self.on_message)
            self._wsapp.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            #self._hub.create_event_listener(on_message=self.on_message, on_error=self.on_error)
        except Exception as ex:
            logger.error("Error creating event listener...")
            logger.error(ex)

    def stop(self):
        logger.info("Listener request for stop..")

        self._request_to_stop = True
        try:
            #self._hub.stop_event_listener()
            if self._wsapp is not None:
                self._wsapp.close()
        except:
            pass 
        self.join()
        hub_event_listener.device_registry.clear()
        logger.info("Listener stopped..")

    def run(self):
        while True:
            # Blocking call
            self.create_listener()
            logger.debug("Listener thread complete...")
            if self._request_to_stop:
                break
            logger.warn("Failed to create listener or listener exited, will sleep 10 seconds before retrying")
            time.sleep(10)
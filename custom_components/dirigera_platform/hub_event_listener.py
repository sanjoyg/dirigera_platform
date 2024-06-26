import threading
import logging 
import time 
import json
import re 
import websocket
import ssl
from typing import Any 

from dirigera import Hub 

logger = logging.getLogger("custom_components.dirigera_platform")

process_events_from = {
    "motionSensor"    : ["isDetected","isOn"],
    "outlet"          : ["isOn"],
    "light"           : ["isOn", "lightLevel", "colorTemperature"],
    "openCloseSensor" : ["isOpen"],
    "waterSensor"     : ["waterLeakDetected"]
}

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
    
    def __init__(self, hub : Hub):
        super().__init__()
        self._hub : Hub = hub
        self._request_to_stop = False 

    def on_error(self, ws:Any, ws_msg:str):
        logger.debug(f"on_error hub event listener {ws_msg}")
    
    def on_message(self, ws:Any, ws_msg:str):
        
        try:
            logger.debug(f"rcvd message : {ws_msg}")
            msg = json.loads(ws_msg)
            if "type" not in msg or msg['type'] != "deviceStateChanged":
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
                logger.info(f"discarding message as device for id: {id} not found for msg: {msg}")
                return 
            
            registry_value = hub_event_listener.get_registry_entry(id)
            entity = registry_value.entity 

            if "isReachable" in info:
                try:
                    logger.debug(f"Setting {id} reachable as {info['isReachable']}")
                    entity._json_data.is_reachable=info["isReachable"]
                except Exception as ex:
                    logger.error(f"Failed to setattr is_reachable on device: {id} for msg: {msg}")
                    logger.error(ex)

            to_process_attr = process_events_from[device_type]
            turn_on_off = False 
            if "attributes" in info:
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
                        logger.debug(f"setting {key_attr}  to {attributes[key]}")
                        setattr(entity._json_data.attributes,key_attr, attributes[key])
                        logger.debug(entity._json_data)
                    except Exception as ex:
                        logger.warn(f"Failed to set attribute key: {key} converted to {key_attr} on device: {id}")
                        logger.warn(ex)
                                 
                # Lights behave odd with hubs when setting attribute one event is generated which
                # causes brightness or other to toggle so put in a hack to fix that
                # if its is_on attribute then ignore this routine
                if device_type == "light" and entity.should_ignore_update and not turn_on_off:
                    entity.reset_ignore_update()
                    logger.debug("Ignoring calling update_ha_state as ignore_update is set")
                    return 
                
                entity.schedule_update_ha_state(False)
                
                if registry_value.cascade_entity is not None:
                    # Cascade the update
                    logger.debug(f"Cascading to cascade entity : {registry_value.cascade_entity.unique_id}")
                    registry_value.cascade_entity.schedule_update_ha_state(False)


        except Exception as ex:
            logger.error("error processing hub event")
            logger.error(f"{ws_msg}")
            logger.error(ex)

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
import threading
import logging 
import time 
from typing import Any 
import json
import re 
import websocket
import ssl

logger = logging.getLogger("custom_components.dirigera_platform")

def to_snake_case(name:str) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

class hub_event_listener(threading.Thread):
    device_registry = {}

    def register(id: str, device: any):
        if id in hub_event_listener.device_registry:
            logger.error(f"duplicate id: {id} requested registration")
            return 
        hub_event_listener.device_registry[id] = device 

    def __init__(self, hub):
        super().__init__()
        self._hub = hub
        self._listening = False
        self._request_to_stop = False 
        self._wsapp = None 

    def on_error(ws:Any, ws_msg:str):
        logger.debug(f"on_error hub event listener {ws_msg}")
    
    def on_message(self, ws:Any, ws_msg:str):
        try:
            logger.debug(f"rcvd message : {ws_msg}")
            msg = json.loads(ws_msg)
            if "type" not in msg or msg['type'] != "deviceStateChanged":
                logger.error(f"discarding message: {msg}")
                return 

            if "data" not in msg or "id" not in msg['data']:
                logger.warn(f"discarding message as  key 'data' or 'data/id' not found: {msg}")
                return  
            
            info = msg['data'] 
            id = info['id']
            if id not in hub_event_listener.device_registry:
                logger.warn(f"discarding message as device for id: {id} not found for msg: {msg}")
                return 
            registry_value = hub_event_listener.device_registry[id]
            
            delegate = None
            entity = None 

            if type(registry_value) is list:
                delegate = registry_value[0]
                entity = registry_value[1]
            else:
                entity = registry_value
             
            #device = hub_event_listener.device_registry[id]
            if "isReachable" in info:
                try:
                    logger.debug(f"Setting {id} reachable as {info['isReachable']}")
                    entity._json_data.is_reachable=info["isReachable"]
                except Exception as ex:
                    logger.error(f"Failed to setattr is_reachable on device: {id} for msg: {msg}")
                    logger.error(ex)
            
            if "attributes" in info:
                attributes = info["attributes"]
                for key in attributes:
                    try:
                        key_attr = to_snake_case(key)
                        logger.debug(f"setting {key_attr}  to {attributes[key]}")
                        setattr(entity._json_data.attributes,key_attr, attributes[key])
                    except Exception as ex:
                        logger.warn(f"Failed to set attribute key: {key} converted to {key_attr} on device: {id}")
                        logger.warn(ex)
                if delegate is not None:
                    delegate.async_schedule_update_ha_state(True)
                else:
                    entity.async_schedule_update_ha_state(True)

        except Exception as ex:
            logger.error("error processing hub event")
            logger.error(f"{ws_msg}")
            logger.error(ex)

    def create_listener(self):
        try:
            logger.info("Starting dirigera hub event listener")
            self._listening = True 
            self._wsapp = websocket.WebSocketApp(
                self._hub.websocket_base_url,
                header={"Authorization": f"Bearer {self._hub.token}"},
                on_message=self.on_message)
            self._wsapp.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            #self._hub.create_event_listener(on_message=self.on_message, on_error=self.on_error)
            self._listening = True 
        except Exception as ex:
            self._listening = False
            logger.error("Error creating event listener...")
            logger.error(ex)

    def stop(self):
        logger.info("Listener request for stop..")

        self._request_to_stop = True
        try:
            if self._wsapp is not None:
                self._wsapp.close()
        except:
            pass 
        #self.stop_event_listener()
        self.join()
        hub_event_listener.device_registry.clear()
        logger.info("Listener stopped..")

    def run(self):
        while True:
            if not self._listening:
                # Blocking call
                self.create_listener()
                logger.debug("Listener thread complete...")
                if self._request_to_stop:
                    break
                if not self._listening:
                    logger.warn("Failed to create listener will sleep 10 seconds before retrying")
                    time.sleep(10)
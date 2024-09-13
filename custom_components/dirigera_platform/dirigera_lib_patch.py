from __future__ import annotations
from typing import Any, Dict, List, Optional
from typing import Any, Optional, Dict

from dirigera import Hub

from dirigera.devices.device import Attributes, Device
from dirigera.hub.abstract_smart_home_hub import AbstractSmartHomeHub

# Patch to fix issues with motion sensor
class HubX(Hub):
    def __init__(
        self, token: str, ip_address: str, port: str = "8443", api_version: str = "v1"
    ) -> None:
        super().__init__(token, ip_address, port, api_version)

    def get_controllers(self) -> List[ControllerX]:
        """
        Fetches all controllers registered in the Hub
        """
        devices = self.get("/devices")
        controllers = list(filter(lambda x: x["type"] == "controller", devices))
        return [dict_to_controller(controller, self) for controller in controllers]
    
    def create_empty_scene_for_controller(self, name:str, controller_id: str):
        data = {
            "info": { "name" : name , "icon" : "scenes_trophy"},
            "type": "customScene",
            "triggers": [ { 
                    "type" : "controller", 
                    "disabled": False, 
                    "trigger": {
                        "controllerType" : "shortcutController",
                        "buttonIndex" : 0,
                        "device_id" : controller_id
                    }
                }
            ],
            "actions": []
        }
        
        response_dict = self.post(
            "/scenes",
            data=data,
        )

class ControllerAttributesX(Attributes):
    is_on: Optional[bool] = None
    battery_percentage: Optional[int] = None
    switch_label: Optional[str] = None

class ControllerX(Device):
    dirigera_client: AbstractSmartHomeHub
    attributes: ControllerAttributesX

    def reload(self) -> ControllerX:
        data = self.dirigera_client.get(route=f"/devices/{self.id}")
        return ControllerX(dirigeraClient=self.dirigera_client, **data)

    def set_name(self, name: str) -> None:
        if "customName" not in self.capabilities.can_receive:
            raise AssertionError(
                "This controller does not support the set_name function"
            )

        data = [{"attributes": {"customName": name}}]
        self.dirigera_client.patch(route=f"/devices/{self.id}", data=data)
        self.attributes.custom_name = name

def dict_to_controller(
    data: Dict[str, Any], dirigera_client: AbstractSmartHomeHub
) -> ControllerX:
    return ControllerX(dirigeraClient=dirigera_client, **data)
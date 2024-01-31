from dirigera import Hub
from dirigera.devices.device import Attributes
from dirigera.devices.motion_sensor import MotionSensor
from dirigera.devices.open_close_sensor import OpenCloseSensor, dict_to_open_close_sensor
from dirigera.hub.abstract_smart_home_hub import AbstractSmartHomeHub
from typing import Any, Dict, List

# Patch to fix issues with motion sensor

class MotionSensorAttributesX(Attributes):
    battery_percentage: int
    is_on: bool

class MotionSensorX(MotionSensor):
    dirigera_client: AbstractSmartHomeHub
    attributes: MotionSensorAttributesX

def dict_to_motion_sensorx(data: Dict[str, Any], dirigera_client: AbstractSmartHomeHub) -> MotionSensorX:
    return MotionSensorX(dirigeraClient=dirigera_client, **data)

class HubX(Hub):
    def __init__( self, token: str, ip_address: str, port: str = "8443", api_version: str = "v1") -> None:
        super().__init__(token, ip_address, port, api_version)

    def get_motion_sensors(self) -> List[MotionSensor]:
        devices = self.get("/devices")
        sensors = list(filter(lambda x: x["deviceType"] == "motionSensor", devices))
        return [dict_to_motion_sensorx(sensor, self) for sensor in sensors]

    def get_motion_sensor_by_id(self, id_: str) -> MotionSensorX:
        motion_sensor = self._get_device_data_by_id(id_)
        if motion_sensor["deviceType"] != "motionSensor":
            raise ValueError("Device is not an MotionSensor")
        return dict_to_motion_sensorx(motion_sensor, self)
    
    def get_open_close_by_id(self, id_: str) -> OpenCloseSensor:
        open_close_sensor = self._get_device_data_by_id(id_)
        if open_close_sensor["deviceType"] != "openCloseSensor":
            raise ValueError("Device is not an OpenCloseSensor")
        return dict_to_open_close_sensor(open_close_sensor, self)

from typing import Any, Dict, List, Optional

from dirigera import Hub
from dirigera.devices.air_purifier import AirPurifier, dict_to_air_purifier
from dirigera.devices.blinds import Blind, dict_to_blind
from dirigera.devices.motion_sensor import MotionSensorAttributes
from dirigera.devices.environment_sensor import (
    EnvironmentSensor,
    dict_to_environment_sensor,
)
from dirigera.devices.motion_sensor import MotionSensor
from dirigera.devices.open_close_sensor import (
    OpenCloseSensor,
    dict_to_open_close_sensor,
)
from dirigera.hub.abstract_smart_home_hub import AbstractSmartHomeHub

# Patch to fix issues with motion sensor

class MotionSensorAttributesX(MotionSensorAttributes):
    is_detected: Optional[bool]


class MotionSensorX(MotionSensor):
    dirigera_client: AbstractSmartHomeHub
    attributes: MotionSensorAttributesX


def dict_to_motion_sensorx(
    data: Dict[str, Any], dirigera_client: AbstractSmartHomeHub
) -> MotionSensorX:
    return MotionSensorX(dirigeraClient=dirigera_client, **data)


class HubX(Hub):
    def __init__(
        self, token: str, ip_address: str, port: str = "8443", api_version: str = "v1"
    ) -> None:
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

    def get_environment_sensor_by_id(self, id_: str) -> EnvironmentSensor:
        environment_sensor = self._get_device_data_by_id(id_)
        if environment_sensor["deviceType"] != "environmentSensor":
            raise ValueError("Device is not an EnvironmentSensor")
        return dict_to_environment_sensor(environment_sensor, self)

    def get_blinds_by_id(self, id_: str) -> Blind:
        blind_sensor = self._get_device_data_by_id(id_)
        if blind_sensor["deviceType"] != "blinds":
            raise ValueError("Device is not a Blind")
        return dict_to_blind(blind_sensor, self)

    def get_air_purifier_by_id(self, id_: str) -> AirPurifier:
        air_purifier_device = self._get_device_data_by_id(id_)
        if air_purifier_device["deviceType"] != "airPurifier":
            raise ValueError("Device is not an Air Purifier")
        return dict_to_air_purifier(air_purifier_device, self)

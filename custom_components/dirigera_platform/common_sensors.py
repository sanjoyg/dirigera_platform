from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import DeviceInfo

class battery_percentage_sensor(SensorEntity):
    def __init__(self, device):
        self._device = device

    @property
    def available(self):
        return self._device.available
    
    @property
    def device_info(self) -> DeviceInfo:
        return self._device.device_info
    
    @property
    def unique_id(self):
        return f"{self._device.unique_id}_BP01"
    
    @property
    def device_class(self) -> str:
        return SensorDeviceClass.BATTERY
    
    @property
    def native_unit_of_measurement(self) -> str:
        return "%"
    
    @property
    def name(self) -> str:
        return f"{self._device.name} Battery"
    
    @property
    def native_value(self):
        return getattr(self._device, "battery_percentage", 0)
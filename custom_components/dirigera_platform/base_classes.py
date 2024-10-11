from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass, SensorEntity
from homeassistant.components.datetime import DateTimeEntity
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.core import HomeAssistantError
from homeassistant.components.number import NumberEntity, NumberDeviceClass

from .hub_event_listener import hub_event_listener, registry_entry
from .const import DOMAIN

import logging 
from datetime import datetime

logger = logging.getLogger("custom_components.dirigera_platform")

def induce_properties(class_to_induce, attr):
    for key in attr.keys():
            logger.debug(f"Inducing class {class_to_induce.__name__} property {key} : value {attr[key]}")
            make_property(class_to_induce, key, attr[key])

def make_property(class_to_induce, name, value):
    setattr(class_to_induce, name, property(lambda self: getattr(self._json_data.attributes,name)))

class ikea_base_device:
    def __init__(self, hass, hub, json_data, get_by_id_fx) -> None:
        logger.debug("ikea_base_device ctor...")
        self._hass = hass 
        self._hub = hub
        self._json_data = json_data
        self._get_by_id_fx = get_by_id_fx
        self._listeners : list[Entity] = []

        # inject properties based on attr
        induce_properties(ikea_base_device, self._json_data.attributes.dict())
        
        # Register the device for updates
        if self.should_register_with_listener:
            hub_event_listener.register(self._json_data.id, registry_entry(self))

    def add_listener(self, entity : Entity) -> None:
        self._listeners.append(entity)

    @property
    def unique_id(self):
        return self._json_data.id

    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def should_register_with_listener(self):
        return True 
    
    @property
    def device_info(self) -> DeviceInfo:
        logger.debug(f"device_info called {self.name}")
        
        return DeviceInfo(
            identifiers={("dirigera_platform", self._json_data.id)},
            name=self.name,
            manufacturer=self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model,
            sw_version=self._json_data.attributes.firmware_version,
            suggested_area=self._json_data.room.name if self._json_data.room is not None else None,
        )

    @property
    def name(self):
        if self._json_data.attributes.custom_name is None or len(self._json_data.attributes.custom_name) == 0:
            return self.unique_id
        return self._json_data.attributes.custom_name
            
    async def async_update(self):
        logger.debug(f"update called {self.name}")
        try:
            self._json_data = await self._hass.async_add_executor_job(self._get_by_id_fx, self._json_data.id)
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")
    
    # To ensure state update of hass is cascaded
    def async_schedule_update_ha_state(self, force_refresh:bool = False) -> None:
        for listener in self._listeners:
            listener.schedule_update_ha_state(force_refresh)

    # To ensure state update of hass is cascaded
    def schedule_update_ha_state(self, force_refresh:bool = False) -> None:
        for listener in self._listeners:
            listener.schedule_update_ha_state(force_refresh)

class ikea_base_device_sensor():
    def __init__(self,  device, id_suffix:str = "", name:str = "", uom="", icon="", device_class=None, entity_category=None, state_class=None):
        self._device = device
        self._name = name
        self._id_suffix = id_suffix
        self._uom = uom
        self._device_class = device_class
        self._entity_category = entity_category
        self._state_class = state_class
        self._device.add_listener(self)
        self._icon = icon 
        
    @property
    def unique_id(self):
        return self._device.unique_id + self._id_suffix

    @property
    def available(self):
        return self._device.available

    @property
    def device_info(self) -> DeviceInfo:
        return self._device.device_info
        
    @property
    def name(self):
        return self._name
    
    @property
    def entity_category(self):
        return self._entity_category
    
    @property
    def device_class(self) -> str:
        return self._device_class
    
    @property
    def state_class(self):
        return self._state_class
    
    @property
    def icon(self):
        return self._icon 
    
    @property
    def native_unit_of_measurement(self) -> str:
        return self._uom
    
    async def async_update(self):
        await self._device.async_update()
     
class battery_percentage_sensor(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="BP01",
                            name="Battery Percentage",
                            uom="%",
                            icon="mdi:battery",
                            device_class=SensorDeviceClass.BATTERY,
                            entity_category=EntityCategory.DIAGNOSTIC)

    @property
    def native_value(self):
        return getattr(self._device, "battery_percentage")
    
class current_amps_sensor(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="CA01",
                            name="Current Amps",
                            uom="A",
                            icon="mdi:current-ac",
                            device_class=SensorDeviceClass.CURRENT)
    
    @property
    def native_value(self):
        return getattr(self._device, "current_amps")

class current_active_power_sensor(ikea_base_device_sensor, SensorEntity):   
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="CAP01",
                            name="Current Active Power",
                            uom="W",
                            icon="mdi:lightning-bolt-outline",
                            device_class=SensorDeviceClass.POWER)

    @property
    def native_value(self):
        return getattr(self._device, "current_active_power")
    
class current_voltage_sensor(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(device,"current_voltage","CV01",SensorDeviceClass.VOLTAGE,"V","Current Voltage","mdi:power-plug")
    
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="CV01",
                            name="Current Voltage",
                            uom="V",
                            icon="mdi:power-plug",
                            device_class=SensorDeviceClass.VOLTAGE)

    @property
    def native_value(self):
        return getattr(self._device, "current_voltage")
    
class total_energy_consumed_sensor(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="TEC01",
                            name="Total Energy Consumed",
                            uom="kWh",
                            icon="mdi:lightning-bolt-outline",
                            device_class=SensorDeviceClass.ENERGY,
                            state_class=SensorStateClass.TOTAL_INCREASING)

    @property
    def native_value(self):
        return getattr(self._device, "total_energy_consumed")
    
class energy_consumed_at_last_reset_sensor(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="ELAR01",
                            name="Energy Consumed at Last Reset",
                            uom="kWh",
                            icon="mdi:lightning-bolt-outline",
                            device_class=SensorDeviceClass.ENERGY,
                            state_class=SensorStateClass.TOTAL_INCREASING)

    @property
    def native_value(self):
        return getattr(self._device, "energy_consumed_at_last_reset")

class time_of_last_energy_reset_sensor(ikea_base_device_sensor, DateTimeEntity):
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="TLER01",
                            name="Time of Last Energy Reset",
                            icon="mdi:update")

    @property
    def native_value(self):
        return getattr(self._device, "time_of_last_energy_reset")

class total_energy_consumed_last_updated_sensor(ikea_base_device_sensor, DateTimeEntity):
    def __init__(self, device):
        super().__init__(device,"total_energy_consumed_last_updated","%Y-%m-%dT%H:%M:%S.%f%z","TECLU01"," Time Energy Consumed Last Updated")
    
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="TECLU01",
                            name="Time Energy Consumed Last Updated",
                            icon="mdi:update")

    @property
    def native_value(self):
        return getattr(self._device, "total_energy_consumed_last_updated")
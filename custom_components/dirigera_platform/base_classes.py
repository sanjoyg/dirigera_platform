from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.core import HomeAssistantError

from .hub_event_listener import hub_event_listener, registry_entry
from .const import DOMAIN

import logging 

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
    def __init__(self,  device, id_suffix:str = "", name_suffix:str = ""):
        self._device = device
        self._name_suffix = name_suffix
        self._id_suffix = id_suffix
        self._device.add_listener(self)

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
        return self._device.name + " " + self._name_suffix
            
    async def async_update(self):
        await self._device.async_update()

class battery_percentage_sensor(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(device)

    @property
    def entity_category(self):
        return EntityCategory.DIAGNOSTIC
      
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
    def icon(self):
        return "mdi:battery"
    @property
    def name(self) -> str:
        return f"{self._device.name} Battery"
    
    @property
    def native_value(self):
        return getattr(self._device, "battery_percentage", 0)

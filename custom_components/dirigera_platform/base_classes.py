from homeassistant import core
from homeassistant.core import HomeAssistantError

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass, SensorEntity
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.cover import CoverDeviceClass, CoverEntity,CoverEntityFeature
from homeassistant.components.datetime import DateTimeEntity
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    )

from dirigera import Hub
from dirigera.devices.blinds import Blind
from dirigera.devices.environment_sensor import EnvironmentSensor
from dirigera.devices.controller import Controller
from dirigera.devices.air_purifier import FanModeEnum

from .hub_event_listener import hub_event_listener, registry_entry
from .const import DOMAIN

from enum import Enum 
import logging 
import math
import datetime

logger = logging.getLogger("custom_components.dirigera_platform")

DATE_TIME_FORMAT:str = "%Y-%m-%dT%H:%M:%S.%fZ"

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
        self._skip_update = False 

        # inject properties based on attr
        induce_properties(ikea_base_device, self._json_data.attributes.dict())
        
        # Register the device for updates
        if self.should_register_with_listener:
            hub_event_listener.register(self._json_data.id, registry_entry(self))

    @property
    def skip_update(self)->bool:
        return self._skip_update
    
    @skip_update.setter
    def skip_update(self, value:bool):
        self._skip_update = value 
        
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
        if self.skip_update:
            logger.debug(f"update skipped for {self.name} as marked to skip...")
            return 
        
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
    def __init__(self,  device, id_suffix:str = "", name:str = "", native_unit_of_measurement="", icon="", device_class=None, entity_category=None, state_class=None):
        self._device = device
        self._name = name
        self._id_suffix = id_suffix
        self._native_unit_of_measurement = native_unit_of_measurement
        self._device_class = device_class
        self._entity_category = entity_category
        self._state_class = state_class
        self._device.add_listener(self)
        self._icon = icon 
        self.printed = False 
        
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
        if self._name is None or len(self._name) == 0:
            return self._device.name
        if self._device.name.lower()  == self._name.lower():
            # Dont duplication , Bug Fix #109
            return self._device.name
        return f"{self._device.name} {self._name}"
    
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
        return self._native_unit_of_measurement
    
    async def async_update(self):
        await self._device.async_update()

class ikea_outlet_device(ikea_base_device):
    def __init__(self, hass, hub, json_data):
        super().__init__(hass, hub, json_data, hub.get_outlet_by_id)
        self.skip_update = True 
    
    async def async_turn_on(self):
        logger.debug("outlet turn_on")
        try:
            await self._hass.async_add_executor_job(self._json_data.set_on, True)
        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_turn_off(self):
        logger.debug("outlet turn_off")
        try:
            await self._hass.async_add_executor_job(self._json_data.set_on, False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

class ikea_outlet_switch_sensor(ikea_base_device_sensor, SwitchEntity):
    def __init__(self, device):
        super().__init__(device = device, name = device.name )
        
    @property
    def is_on(self):
        return self._device.is_on

    async def async_turn_on(self):
        logger.debug("sensor: outlet turn_on")
        await self._device.async_turn_on()

    async def async_turn_off(self):
        logger.debug("sensor: outlet turn_off")
        await self._device.async_turn_off()

class ikea_motion_sensor_device(ikea_base_device):
    def __init__(self,hass, hub, json_data):
        logger.debug("ikea_motion_sensor_device ctor...")
        super().__init__(hass, hub, json_data, hub.get_motion_sensor_by_id)
        self.skip_update = True 
        
class ikea_motion_sensor(ikea_base_device_sensor, BinarySensorEntity):  
    def __init__(self, device: ikea_motion_sensor_device):
        logger.debug("ikea_motion_sensor ctor...")
        # No suffix or name prefix for backward compatibility
        super().__init__(device)
   
    @property
    def is_on(self):
        return self._device.is_on or self._device.is_detected

class ikea_open_close_device(ikea_base_device):
    def __init__(self, hass, hub, json_data):
        logger.debug("ikea_motion_sensor_device ctor...")
        super().__init__(hass, hub, json_data, hub.get_open_close_by_id)
        self.skip_update = True 

class ikea_open_close_sensor(ikea_base_device_sensor, BinarySensorEntity):
    def __init__(self, device: ikea_open_close_device):
        logger.debug("ikea_motion_sensor ctor...")
        # No suffix or name prefix for backward compatibility
        super().__init__(device)

    @property
    def device_class(self) -> str:
        return BinarySensorDeviceClass.WINDOW

    @property
    def is_on(self):
        return self._device.is_open

class ikea_water_sensor_device(ikea_base_device):
    def __init__(self, hass, hub, json_data):
        super().__init__(hass, hub, json_data, hub.get_water_sensor_by_id)
        self.skip_update = True 
        
class ikea_water_sensor(ikea_base_device_sensor, BinarySensorEntity):
    def __init__(self, device : ikea_water_sensor_device):
        logger.debug("ikea_water_sensor ctor...")
        super().__init__(device)
    
    @property
    def is_on(self):
        return self._device.water_leak_detected
         
class ikea_blinds_device(ikea_base_device):
    def __init__(self, hass:core.HomeAssistant, hub:Hub, blind:Blind):
        logger.debug("IkeaBlinds ctor...")
        super().__init__(hass, hub, blind, hub.get_blinds_by_id)
    
    @property
    def device_class(self) -> str:
        return CoverDeviceClass.BLIND
    
    async def async_open_cover(self):
        await self._hass.async_add_executor_job(self._json_data.set_target_level, 0)

    async def async_close_cover(self):
        await self._hass.async_add_executor_job(self._json_data.set_target_level, 100)

    async def async_set_cover_position(self, position:int):
        if position >= 0 and position <= 100:
            await self._hass.async_add_executor_job(self._json_data.set_target_level,100 - position)
    
class ikea_blinds_sensor(ikea_base_device_sensor, CoverEntity):
    def __init__(self, device:ikea_blinds_device):
        logger.debug("IkeaBlinds ctor...")
        super().__init__(device)

    @property
    def device_class(self) -> str:
        return CoverDeviceClass.BLIND

    @property
    def supported_features(self):
        return (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
        )

    @property
    def current_cover_position(self):
        return 100 - self._device.blinds_current_level

    @property
    def target_cover_position(self):
        return 100 - self._device.blinds_target_level

    @property
    def is_closed(self):
        if self.current_cover_position is None:
            return False
        return self.current_cover_position == 0

    @property
    def is_closing(self):
        if self.current_cover_position is None or self.target_cover_position is False:
            return False

        if self.current_cover_position != 0 and self.target_cover_position == 0:
            return True

        return False

    @property
    def is_opening(self):
        if self.current_cover_position is None or self.target_cover_position is False:
            return False

        if self.current_cover_position != 100 and self.target_cover_position == 100:
            return True

        return False

    async def async_open_cover(self, **kwargs):
        await self._device.async_open_cover()

    async def async_close_cover(self, **kwargs):
        await self._device.async_close_cover()

    async def async_set_cover_position(self, **kwargs):
        position = int(kwargs["position"])
        await self._device.async_set_cover_position(position)

class ikea_vindstyrka_device(ikea_base_device):
    def __init__(self, hass:core.HomeAssistant, hub:Hub , json_data:EnvironmentSensor) -> None:
        super().__init__(hass, hub, json_data, hub.get_environment_sensor_by_id)
        self._updated_at = None 

    async def async_update(self):        
        if self._updated_at is None or (datetime.datetime.now() - self._updated_at).total_seconds() > 30:
            try:
                logger.debug("env sensor update called...")
                self._json_data = await self._hass.async_add_executor_job(self._hub.get_environment_sensor_by_id, self._json_data.id)
                self._updated_at = datetime.datetime.now()
            except Exception as ex:
                logger.error(f"error encountered running update on : {self.name}")
                logger.error(ex)
                raise HomeAssistantError(ex, DOMAIN, "hub_exception")

class ikea_vindstyrka_temperature(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device: ikea_vindstyrka_device) -> None:
        super().__init__(
            device, 
            id_suffix="TEMP", 
            name="Temperature",
            device_class=SensorDeviceClass.TEMPERATURE, 
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class="measurement")
        logger.debug("ikea_vindstyrka_temperature ctor...")

    @property
    def native_value(self) -> float:
        return self._device.current_temperature
 
class ikea_vindstyrka_humidity(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device: ikea_vindstyrka_device) -> None:
        logger.debug("ikea_vindstyrka_humidity ctor...")
        super().__init__(
                    device, 
                    id_suffix="HUM", 
                    name="Humidity",
                    device_class=SensorDeviceClass.HUMIDITY,
                    native_unit_of_measurement=PERCENTAGE)

    @property
    def native_value(self) -> int:
        return self._device.current_r_h
    
class WhichPM25(Enum):
    CURRENT = 0
    MIN = 1
    MAX = 2

class ikea_vindstyrka_pm25(ikea_base_device_sensor, SensorEntity):
    def __init__(
        self, device: ikea_vindstyrka_device, pm25_type: WhichPM25
    ) -> None:
        logger.debug("ikea_vindstyrka_pm25 ctor...")
        self._pm25_type = pm25_type
        id_suffix = " "
        name_suffix = " "
        if self._pm25_type == WhichPM25.CURRENT:
            id_suffix = "CURPM25"
            name_suffix = "Current PM2.5"
        if self._pm25_type == WhichPM25.MAX:
            id_suffix = "MAXPM25"
            name_suffix = "Max Measured PM2.5"
        if self._pm25_type == WhichPM25.MIN:
            id_suffix = "MINPM25"
            name_suffix = "Min Measured PM2.5"
        
        super().__init__(device, 
                         id_suffix=id_suffix, 
                         name=name_suffix,
                         device_class=SensorDeviceClass.PM25,
                         native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER)

    @property
    def native_value(self) -> int:
        if self._pm25_type == WhichPM25.CURRENT:
            return self._device.current_p_m25
        elif self._pm25_type == WhichPM25.MAX:
            return self._device.max_measured_p_m25
        elif self._pm25_type == WhichPM25.MIN:
            return self._device.min_measured_p_m25
        logger.debug("ikea_vindstyrka_pm25.native_value() shouldnt be here")
        return None

class ikea_vindstyrka_voc_index(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device: ikea_vindstyrka_device) -> None:
        logger.debug("ikea_vindstyrka_voc_index ctor...")
        super().__init__(
            device, 
            id_suffix="VOC", 
            name="VOC Index",
            device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
            native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER)

    @property
    def native_value(self) -> int:
        return self._device.voc_index

# SOMRIG Controllers act differently in the gateway Hub
# While its one device but two id's are sent back each
# representing the two buttons on the controler. The id is
# all same except _1 and _2 suffix. The serial number on the
# controllers is same.

CONTROLLER_BUTTON_MAP = { "SOMRIG shortcut button" : 2 }

class ikea_controller_device(ikea_base_device, SensorEntity):
    def __init__(self,hass:core.HomeAssistant, hub:Hub, json_data:Controller):
        logger.debug("ikea_controller ctor...")
        self._buttons = 1
        if json_data.attributes.model in CONTROLLER_BUTTON_MAP:
            self._buttons = CONTROLLER_BUTTON_MAP[json_data.attributes.model]
            logger.debug(f"Set #buttons to {self._buttons} as controller model is : {json_data.attributes.model}")
        
        super().__init__(hass , hub, json_data, hub.get_controller_by_id)
        self.skip_update = True 
        
    @property
    def entity_category(self):
        return EntityCategory.DIAGNOSTIC
    
    @property
    def icon(self):
        return "mdi:battery"
    
    @property
    def native_value(self):
        return self.battery_percentage

    @property
    def native_unit_of_measurement(self) -> str:
        return "%"

    @property
    def device_class(self) -> str:
        return SensorDeviceClass.BATTERY

    @property
    def number_of_buttons(self) -> int:
        return self._buttons
    
    async def async_update(self):  
        pass

class ikea_starkvind_air_purifier_device(ikea_base_device):
    def __init__(self, hass, hub, json_data) -> None:
        logger.debug("Air purifer Fan device ctor ...")
        super().__init__(hass, hub, json_data, hub.get_air_purifier_by_id)
        self._updated_at = None

    @property
    def supported_features(self) -> FanEntityFeature:
        return FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED|FanEntityFeature.TURN_OFF|FanEntityFeature.TURN_ON

    @property
    def percentage(self) -> int:
        # Scale the 1-50 into
        return math.ceil(self.motor_state * 100 / 50)

    @property
    def preset_modes(self) -> list[str]:
        return [e.value for e in FanModeEnum]
    
    @property
    def preset_mode(self) -> str:
        if self.fan_mode == FanModeEnum.OFF:
            return "off"
        if self.fan_mode == FanModeEnum.LOW:
            return "low"
        if self.fan_mode == FanModeEnum.MEDIUM:
            return "medium"
        if self.fan_mode == FanModeEnum.HIGH:
            return "high"
        return "auto"
        #return self.fan_mode
    
    async def async_update(self):
        if (
            self._updated_at is None
            or (datetime.datetime.now() - self._updated_at).total_seconds() > 30
        ):
            try:
                self._json_data = await self._hass.async_add_executor_job(self._hub.get_air_purifier_by_id, self._json_data.id)
                self._updated_at = datetime.datetime.now()
            except Exception as ex:
                logger.error("error encountered running update on : {}".format(self.name))
                logger.error(ex)
                raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_set_percentage(self, percentage: int) -> None:
        # Convert percent to speed
        desired_speed = math.ceil(percentage * 50 / 100)
        logger.debug("set_percentage got : {}, scaled to : {}".format(percentage, desired_speed))
        await self._hass.async_add_executor_job(self._json_data.set_motor_state, desired_speed)

    async def async_set_status_light(self, status: bool) -> None:
        logger.debug("set_status_light : {}".format(status))
        await self._hass.async_add_executor_job(self._json_data.set_status_light, status)

    async def async_set_child_lock(self, status: bool) -> None:
        logger.debug("set_child_lock : {}".format(status))
        await self._hass.async_add_executor_job(self._json_data.set_child_lock, status)

    async def async_set_fan_mode(self, preset_mode: FanModeEnum) -> None:
        logger.debug("set_fan_mode : {}".format(preset_mode.value))
        await self._hass.async_add_executor_job(self._json_data.set_fan_mode, preset_mode)

    async def async_set_preset_mode(self, preset_mode: str):
        logger.debug("set_preset_mode : {}".format(preset_mode))
        mode_to_set = None
        if preset_mode == "auto":
            mode_to_set = FanModeEnum.AUTO
        elif preset_mode == "high":
            mode_to_set = FanModeEnum.HIGH
        elif preset_mode == "medium":
            mode_to_set = FanModeEnum.MEDIUM
        elif preset_mode == "low":
            mode_to_set = FanModeEnum.LOW
        elif preset_mode == "off":
            mode_to_set = FanModeEnum.OFF
        logger.debug(f"Asked to set preset {preset_mode}")
        if mode_to_set is None:
            logger.error("Non defined preset used to set : {}".format(preset_mode))
            self.preset_mode = mode_to_set
            return

        logger.debug("set_preset_mode equated to : {}".format(mode_to_set.value))
        #await self._hass.async_add_executor_job(self.async_set_fan_mode, mode_to_set)
        await self._hass.async_add_executor_job(self._json_data.set_fan_mode, mode_to_set)
        
    async def async_turn_on(self, percentage=None, preset_mode=None) -> None:
        logger.debug("Airpurifier call to turn_on with percentage: {}, preset_mode: {}".format(percentage, preset_mode))
        
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            logger.debug("We were asked to be turned on but percentage and preset were not set, using last known")
            if self.preset_mode is not None:
                await self.async_set_preset_mode(self.preset_mode)
            elif self.percentage is not None:
                await self.async_set_percentage(self.percentage)
            else:
                logger.debug("No last known value, setting to auto")
                await self.async_set_preset_mode("auto")

    async def async_turn_off(self, **kwargs) -> None:
        await self.async_set_percentage(0)
        #await self._hass.async_add_executor_job(self.set_percentage, 0)

class ikea_starkvind_air_purifier_fan(ikea_base_device_sensor, FanEntity):
    def __init__(self, device: ikea_starkvind_air_purifier_device) -> None:
        logger.debug("Air purifer Fan sensor ctor ...")
        super().__init__(device)
    
    @property
    def percentage(self):
        return self._device.percentage

    @property
    def preset_modes(self) -> list[str]:
        return self._device.preset_modes
    
    @property
    def preset_mode(self):
        return self._device.preset_mode

    # Property Doesnt Exist
    @property
    def speed_count(self):
        return 50

    @property
    def supported_features(self) -> FanEntityFeature:
        return  self._device.supported_features
    
    async def async_set_percentage(self, percentage: int) -> None:
        await self._device.async_set_percentage(percentage)

    async def async_set_preset_mode(self, preset_mode: str):
        await self._device.async_set_preset_mode(preset_mode)

    async def async_set_fan_mode(self, preset_mode: FanModeEnum) -> None:
        await self._device.async_set_fan_mode(preset_mode)
        
    async def async_turn_on(self, percentage=None, preset_mode=None) -> None:
        await self._device.async_turn_on(percentage, preset_mode)

    async def async_turn_off(self, **kwargs) -> None:
        await self._device.async_turn_off()

class ikea_starkvind_air_purifier_sensor(ikea_base_device_sensor, SensorEntity):
    def __init__(
        self,
        device: ikea_starkvind_air_purifier_device,
        prefix: str,
        device_class: SensorDeviceClass,
        native_value_prop: str,
        native_unit_of_measurement: str,
        icon_name: str,
    ):
        logger.debug("ikea_starkvind_air_purifier_sensor ctor ...")
        super().__init__(
                    device,
                    id_suffix=prefix,
                    name=prefix,
                    device_class=device_class,
                    native_unit_of_measurement=native_uom,
                    icon=icon_name)

        self._native_value_prop = native_value_prop

    @property
    def native_value(self):
        return getattr(self._device, self._native_value_prop)

    async def async_turn_off(self):
        pass 

    async def async_turn_on(self):
        pass 

class ikea_starkvind_air_purifier_binary_sensor(ikea_base_device_sensor, BinarySensorEntity):
    def __init__(
        self,
        device: ikea_starkvind_air_purifier_device,
        device_class: BinarySensorDeviceClass,
        prefix: str,
        native_value_prop: str,
        icon_name: str,
    ):
        logger.debug("ikea_starkvind_air_purifier_binary_sensor ctor ...")
        super().__init__(
                            device,
                            id_suffix=prefix,
                            name=prefix,
                            device_class=device_class,
                            icon=icon_name)
        
        self._native_value_prop = native_value_prop
        device.add_listener(self)
    
    @property
    def is_on(self):
        return getattr(self._device, self._native_value_prop)
        
    def async_turn_off(self):
        pass

    def async_handle_turn_on_service(self):
        pass

class ikea_starkvind_air_purifier_switch_sensor(ikea_base_device_sensor, SwitchEntity):
    def __init__(
        self,
        device: ikea_starkvind_air_purifier_device,
        prefix: str,
        is_on_prop: str,
        turn_on_off_fx: str,
        icon_name: str,
    ):
        logger.debug("ikea_starkvind_air_purifier_switch_sensor ctor...")
        super().__init__(
                            device,
                            id_suffix=prefix,
                            name=prefix,
                            device_class=SwitchDeviceClass.OUTLET,
                            icon=icon_name)
        self._is_on_prop = is_on_prop
        self._turn_on_off = getattr(self._device, turn_on_off_fx)

    @property
    def is_on(self):
        return getattr(self._device, self._is_on_prop)
         
    async def async_turn_on(self):
        logger.debug("{} turn_on".format(self.name))
        try:
            await self._turn_on_off(True)
        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_turn_off(self):
        logger.debug("{} turn_off".format(self.name))
        try:
            await self._turn_on_off(False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")
                    
class battery_percentage_sensor(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="BP01",
                            name="Battery Percentage",
                            native_unit_of_measurement=PERCENTAGE,
                            state_class=SensorStateClass.MEASUREMENT,
                            #uom="%",
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
                            #uom="A",
                            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                            state_class=SensorStateClass.MEASUREMENT,
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
                            native_unit_of_measurement=UnitOfPower.WATT,
                            icon="mdi:lightning-bolt-outline",
                            device_class=SensorDeviceClass.POWER)

    @property
    def native_value(self):
        return getattr(self._device, "current_active_power")
    
class current_voltage_sensor(ikea_base_device_sensor, SensorEntity):
    
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="CV01",
                            name="Current Voltage",
                            #uom="V",
                            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                            state_class=SensorStateClass.MEASUREMENT,
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
                            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
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
                            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
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
                            device_class=SensorDeviceClass.TIMESTAMP,
                            name="Time of Last Energy Reset",
                            icon="mdi:update")

    @property
    def native_value(self):
        # Hack
        value = getattr(self._device, "time_of_last_energy_reset")
        if type(value) == str:
            #convert to datetime
            logger.debug(f"Found time_of_last_energy_reset as string attempting convert to datetime")
            self.time_of_last_energy_reset = value 
        return getattr(self._device, "time_of_last_energy_reset")

    @property
    def time_of_last_energy_reset(self):
        return self.native_value()
    
    @time_of_last_energy_reset.setter
    def time_of_last_energy_reset(self, value):
        # This is called from hub events where its a str
        try:
            dt_value = datetime.datetime.strptime(value, DATE_TIME_FORMAT)
            setattr(self._device,"time_of_last_energy_reset",dt_value)
        except:
            logger.warning(f"Failed to set time_of_last_energy_reset in sensor using value : {value}")
 
class total_energy_consumed_last_updated_sensor(ikea_base_device_sensor, DateTimeEntity):
    def __init__(self, device):
        super().__init__(   device,
                            id_suffix="TECLU01",
                            name="Total Energy Consumed Last Updated",
                            device_class=SensorDeviceClass.TIMESTAMP,
                            icon="mdi:update")
    
    def __init__(self, device):
        super().__init__(
                            device = device, 
                            id_suffix="TECLU01",
                            device_class=SensorDeviceClass.TIMESTAMP,
                            name="Time Energy Consumed Last Updated",
                            icon="mdi:update")

    @property
    def native_value(self):
        return getattr(self._device, "total_energy_consumed_last_updated")
    
    @property
    def total_energy_consumed_last_updated(self):
        return self.native_value()
    
    @total_energy_consumed_last_updated.setter
    def time_of_last_energy_reset(self, value):
        # This is called from hub events where its a str
        try:
            dt_value = datetime.datetime.strptime(value, DATE_TIME_FORMAT)
            setattr(self._device,"total_energy_consumed_last_updated",dt_value)
        except:
            logger.warning(f"Failed to set total_energy_consumed_last_updated in sensor using value : {value}")
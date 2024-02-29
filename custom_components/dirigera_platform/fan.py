from homeassistant import config_entries, core
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass

from homeassistant.components.fan import FanEntity, FanEntityFeature

from .dirigera_lib_patch import HubX
from dirigera.devices.air_purifier import FanModeEnum

from .const import DOMAIN
from .mocks.ikea_air_purifier_mock import ikea_starkvind_air_purifier_mock_device
import datetime 
import logging
import math 

logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("FAN/AirPurifier Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger.debug(config)

    hub = HubX(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    
    air_purifiers = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":   
        logger.warning("Setting up mock air purifier")
        mock_air_purifier1 = ikea_starkvind_air_purifier_mock_device()
        air_purifiers = [mock_air_purifier1] 
        #ikea_vindstyrka_temperature.async_will_remove_from_hass = ikea_vindstyrka_device_mock.async_will_remove_from_hass

    else:            
        hub_air_purifiers = await hass.async_add_executor_job(hub.get_air_purifiers)
        air_purifiers = [ikea_starkvind_air_purifier_device(hub, air_purifier) for air_purifier in hub_air_purifiers]

    sensor_to_add = []
    logger.debug("Found {} air_purifier devices to setup...".format(len(air_purifiers)))
    
    for air_purifier_device in air_purifiers:
        # Fan Entity
        sensor_to_add.append(ikea_starkvind_air_purifier_fan(air_purifier_device))
        
        # Separate BinarySensor Entitiy is created for the following
        # 1. filterAlarmStatus  - BinarySensor
        sensor_to_add.append(ikea_starkvind_air_purifier_binary_sensor(air_purifier_device, BinarySensorDeviceClass.PROBLEM,"Filter Alarm Status","filter_alarm_status","mdi:alarm-light-outline"))
        
        # Seperate SwitchEnity are created for the folllwing
        # 1. childLock          - BinarySensor
        # 2. statusLight        - BinarySensor
        sensor_to_add.append(ikea_starkvind_air_purifier_switch_sensor(air_purifier_device,"Child Lock","child_lock","set_child_lock","mdi:account-lock-outline"))
        sensor_to_add.append(ikea_starkvind_air_purifier_switch_sensor(air_purifier_device,"Status Light","status_light","set_status_light","mdi:lightbulb"))

         # Seperate SensorEntity are created for the folllwing
        # 1. filterLifeTime     - Sensor
        # 2. filterElapsedtime  - Sensor
        # 3. CurrentPM25        - Sensor
        # 4. MotorRunTime       - Sensor
        sensor_to_add.append(ikea_starkvind_air_purifier_sensor(air_purifier_device,"Filter Lifetime",SensorDeviceClass.DURATION,"filter_lifetime","min","mdi:clock-time-eleven-outline"))
        sensor_to_add.append(ikea_starkvind_air_purifier_sensor(air_purifier_device,"Filter Elapsed Time",SensorDeviceClass.DURATION,"filter_elapsed_time","min","mdi:timelapse"))
        sensor_to_add.append(ikea_starkvind_air_purifier_sensor(air_purifier_device,"Current pm25",SensorDeviceClass.PM25,"current_p_m25","µg/m³","mdi:molecule"))
        sensor_to_add.append(ikea_starkvind_air_purifier_sensor(air_purifier_device,"Motor Runtime",SensorDeviceClass.DURATION,"motor_runtime","min","mdi:run-fast"))

    async_add_entities(sensor_to_add)
    logger.debug("FAN/AirPurifier Complete async_setup_entry")

class ikea_starkvind_air_purifier_device:
    def __init__(self, hub, json_data) -> None:
        self._json_data = json_data 
        self._updated_at = None 
        self._hub = hub 
        self._updated_at = None 
        logger.debug("Air purifer Fan Entity ctor complete...")
    
    def update(self):
        if self._updated_at is None or \
            (datetime.datetime.now() - self._updated_at).total_seconds() > 30:
            try:
                self._json_data = self._hub.get_air_purifier_by_id(self._json_data.id)
                self._updated_at = datetime.datetime.now()
            except Exception as ex:
                logger.error("error encountered running update on : {}".format(self.name))
                logger.error(ex)
                raise HomeAssistantError(ex,DOMAIN,"hub_exception")
        
    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform",self._json_data.id)},
            name = self._json_data.attributes.custom_name,
            manufacturer = self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model ,
            sw_version=self._json_data.attributes.firmware_version
        )
    
    @property
    def name(self) -> str:
        return self._json_data.attributes.custom_name
    
    @property
    def unique_id(self):
        return self._json_data.id
    
    @property
    def supported_features(self):
        return FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED
    
    @property
    def motor_state(self) -> int:
        return self._json_data.attributes.motor_state 
    
    @property
    def percentage(self) -> int:
        # Scale the 1-50 into 
        return math.ceil(self.motor_state * 100/50)
    
    @property
    def fan_mode_sequence(self) -> str:
        return self._json_data.attributes.fan_mode_sequence 
    
    @property
    def preset_modes(self):
        return [ e.value for e in FanModeEnum]
    
    @property
    def preset_mode(self) -> str:
        return self._json_data.attributes.fan_mode 
    
    @property
    def speed_count(self):
        return 50 
    
    @property
    def motor_runtime(self):
        return self._json_data.attributes.motor_runtime
    
    @property
    def filter_alarm_status(self) -> bool:
        return self._json_data.attributes.filter_alarm_status 
    
    @property
    def filter_elapsed_time(self) -> int:
        return self._json_data.attributes.filter_elapsed_time 
    
    @property
    def filter_lifetime(self) -> int:
        return self._json_data.attributes.filter_lifetime
    
    @property
    def current_p_m25(self) -> int:
        return self._json_data.attributes.current_p_m25
    
    @property
    def status_light(self) -> bool:
        return self._json_data.attributes.status_light
    
    @property
    def child_lock(self) -> bool:
        return self._json_data.attributes.child_lock

    @property
    def is_on(self):
        if self.available and self.motor_state > 0:
            return True 
        return False 
    
    def set_percentage(self, percentage: int) -> None:
        # Convert percent to speed
        desired_speed = math.ceil(percentage * 50 / 100)
        logger.debug("set_percentage got : {}, scaled to : {}".format(percentage, desired_speed))
        self._json_data.set_motor_state(desired_speed)    

    def set_status_light(self, status:bool) -> None:
        logger.debug("set_status_light : {}".format(status))
        self._json_data.set_status_light(status)
    
    def set_child_lock(self, status: bool) -> None:
        logger.debug("set_child_lock : {}".format(status))
        self._json_data.set_child_lock(status)

    def set_fan_mode(self, preset_mode: FanModeEnum) -> None:
        logger.debug("set_fan_mode : {}".format(preset_mode.value))
        self._json_data.set_fan_mode(preset_mode)

    def set_preset_mode(self, preset_mode: str):
        logger.debug("set_preset_mode : {}".format(preset_mode))
        mode_to_set = None 
        if preset_mode == 'auto':
            mode_to_set = FanModeEnum.AUTO
        elif preset_mode == 'high':
            mode_to_set = FanModeEnum.HIGH
        elif preset_mode == 'medium':
            mode_to_set = FanModeEnum.MEDIUM
        elif preset_mode == 'low':
            mode_to_set = FanModeEnum.LOW
    
        if mode_to_set is None:
            logger.error("Non defined preset used to set : {}".format(preset_mode))
            return 
        
        logger.debug("set_preset_mode equated to : {}".format(mode_to_set.value))
        self.set_fan_mode(mode_to_set)

    def turn_on(self, percentage = None, preset_mode = None) -> None:
        logger.debug("Airpurifier call to turn_on with percentage: {}, preset_mode: {}".format(percentage, preset_mode))
        if preset_mode is not None:
            self.set_preset_mode(preset_mode)
        elif percentage is not None:
            self.set_percentage(percentage)
        else:
            logger.debug("We were asked to be turned on but percentage and preset were not set, using last known")
            if self.preset_mode is not None:
                self.set_preset_mode(self.preset_mode)
            elif self.percentage is not None:
                self.set_percentage(self.percentage)
            else:
                logger.debug("No last known value, setting to auto")
                self.set_preset_mode("auto")
    
    def turn_off(self, **kwargs) -> None:
        self.set_percentage(0)

class ikea_starkvind_air_purifier_fan(FanEntity):
    def __init__(self, device:ikea_starkvind_air_purifier_device) -> None:
        self._device = device 

    @property
    def available(self):
        return self._device.available
      
    @property
    def device_info(self) -> DeviceInfo:
        return self._device.device_info
    
    @property
    def name(self):
        return self._device.name
    
    @property
    def preset_mode(self):
        return self._device.preset_mode
    
    @property
    def speed_count(self):
        return self._device.speed_count

    @property
    def unique_id(self) -> str:
        return self._device.unique_id

    @property
    def supported_features(self):
        return self._device.supported_features
    
    @property
    def is_on(self):
        return self._device.is_on
    
    @property 
    def percentage(self):
        return self._device.percentage
    
    @property
    def preset_mode(self):
        return self._device.preset_mode
    
    @property
    def preset_modes(self):
        return self._device.preset_modes
    
    @property
    def speed_count(self):
        return self._device.speed_count
    
    def update(self):
        self._device.update()
    
    def set_percentage(self, percentage: int) -> None:
        self._device.set_percentage(percentage)

    def set_preset_mode(self, preset_mode: str):
        self._device.set_preset_mode(preset_mode)
    
    def turn_on(self,  percentage = None, preset_mode = None) -> None:
        self._device.turn_on(percentage, preset_mode)
    
    def turn_off(self, **kwargs) -> None:
        self._device.turn_off()
    
class ikea_starkvind_air_purifier_sensor(SensorEntity):
    def __init__(self, device:ikea_starkvind_air_purifier_device, prefix: str, device_class: SensorDeviceClass, native_value_prop: str, native_uom: str, icon_name: str):
        self._device = device
        self._prefix = prefix
        self._native_value_prop = native_value_prop
        self._device_class = device_class
        self._native_unit_of_measurement = native_uom
        self._icon = icon_name 
    
    def update(self):
        self._device.update()

    @property
    def icon(self):
        return self._icon
    
    @property
    def name(self):
        return self._device.name + " " + self._prefix.replace("_"," ") 
    
    @property
    def unique_id(self) -> str:
        return self._device.unique_id + self._prefix
    
    @property
    def available(self):
        return self._device.available
      
    @property
    def device_info(self) -> DeviceInfo:
        return self._device.device_info
    
    @property
    def device_class(self):
        return self._device_class

    @property
    def native_unit_of_measurement(self) -> str:
        return self._native_unit_of_measurement
    
    @property
    def native_value(self):
        return getattr(self._device, self._native_value_prop)

class ikea_starkvind_air_purifier_binary_sensor(BinarySensorEntity):
    def __init__(self, device:ikea_starkvind_air_purifier_device, device_class: BinarySensorDeviceClass, prefix: str, native_value_prop: str, icon_name: str):
        self._device = device
        self._prefix = prefix
        self._device_class = device_class
        self._native_value_prop = native_value_prop
        self._icon = icon_name 

    def update(self):
        self._device.update()

    @property
    def icon(self):
        return self._icon

    @property
    def name(self):
        return self._device.name + " " + self._prefix.replace("_"," ")  
    
    @property
    def unique_id(self) -> str:
        return self._device.unique_id + self._prefix
    
    @property
    def available(self):
        return self._device.available
      
    @property
    def device_info(self) -> DeviceInfo:
        return self._device.device_info
    
    @property
    def device_class(self):
        return self._device_class
    
    @property
    def is_on(self):
        return getattr(self._device, self._native_value_prop)
    
    def async_turn_off(self):
        pass 

    def async_handle_turn_on_service(self):
        pass 

class ikea_starkvind_air_purifier_switch_sensor(SwitchEntity):
    def __init__(self, device:ikea_starkvind_air_purifier_device, prefix: str, is_on_prop: str, turn_on_off_fx: str, icon_name: str):
        self._device = device
        self._prefix = prefix
        self._is_on_prop = is_on_prop
        self._turn_on_off = getattr(self._device, turn_on_off_fx)
        self._icon = icon_name 

    def update(self):
        self._device.update()

    @property
    def icon(self):
        return self._icon

    @property
    def name(self):
        return self._device.name + " " + self._prefix.replace("_"," ")  
    
    @property
    def unique_id(self) -> str:
        return self._device.unique_id + self._prefix
    
    @property
    def available(self):
        return self._device.available
      
    @property
    def device_info(self) -> DeviceInfo:
        return self._device.device_info
    
    @property
    def device_class(self):
        return SwitchDeviceClass.OUTLET
    
    @property
    def is_on(self):
        logger.debug("ikea_starkvind_air_purifier_switch_sensor is_on call..")
        return getattr(self._device, self._is_on_prop)

    def async_handle_turn_on_service(self):
        logger.debug("{} turn_on".format(self.name))
        try:
            self._turn_on_off(True)
        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
    
    def turn_off(self):
        logger.debug("{} turn_off".format(self.name))
        try:
            self._turn_on_off(False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
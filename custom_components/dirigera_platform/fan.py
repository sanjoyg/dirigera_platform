import datetime
import logging
import math

from dirigera import Hub
from dirigera.devices.air_purifier import FanModeEnum
from dirigera.devices.air_purifier import AirPurifier

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import Entity
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError

from .const import DOMAIN
from .mocks.ikea_air_purifier_mock import ikea_starkvind_air_purifier_mock_device
from .base_classes import ikea_base_device, ikea_base_device_sensor

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

    hub = Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    air_purifiers = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":
        logger.warning("Setting up mock air purifier")
        mock_air_purifier1 = ikea_starkvind_air_purifier_mock_device()
        air_purifiers = [mock_air_purifier1]
        # ikea_vindstyrka_temperature.async_will_remove_from_hass = ikea_vindstyrka_device_mock.async_will_remove_from_hass

    else:
        hub_air_purifiers : list[AirPurifier] = await hass.async_add_executor_job(hub.get_air_purifiers)
        air_purifier_devices : list[ikea_starkvind_air_purifier_device] = [ikea_starkvind_air_purifier_device(hass, hub, a) for a in hub_air_purifiers]

    sensor_to_add = []
    logger.debug("Found {} air_purifier devices to setup...".format(len(air_purifiers)))

    for device in air_purifier_devices:
        # Fan Entity
        sensor_to_add.append(ikea_starkvind_air_purifier_fan(device))

        # Separate BinarySensor Entitiy is created for the following
        # 1. filterAlarmStatus  - BinarySensor
        sensor_to_add.append(
            ikea_starkvind_air_purifier_binary_sensor(
                device,
                BinarySensorDeviceClass.PROBLEM,
                "Filter Alarm Status",
                "filter_alarm_status",
                "mdi:alarm-light-outline",
            )
        )

        # Seperate SwitchEnity are created for the folllwing
        # 1. childLock          - BinarySensor
        # 2. statusLight        - BinarySensor
        sensor_to_add.append(
            ikea_starkvind_air_purifier_switch_sensor(
                device,
                "Child Lock",
                "child_lock",
                "async_set_child_lock",
                "mdi:account-lock-outline",
            )
        )
        sensor_to_add.append(
            ikea_starkvind_air_purifier_switch_sensor(
                device,
                "Status Light",
                "status_light",
                "async_set_status_light",
                "mdi:lightbulb",
            )
        )

        # Seperate SensorEntity are created for the folllwing
        # 1. filterLifeTime     - Sensor
        # 2. filterElapsedtime  - Sensor
        # 3. CurrentPM25        - Sensor
        # 4. MotorRunTime       - Sensor
        sensor_to_add.append(
            ikea_starkvind_air_purifier_sensor(
                device,
                "Filter Lifetime",
                SensorDeviceClass.DURATION,
                "filter_lifetime",
                "min",
                "mdi:clock-time-eleven-outline",
            )
        )
        sensor_to_add.append(
            ikea_starkvind_air_purifier_sensor(
                device,
                "Filter Elapsed Time",
                SensorDeviceClass.DURATION,
                "filter_elapsed_time",
                "min",
                "mdi:timelapse",
            )
        )
        sensor_to_add.append(
            ikea_starkvind_air_purifier_sensor(
                device,
                "Current pm25",
                SensorDeviceClass.PM25,
                "current_p_m25",
                "µg/m³",
                "mdi:molecule",
            )
        )
        sensor_to_add.append(
            ikea_starkvind_air_purifier_sensor(
                device,
                "Motor Runtime",
                SensorDeviceClass.DURATION,
                "motor_runtime",
                "min",
                "mdi:run-fast",
            )
        )

    async_add_entities(sensor_to_add)
    logger.debug("FAN/AirPurifier Complete async_setup_entry")

class ikea_starkvind_air_purifier_device(ikea_base_device):
    def __init__(self, hass, hub, json_data) -> None:
        logger.debug("Air purifer Fan device ctor ...")
        super().__init__(hass, hub, json_data, hub.get_air_purifier_by_id)
        self._updated_at = None

    @property
    def supported_features(self) -> FanEntityFeature:
        return FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED

    @property
    def percentage(self) -> int:
        # Scale the 1-50 into
        return math.ceil(self.motor_state * 100 / 50)

    @property
    def preset_modes(self) -> list[str]:
        return [e.value for e in FanModeEnum]
    
    @property
    def preset_mode(self) -> str:
        return self.fan_mode
    
    async def async_update(self):
        if (
            self._updated_at is None
            or (datetime.datetime.now() - self._updated_at).total_seconds() > 30
        ):
            try:
                self._json_data = await self._hass.async_add_executor_job(self._hub.get_air_purifier_by_id, self._json_data.id)
                self._updated_at = datetime.datetime.now()
            except Exception as ex:
                logger.error(
                    "error encountered running update on : {}".format(self.name)
                )
                logger.error(ex)
                raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_set_percentage(self, percentage: int) -> None:
        # Convert percent to speed
        desired_speed = math.ceil(percentage * 50 / 100)
        logger.debug(
            "set_percentage got : {}, scaled to : {}".format(percentage, desired_speed)
        )
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
        logger.debug(
            "Airpurifier call to turn_on with percentage: {}, preset_mode: {}".format(
                percentage, preset_mode
            )
        )
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            logger.debug(
                "We were asked to be turned on but percentage and preset were not set, using last known"
            )
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
        return FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED
    
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
        native_uom: str,
        icon_name: str,
    ):
        logger.debug("ikea_starkvind_air_purifier_sensor ctor ...")
        super().__init__(device)
        self._prefix = prefix
        self._native_value_prop = native_value_prop
        self._device_class = device_class
        self._native_unit_of_measurement = native_uom
        self._icon = icon_name

    @property
    def icon(self):
        return self._icon

    @property
    def name(self):
        return self._device.name + " " + self._prefix.replace("_", " ")

    @property
    def unique_id(self) -> str:
        return self._device.unique_id + self._prefix

    @property
    def device_class(self):
        return self._device_class

    @property
    def native_unit_of_measurement(self) -> str:
        return self._native_unit_of_measurement

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
        super().__init__(device)
        self._prefix = prefix
        self._device_class = device_class
        self._native_value_prop = native_value_prop
        self._icon = icon_name
        device.add_listener(self)
    
    @property
    def icon(self):
        return self._icon

    @property
    def name(self):
        return self._device.name + " " + self._prefix.replace("_", " ")

    @property
    def unique_id(self) -> str:
        return self._device.unique_id + self._prefix

    @property
    def device_class(self):
        return self._device_class

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
        super().__init__(device)
        self._prefix = prefix
        self._is_on_prop = is_on_prop
        self._turn_on_off = getattr(self._device, turn_on_off_fx)
        self._icon = icon_name

    @property
    def icon(self):
        return self._icon

    @property
    def name(self):
        return self._device.name + " " + self._prefix.replace("_", " ")

    @property
    def unique_id(self) -> str:
        return self._device.unique_id + self._prefix

    @property
    def device_class(self):
        return SwitchDeviceClass.OUTLET

    async def async_handle_turn_on_service(self):
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
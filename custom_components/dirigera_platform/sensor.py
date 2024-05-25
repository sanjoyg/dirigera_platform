import datetime
from enum import Enum
import logging

from dirigera import Hub
from dirigera.devices.environment_sensor import EnvironmentSensor
from dirigera.devices.controller import Controller

from homeassistant.helpers.entity import Entity
from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .base_classes import ikea_base_device, ikea_base_device_sensor
logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("EnvSensor & Controllers Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger.debug(config)

    hub = Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    env_devices = []
    controller_devices = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":
        logger.warning("Setting up mock environment sensors")
        from .mocks.ikea_vindstyrka_mock import ikea_vindstyrka_device_mock

        mock_env_device = ikea_vindstyrka_device_mock()
        env_devices = [mock_env_device]

        logger.warning("Setting up mock controllers")
        from .mocks.ikea_controller_mock import ikea_controller_mock

        mock_controller1 = ikea_controller_mock()
        controller_devices = [mock_controller1]

        ikea_vindstyrka_temperature.async_will_remove_from_hass = (
            ikea_vindstyrka_device_mock.async_will_remove_from_hass
        )
    else:
        hub_devices = await hass.async_add_executor_job(hub.get_environment_sensors)
        env_devices = [
            ikea_vindstyrka_device(hass, hub, env_device) for env_device in hub_devices
        ]

        hub_controllers = await hass.async_add_executor_job(hub.get_controllers)
        controller_devices = [
            ikea_controller(hass, hub, controller_device)
            for controller_device in hub_controllers
            # Only create a battery sensor entity if the device reports battery percentage
            # This is not the case of the second device for SOMRIG controllers
            if controller_device.attributes.battery_percentage
        ]

    env_sensors = []
    for env_device in env_devices:
        # For each device setup up multiple entities
        env_sensors.append(ikea_vindstyrka_temperature(env_device))
        env_sensors.append(ikea_vindstyrka_humidity(env_device))
        env_sensors.append(ikea_vindstyrka_pm25(env_device, WhichPM25.CURRENT))
        env_sensors.append(ikea_vindstyrka_pm25(env_device, WhichPM25.MAX))
        env_sensors.append(ikea_vindstyrka_pm25(env_device, WhichPM25.MIN))
        env_sensors.append(ikea_vindstyrka_voc_index(env_device))

    logger.debug("Found {} env devices to setup...".format(len(env_devices)))
    logger.debug("Found {} env entities to setup...".format(len(env_sensors)))
    logger.debug("Found {} controller devices to setup...".format(len(controller_devices)))

    async_add_entities(env_sensors)
    async_add_entities(controller_devices)

    logger.debug("EnvSensor & Controllers Complete async_setup_entry")

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
                logger.error(
                    "error encountered running update on : {}".format(self.name)
                )
                logger.error(ex)
                raise HomeAssistantError(ex, DOMAIN, "hub_exception")

class ikea_vindstyrka_temperature(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device: ikea_vindstyrka_device) -> None:
        super().__init__(device, id_suffix="TEMP", name_suffix="Temperature")
        logger.debug("ikea_vindstyrka_temperature ctor...")

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    @property
    def native_value(self) -> float:
        return self._device.current_temperature

    @property
    def native_unit_of_measurement(self) -> str:
        return "°C"

    @property
    def state_class(self) -> str:
        return "measurement"

class ikea_vindstyrka_humidity(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device: ikea_vindstyrka_device) -> None:
        logger.debug("ikea_vindstyrka_humidity ctor...")
        super().__init__(device, id_suffix="HUM", name_suffix="Humidity")

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    @property
    def native_value(self) -> int:
        return self._device.current_r_h

    @property
    def native_unit_of_measurement(self) -> str:
        return "%"

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

        super().__init__(device, id_suffix=id_suffix, name_suffix=name_suffix)

    @property
    def device_class(self):
        return SensorDeviceClass.PM25

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

    @property
    def native_unit_of_measurement(self) -> str:
        return "µg/m³"

class ikea_vindstyrka_voc_index(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device: ikea_vindstyrka_device) -> None:
        logger.debug("ikea_vindstyrka_voc_index ctor...")
        super().__init__(device, id_suffix="VOC", name_suffix="VOC Index")

    @property
    def device_class(self):
        return SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS

    @property
    def native_value(self) -> int:
        return self._device.voc_index

    @property
    def native_unit_of_measurement(self) -> str:
        return "µg/m³"

class ikea_controller(ikea_base_device, SensorEntity):
    def __init__(self,hass:core.HomeAssistant, hub:Hub, json_data:Controller):
        logger.debug("ikea_controller ctor...")
        super().__init__(hass , hub, json_data, hub.get_controller_by_id)

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

# SOMRIG Controllers act differently in the gateway Hub
# While its one device but two id's are sent back each
# representing the two buttons on the controler. The id is
# all same except _1 and _2 suffix. The serial number on the
# controllers is same.
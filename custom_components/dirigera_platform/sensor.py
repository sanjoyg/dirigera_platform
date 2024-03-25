import datetime
from enum import Enum
import logging

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .dirigera_lib_patch import HubX

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

    hub = HubX(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

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
            ikea_vindstyrka_device(hub, env_device) for env_device in hub_devices
        ]

        hub_controllers = await hass.async_add_executor_job(hub.get_controllers)
        controller_devices = [
            ikea_controller(hub, controller_device)
            for controller_device in hub_controllers
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


class ikea_vindstyrka_device:
    def __init__(self, hub, json_data) -> None:
        self._json_data = json_data
        self._updated_at = None
        self._hub = hub

    def update(self):
        if (
            self._updated_at is None
            or (datetime.datetime.now() - self._updated_at).total_seconds() > 30
        ):
            try:
                self._json_data = self._hub.get_environment_sensor_by_id(
                    self._json_data.id
                )
                self._updated_at = datetime.datetime.now()
            except Exception as ex:
                logger.error(
                    "error encountered running update on : {}".format(self.name)
                )
                logger.error(ex)
                raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    def get_current_temperature(self):
        return self._json_data.attributes.current_temperature

    def get_current_r_h(self):
        return self._json_data.attributes.current_r_h

    def get_current_p_m25(self):
        return self._json_data.attributes.current_p_m25

    def get_max_measured_p_m25(self):
        return self._json_data.attributes.max_measured_p_m25

    def get_min_measured_p_m25(self):
        return self._json_data.attributes.min_measured_p_m25

    def get_voc_index(self):
        return self._json_data.attributes.voc_index

    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform", self._json_data.id)},
            name=self._json_data.attributes.custom_name,
            manufacturer=self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model,
            sw_version=self._json_data.attributes.firmware_version,
        )

    @property
    def name(self) -> str:
        return self._json_data.attributes.custom_name

    @property
    def unique_id(self):
        return self._json_data.id


class ikea_env_base_entity(SensorEntity):
    def __init__(
        self, ikea_env_device: ikea_vindstyrka_device, id_suffix: str, name_suffix: str
    ):
        logger.debug("ikea_env_base_entity ctor...")
        self._ikea_env_device = ikea_env_device
        self._unique_id = self._ikea_env_device.unique_id + id_suffix
        self._name = self._ikea_env_device.name + " " + name_suffix

    @property
    def available(self):
        return self._ikea_env_device.available

    @property
    def device_info(self) -> DeviceInfo:
        return self._ikea_env_device.device_info

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def native_value(self):
        return int

    def update(self):
        self._ikea_env_device.update()


class ikea_vindstyrka_temperature(ikea_env_base_entity):
    def __init__(self, ikea_env_device: ikea_vindstyrka_device) -> None:
        super().__init__(ikea_env_device, "TEMP", "Temperature")
        logger.debug("ikea_vindstyrka_temperature ctor...")

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    @property
    def native_value(self) -> float:
        return self._ikea_env_device.get_current_temperature()

    @property
    def native_unit_of_measurement(self) -> str:
        return "°C"

    @property
    def state_class(self) -> str:
        return "measurement"


class ikea_vindstyrka_humidity(ikea_env_base_entity):
    def __init__(self, ikea_env_device: ikea_vindstyrka_device) -> None:
        logger.debug("ikea_vindstyrka_humidity ctor...")
        super().__init__(ikea_env_device, "HUM", "Humidity")

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    @property
    def native_value(self) -> int:
        return self._ikea_env_device.get_current_r_h()

    @property
    def native_unit_of_measurement(self) -> str:
        return "%"


class WhichPM25(Enum):
    CURRENT = 0
    MIN = 1
    MAX = 2


class ikea_vindstyrka_pm25(ikea_env_base_entity):
    def __init__(
        self, ikea_env_device: ikea_vindstyrka_device, pm25_type: WhichPM25
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

        super().__init__(ikea_env_device, id_suffix, name_suffix)

    @property
    def device_class(self):
        return SensorDeviceClass.PM25

    @property
    def native_value(self) -> int:
        if self._pm25_type == WhichPM25.CURRENT:
            return self._ikea_env_device.get_current_p_m25()
        if self._pm25_type == WhichPM25.MAX:
            return self._ikea_env_device.get_max_measured_p_m25()
        if self._pm25_type == WhichPM25.MIN:
            return self._ikea_env_device.get_min_measured_p_m25()
        logger.debug("ikea_vindstyrka_pm25.native_value() shouldnt be here")
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        return "µg/m³"


class ikea_vindstyrka_voc_index(ikea_env_base_entity):
    def __init__(self, ikea_env_device: ikea_vindstyrka_device) -> None:
        logger.debug("ikea_vindstyrka_voc_index ctor...")
        super().__init__(ikea_env_device, "VOC", "VOC Index")

    @property
    def device_class(self):
        return SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS

    @property
    def native_value(self) -> int:
        return self._ikea_env_device.get_voc_index()

    @property
    def native_unit_of_measurement(self) -> str:
        return "µg/m³"


class ikea_controller(SensorEntity):
    def __init__(self, hub, json_data):
        logger.debug("ikea_controller ctor...")
        self._hub = hub
        self._json_data = json_data

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform", self._json_data.id)},
            name=self._json_data.attributes.custom_name,
            manufacturer=self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model,
            sw_version=self._json_data.attributes.firmware_version,
        )

    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def unique_id(self):
        return self._json_data.id

    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def name(self):
        return self._json_data.attributes.custom_name

    @property
    def is_on(self):
        return self._json_data.attributes.is_on

    #@property
    #def device_info(self) -> DeviceInfo:
    #    return SensorDeviceClass.BATTERY

    @property
    def icon(self):
        return "mdi:battery"
    
    @property
    def native_value(self):
        return self._json_data.attributes.battery_percentage

    @property
    def native_unit_of_measurement(self) -> str:
        return "%"

    def update(self):
        logger.debug("controller update...")
        try:
            self._json_data = self._hub.get_controller_by_name(
                self._json_data.attributes.custom_name
            )
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

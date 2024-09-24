import datetime
from enum import Enum
import logging

from dirigera import Hub
from dirigera.devices.outlet import Outlet

from .switch import ikea_outlet
from .dirigera_lib_patch import HubX
from dirigera.devices.environment_sensor import EnvironmentSensor
from dirigera.devices.controller import Controller

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
    logger.error("Staring async_setup_entry in SENSOR...")
    logger.error(dict(config_entry.data))
    logger.error(f"async_setup_entry SENSOR {config_entry.unique_id} {config_entry.state} {config_entry.entry_id} {config_entry.title} {config_entry.domain}")
    
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
            ikea_vindstyrka_device(hass, hub, env_device) for env_device in hub_devices
        ]

        hub_controllers = await hass.async_add_executor_job(hub.get_controllers)
        logger.error(f"Got {len(hub_controllers)} controllers...")
        
        # Controllers with more one button are returned as spearate controllers
        # their uniqueid has _1, _2 suffixes. Only the primary controller has 
        # battery % attribute which we shall use to identify
        controller_devices = []
        
        for controller_device in hub_controllers:
            controller: ikea_controller = ikea_controller(hass, hub, controller_device)
            
            # Hack to create empty scene so that we can associate it the controller
            # so that click of buttons on the controller can generate events on the hub
            #hub.create(name=f"dirigera_platform_empty_scene_{controller.unique_id}",icon="scenes_heart")
            
            scene_name=f"dirigera_platform_empty_scene_{controller.unique_id}"
            logger.error(f"Creating empty scene {scene_name} for controller {controller.unique_id}...")
            await hass.async_add_executor_job(hub.create_empty_scene,scene_name, controller.unique_id)
            
            if controller_device.attributes.battery_percentage:
                controller_devices.append(controller)
            
    env_sensors = []
    for env_device in env_devices:
        # For each device setup up multiple entities
        env_sensors.append(ikea_vindstyrka_temperature(env_device))
        env_sensors.append(ikea_vindstyrka_humidity(env_device))
        env_sensors.append(ikea_vindstyrka_pm25(env_device, WhichPM25.CURRENT))
        env_sensors.append(ikea_vindstyrka_pm25(env_device, WhichPM25.MAX))
        env_sensors.append(ikea_vindstyrka_pm25(env_device, WhichPM25.MIN))
        env_sensors.append(ikea_vindstyrka_voc_index(env_device))


    outlet_sensors = []
    if config[CONF_IP_ADDRESS] != "mock":
        hub_outlets: list[Outlet] = await hass.async_add_executor_job(hub.get_outlets)
        for outlet in hub_outlets:
            if outlet.attributes.model == "INSPELNING Smart plug":
                outlet_entity = ikea_outlet(hass, hub, outlet)
                outlet_sensors.extend([
                    ikea_outlet_energy_consumed(outlet_entity),
                    ikea_outlet_current_active_power(outlet_entity),
                    ikea_outlet_current_amps(outlet_entity),
                    ikea_outlet_current_voltage(outlet_entity),
                    ikea_outlet_total_energy_consumed_last_updated(outlet_entity),
                    ikea_outlet_time_of_last_energy_reset(outlet_entity)
                ])

    logger.debug("Found {} env devices to setup...".format(len(env_devices)))
    logger.debug("Found {} env entities to setup...".format(len(env_sensors)))
    logger.debug("Found {} controller devices to setup...".format(len(controller_devices)))
    logger.debug("Found {} outlet entities to setup...".format(len(outlet_sensors)))

    async_add_entities(env_sensors)
    async_add_entities(controller_devices)
    async_add_entities(outlet_sensors)

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

# SOMRIG Controllers act differently in the gateway Hub
# While its one device but two id's are sent back each
# representing the two buttons on the controler. The id is
# all same except _1 and _2 suffix. The serial number on the
# controllers is same.

CONTROLLER_BUTTON_MAP = { "SOMRIG shortcut button" : 2 }

class ikea_controller(ikea_base_device, SensorEntity):
    def __init__(self,hass:core.HomeAssistant, hub:Hub, json_data:Controller):
        logger.debug("ikea_controller ctor...")
        self._buttons = 1
        if json_data.attributes.model in CONTROLLER_BUTTON_MAP:
            self._buttons = CONTROLLER_BUTTON_MAP[json_data.attributes.model]
            logger.error(f"Set #buttons to {self._buttons} as controller model is : {json_data.attributes.model}")
        
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

    @property
    def device_class(self) -> str:
        return SensorDeviceClass.BATTERY

    @property
    def number_of_buttons(self) -> int:
        return self._buttons
    
    async def async_update(self):  
        pass

class ikea_outlet_energy_consumed(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(device, id_suffix="ENERGY_CONSUMED", name_suffix="Energy Consumed")
    
    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY

    @property
    def native_value(self):
        return round(self._device.total_energy_consumed, 2)

    @property
    def native_unit_of_measurement(self):
        return "kWh"
    
    @property
    def state_class(self) -> str:
        return "total_increasing"

class ikea_outlet_current_active_power(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(device, id_suffix="ACTIVE_POWER", name_suffix="Active Power")
    
    @property
    def device_class(self):
        return SensorDeviceClass.POWER

    @property
    def native_value(self):
        return round(self._device.current_active_power, 2)

    @property
    def native_unit_of_measurement(self):
        return "W"

class ikea_outlet_current_amps(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(device, id_suffix="CURRENT_AMPS", name_suffix="Current (Amps)")
    
    @property
    def device_class(self):
        return SensorDeviceClass.CURRENT

    @property
    def native_value(self):
        return round(self._device.current_amps, 2)

    @property
    def native_unit_of_measurement(self):
        return "A"

class ikea_outlet_current_voltage(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(device, id_suffix="CURRENT_VOLTAGE", name_suffix="Voltage")
    
    @property
    def device_class(self):
        return SensorDeviceClass.VOLTAGE

    @property
    def native_value(self):
        return round(self._device.current_voltage, 2)

    @property
    def native_unit_of_measurement(self):
        return "V"

class ikea_outlet_total_energy_consumed_last_updated(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(device, id_suffix="TOTAL_ENERGY_CONSUMED_LAST_UPDATED", name_suffix="Total Energy Consumed Last Updated")
    
    @property
    def device_class(self):
        return SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        return self._device.total_energy_consumed_last_updated

class ikea_outlet_time_of_last_energy_reset(ikea_base_device_sensor, SensorEntity):
    def __init__(self, device):
        super().__init__(device, id_suffix="TIME_OF_LAST_ENERGY_RESET", name_suffix="Time of Last Energy Reset")
    
    @property
    def device_class(self):
        return SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self):
        return self._device.time_of_last_energy_reset

import logging

from dirigera import Hub
from dirigera.devices.motion_sensor import MotionSensor
from dirigera.devices.open_close_sensor import OpenCloseSensor
from dirigera.devices.water_sensor import WaterSensor

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN

from .const import DOMAIN
from .mocks.ikea_motion_sensor_mock import ikea_motion_sensor_mock
from .mocks.ikea_open_close_mock import ikea_open_close_mock
from .common_classes import battery_percentage_sensor
from .common_classes import ikea_base_device, ikea_base_device_sensor

logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("Binary Sensor Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger.debug(config)

    # hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    hub = Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    lights = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":
        logger.warning("Setting up mock motion sensors")
        mock_motion_sensor1 = ikea_motion_sensor_mock()
        motion_sensors = [mock_motion_sensor1]

        logger.warning("Setting up mock open/close sensors")
        mock_open_close_sensor1 = ikea_open_close_mock()
        open_close_sensors = [mock_open_close_sensor1]

    else:

        hub_motion_sensors : list[MotionSensor] = await hass.async_add_executor_job(hub.get_motion_sensors)
        motion_sensor_devices : list[ikea_motion_sensor_device] = [ikea_motion_sensor_device(hass, hub, m) for m in hub_motion_sensors]

        motion_sensors = []
        for device in motion_sensor_devices:
            motion_sensors.append(ikea_motion_sensor(device))
            motion_sensors.append(battery_percentage_sensor(device))
    
        logger.debug("Found {} motion_sensor entities to setup...".format(len(motion_sensors)/2))
        async_add_entities(motion_sensors)
    
        if 1==2:
            hub_open_close_sensors : list[OpenCloseSensor] = await hass.async_add_executor_job(hub.get_open_close_sensors)
            open_close_devices : list[ikea_open_close_device] = [
                ikea_open_close_device(hass, hub, open_close_sensor)
                for open_close_sensor in hub_open_close_sensors
            ]

            open_close_sensors = []
            for device in open_close_devices:
                open_close_sensors.append(ikea_motion_sensor(device))
                open_close_sensors.append(battery_percentage_sensor(device))

            logger.debug("Found {} open close entities to setup...".format(len(open_close_sensors)/2))
            async_add_entities(open_close_sensors)

            hub_water_sensors : list[WaterSensor] = await hass.async_add_executor_job(hub.get_water_sensors)
            water_sensor_devices = [ ikea_water_sensor_device(hass, hub, hub_water_sensor) 
                                    for hub_water_sensor in hub_water_sensors
                                ]
            
            water_sensors = []
            for device in water_sensor_devices:
                water_sensors.append(battery_percentage_sensor(device))
                water_sensors.append(ikea_water_sensor(device))

            logger.debug(f"Found {len(hub_water_sensors)/2} water sensors to setup....")
            async_add_entities(water_sensors)

    logger.debug("Binary Sensor Complete async_setup_entry")

class ikea_motion_sensor_device(ikea_base_device):
    def __init__(self,hass, hub, json_data):
        logger.debug("ikea_motion_sensor_device ctor...")
        super().__init__(hass, hub, json_data, hub.get_motion_sensor_by_id)

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
        super().__init__(hub, hass, json_data, hub.get_open_close_by_id)

class ikea_open_close(ikea_base_device_sensor, BinarySensorEntity):
    def __init__(self, device: ikea_motion_sensor_device):
        logger.debug("ikea_motion_sensor ctor...")
        # No suffix or name prefix for backward compatibility
        super(ikea_base_device_sensor).__init__(device)

    @property
    def device_class(self) -> str:
        return BinarySensorDeviceClass.WINDOW

class ikea_water_sensor_device(ikea_base_device):
    def __init__(self, hass, hub, json_data):
        super().__init__(hass, hub, json_data, hub.get_water_sensor_by_id)

class ikea_water_sensor(ikea_base_device_sensor, BinarySensorEntity):
    def __init__(self, device : ikea_water_sensor_device):
        logger.debug("ikea_water_sensor ctor...")
        super().__init__(device)
    
    @property
    def is_on(self):
        # Note: the `is_detected` attribute is not present for Trådfri Motion Sensor E1745, only in the webhook events
        return self._device.water_leak_detected
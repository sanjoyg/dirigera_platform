import logging
from dirigera import Hub
from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .mocks.ikea_motion_sensor_mock import ikea_motion_sensor_mock
from .mocks.ikea_open_close_mock import ikea_open_close_mock
from .hub_event_listener import hub_event_listener
from .common_sensors import battery_percentage_sensor

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
        hub_motion_sensors = await hass.async_add_executor_job(hub.get_motion_sensors)
        motion_sensors = [
            ikea_motion_sensor(hub, motion_sensor)
            for motion_sensor in hub_motion_sensors
        ]

        hub_open_close_sensors = await hass.async_add_executor_job(
            hub.get_open_close_sensors
        )
        open_close_sensors = [
            ikea_open_close(hub, open_close_sensor)
            for open_close_sensor in hub_open_close_sensors
        ]

        hub_water_sensors = await hass.async_add_executor_job(hub.get_water_sensors)
        water_sensor_devices = [ ikea_water_sensor_device(hass, hub, hub_water_sensor) 
                                 for hub_water_sensor in hub_water_sensors
                               ]
        water_sensors = []
        for water_sensor_device in water_sensor_devices:
            water_sensors.append(battery_percentage_sensor(water_sensor_device))
            water_sensors.append(ikea_water_sensor(water_sensor_device))

    logger.debug("Found {} motion_sensor entities to setup...".format(len(motion_sensors)))
    async_add_entities(motion_sensors)
    
    logger.debug("Found {} open close entities to setup...".format(len(open_close_sensors)))
    async_add_entities(open_close_sensors)

    logger.debug(f"Found {len(hub_water_sensors)} water sensors to setup....")
    async_add_entities(water_sensors)

    logger.debug("Binary Sensor Complete async_setup_entry")

class ikea_motion_sensor(BinarySensorEntity):
    
    def __init__(self, hub, json_data):
        logger.debug("ikea_motion_sensor ctor...")
        self._hub = hub
        self._json_data = json_data
    
    @property
    def unique_id(self):
        return self._json_data.id

    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def device_info(self) -> DeviceInfo:
        # Register the device for updates
        hub_event_listener.register(self._json_data.id, self)

        return DeviceInfo(
            identifiers={("dirigera_platform", self._json_data.id)},
            name=self.name,
            manufacturer=self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model,
            sw_version=self._json_data.attributes.firmware_version,
        )

    @property
    def name(self):
        if self._json_data.attributes.custom_name is None or len(self._json_data.attributes.custom_name) == 0:
            return self.unique_id
        return self._json_data.attributes.custom_name

    @property
    def is_on(self):
        # Note: the `is_detected` attribute is not present for Trådfri Motion Sensor E1745, only in the webhook events
        return self._json_data.attributes.is_on or getattr(self._json_data.attributes, 'is_detected', False)

    async def async_update(self):
        logger.debug("motion sensor update...")
        try:
            self._json_data = await self.hass.async_add_executor_job(self._hub.get_motion_sensor_by_id, self._json_data.id)
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

class ikea_open_close(ikea_motion_sensor):
    def __init__(self, hub, json_data):
        logger.debug("ikea_open_close ctor...")
        self._hub = hub
        self._json_data = json_data

    @property
    def device_info(self) -> DeviceInfo:
        # Register the device for updates
        hub_event_listener.register(self._json_data.id, self)
        
        return DeviceInfo(
            identifiers={("dirigera_platform", self._json_data.id)},
            name=self.name,
            manufacturer=self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model,
            sw_version=self._json_data.attributes.firmware_version,
        )

    @property
    def device_class(self) -> str:
        return BinarySensorDeviceClass.WINDOW

    @property
    def name(self):
        if self._json_data.attributes.custom_name is None or len(self._json_data.attributes.custom_name) == 0:
            return self.unique_id
        return self._json_data.attributes.custom_name

    @property
    def is_on(self):
        return self._json_data.attributes.is_open

    async def async_update(self):
        logger.debug("open close sensor update...")
        try:
            self._json_data = await self.hass.async_add_executor_job(self._hub.get_open_close_by_id, self._json_data.id)
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

class ikea_water_sensor_device:
    def __init__(self, hass, hub, json_data) -> None:
        self._hass = hass 
        self._json_data = json_data
        self._updated_at = None
        self._hub = hub
        self._listeners = []

        # Register the device for updates
        hub_event_listener.register(self._json_data.id, self)

    def add_listener(self, entity : Entity) -> None:
        self._listeners.append(entity)

    async def async_update(self):
        try:
            logger.debug("water sensor update called...")
            self._json_data = await self._hass.async_add_executor_job(self._hub.get_water_sensor_by_id, self._json_data.id)
        except Exception as ex:
            logger.error(
                "error encountered running update on : {}".format(self.name)
            )
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    #Hack for faster update
    def async_schedule_update_ha_state(self, force_refresh:bool = False) ->None :
        logger.debug("water sensor update_ha_state")
        for listener in self._listeners:
            logger.debug("routing to update_ha_state")
            listener.async_schedule_update_ha_state(force_refresh)

    @property
    def water_leak_detected(self) -> bool: 
        return self._json_data.attributes.water_leak_detected

    @property
    def battery_percentage(self) -> int:
        return self._json_data.attributes.battery_percentage
    
    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def device_info(self) -> DeviceInfo:

        return DeviceInfo(
            identifiers={("dirigera_platform", self._json_data.id)},
            name=self.name,
            manufacturer=self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model,
            sw_version=self._json_data.attributes.firmware_version,
        )

    @property
    def name(self) -> str:
        if self._json_data.attributes.custom_name is None or len(self._json_data.attributes.custom_name) == 0:
            return self.unique_id
        return self._json_data.attributes.custom_name

    @property
    def unique_id(self):
        return f"{self._json_data.id}_WL01"

class ikea_water_sensor(BinarySensorEntity):
    def __init__(self, device : ikea_water_sensor_device):
        logger.debug("ikea_water_sensor ctor...")
        self._device = device
        self._device.add_listener(self)

    @property
    def unique_id(self):
        return self._device.unique_id

    @property
    def available(self):
        return self._device.available

    @property
    def device_info(self) -> DeviceInfo:
        return self._device.device_info

    @property
    def name(self):
        return f"{self._device.name} Water Leak Detected"

    @property
    def is_on(self):
        # Note: the `is_detected` attribute is not present for Trådfri Motion Sensor E1745, only in the webhook events
        return self._device.water_leak_detected
    
    async def async_update(self):
        logger.debug("water sensor entity update")
        await self._device.async_update()
import logging

import dirigera

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .dirigera_lib_patch import HubX
from .mocks.ikea_motion_sensor_mock import ikea_motion_sensor_mock
from .mocks.ikea_open_close_mock import ikea_open_close_mock
from .hub_event_listener import hub_event_listener

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
    hub = HubX(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

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

    logger.debug(
        "Found {} motion_sensor entities to setup...".format(len(motion_sensors))
    )
    async_add_entities(motion_sensors)
    logger.debug(
        "Found {} open close entities to setup...".format(len(open_close_sensors))
    )
    async_add_entities(open_close_sensors)

    logger.debug("Binary Sensor Complete async_setup_entry")


class ikea_motion_sensor(BinarySensorEntity):
    
    def __init__(self, hub, json_data):
        logger.debug("ikea_motion_sensor ctor...")
        self._hub = hub
        self._json_data = json_data

        self.user_detected_attr = False 
        if self._json_data.attributes.model.lower().startswith("vallhorn"):
            logger.debug("VALLHORN Motion sensor detected will use is_detected attribute..")
            self.user_detected_attr = True 

    @property
    def should_poll(self) -> bool:
        return False 
    
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
        if self.user_detected_attr:
            return self._json_data.attributes.is_detected
        return self._json_data.attributes.is_on

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

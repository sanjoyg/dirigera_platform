import datetime
from enum import Enum
import logging

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from ..const import DOMAIN

logger = logging.getLogger("custom_components.dirigera_platform")


class ikea_controller_mock(SensorEntity):
    counter = 0

    def __init__(self) -> None:
        logger.debug("ikea_controller_mock ctor")
        ikea_controller_mock.counter = ikea_controller_mock.counter + 1
        self._unique_id = "CT1907151129080101_" + str(ikea_controller_mock.counter)
        self._name = "Mock Controller " + str(ikea_controller_mock.counter)

    def update(self):
        logger.debug("update called on ikea_controller_mock")
        pass

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform", self._unique_id)},
            name=self._name,
            manufacturer="IKEA of Sweden",
            model="Mock Controler",
            sw_version="mock sw",
        )

    @property
    def name(self) -> str:
        logger.debug("name() called on ikea_controller_mock: {}".format(self._name))
        return self._name

    @property
    def unique_id(self):
        logger.debug(
            "unique_id() called on ikea_controller_mock : {}".format(self._unique_id)
        )
        return self._unique_id

    @property
    def available(self):
        logger.debug("available() called on ikea_controller_mock")
        return True

    @property
    def is_on(self):
        return True

    @property
    def device_class(self):
        logger.debug("device_class() called on ikea_controller_mock")
        return SensorDeviceClass.BATTERY

    @property
    def native_value(self):
        logger.debug("native_value() called on ikea_controller_mock")
        return 20

    @property
    def native_unit_of_measurement(self) -> str:
        return "%"

    async def async_will_remove_from_hass(self) -> None:
        ikea_controller_mock.counter = ikea_controller_mock.counter - 1

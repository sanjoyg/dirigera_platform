import datetime
import logging
import random

from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from ..const import DOMAIN
from ..sensor import ikea_vindstyrka_device

logger = logging.getLogger("custom_components.dirigera_platform")


class ikea_vindstyrka_device_mock(ikea_vindstyrka_device):
    counter = 0

    def __init__(self) -> None:
        logger.debug("ikea_vindstyrka_device_mock ctor")
        ikea_vindstyrka_device_mock.counter = ikea_vindstyrka_device_mock.counter + 1
        self._unique_id = "E1907151129080101_" + str(
            ikea_vindstyrka_device_mock.counter
        )
        self._name = "Mock Env Sensor " + str(ikea_vindstyrka_device_mock.counter)
        self._updated_at = None

    def update(self):
        if (
            self._updated_at is None
            or (datetime.datetime.now() - self._updated_at).total_seconds() > 30
        ):
            try:
                logger.debug("Updated environment sensor...")
                self._updated_at = datetime.datetime.now()
            except Exception as ex:
                logger.error("error encountered running update on : {}".format(self.name))
                logger.error(ex)
                raise HomeAssistantError(ex, DOMAIN, "hub_exception")
        else:
            logger.debug("Not updating environment sensor...")

    def get_current_temperature(self):
        return random.randint(-10, 50)

    def get_current_r_h(self):
        return random.randint(10, 90)

    def get_current_p_m25(self):
        return random.randint(50, 500)

    def get_max_measured_p_m25(self):
        return random.randint(202, 500)

    def get_min_measured_p_m25(self):
        return random.randint(50, 200)

    def get_voc_index(self):
        return random.randint(50, 500)

    @property
    def available(self):
        return True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform", self._unique_id)},
            name=self._name,
            manufacturer="IKEA of Sweden",
            model="Mock Env Sensor",
            sw_version="mock sw",
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    async def async_will_remove_from_hass(self) -> None:
        ikea_vindstyrka_device_mock.counter = ikea_vindstyrka_device_mock.counter - 1

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo

logger = logging.getLogger("custom_components.dirigera_platform")


class ikea_open_close_mock(BinarySensorEntity):
    counter = 0

    def __init__(self):
        ikea_open_close_mock.counter = ikea_open_close_mock.counter + 1

        self._manufacturer = "IKEA of Sweden"
        self._unique_id = "OC1907151129080101_" + str(ikea_open_close_mock.counter)
        self._model = "mock open/close sensor"
        self._sw_version = "mock sw"
        self._name = "mock"

        self._name = "Mock Open Close Sensor {}".format(ikea_open_close_mock.counter)
        self._is_on = False

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform", self._unique_id)},
            name=self._name,
            manufacturer=self._manufacturer,
            model=self._model,
            sw_version=self._sw_version,
            suggested_area="Living room",
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_on(self):
        return self._is_on

    def update(self):
        pass

    async def async_will_remove_from_hass(self) -> None:
        ikea_open_close_mock.counter = ikea_open_close_mock.counter - 1

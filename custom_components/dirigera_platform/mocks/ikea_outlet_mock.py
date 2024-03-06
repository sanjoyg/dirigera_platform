import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import DeviceInfo

logger = logging.getLogger("custom_components.dirigera_platform")


class ikea_outlet_mock(SwitchEntity):
    counter = 0

    def __init__(self, hub, hub_outlet):
        self._hub = hub
        self._hub_outlet = hub_outlet
        ikea_outlet_mock.counter = ikea_outlet_mock.counter + 1

        self._manufacturer = "IKEA of Sweden"
        self._unique_id = "O1907151129080101_" + str(ikea_outlet_mock.counter)
        self._model = "mock outlet"
        self._sw_version = "mock sw"
        self._name = "mock"

        self._name = "Mock Outlet {}".format(ikea_outlet_mock.counter)
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
        )

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_on(self):
        return self._is_on

    def turn_on(self):
        self._is_on = True

    def turn_off(self):
        self._is_on = False

    def update(self):
        pass

    async def async_will_remove_from_hass(self) -> None:
        ikea_outlet_mock.counter = ikea_outlet_mock.counter - 1

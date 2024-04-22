import logging

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.helpers.entity import DeviceInfo

logger = logging.getLogger("custom_components.dirigera_platform")


class ikea_blinds_mock(CoverEntity):
    counter = 0

    def __init__(self, hub, hub_blinds) -> None:
        logger.debug("IkeaBlinds mock ctor...")
        self._hub = hub
        ikea_blinds_mock.counter = ikea_blinds_mock.counter + 1

        self._manufacturer = "IKEA of Sweden"
        self._unique_id = "B1907151129080101_" + str(ikea_blinds_mock.counter)
        self._model = "mock blind"
        self._sw_version = "mock sw"
        self._name = "mock"

        self._name = "Mock Blind {}".format(ikea_blinds_mock.counter)
        self._supported_feature = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
        )
        self._is_on = False
        self._current_level = 100
        self._target_level = 100

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
            suggested_area="Bedroom",
        )

    @property
    def supported_features(self):
        logger.debug("blinds supported_features called")
        return self._supported_feature

    def update(self):
        logger.debug("mock update for {}...".format(self._name))
        pass

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_on(self):
        return self._is_on

    @property
    def device_class(self) -> str:
        return CoverDeviceClass.BLIND

    @property
    def current_cover_position(self):
        logger.debug("blinds current_cover_position called")
        logger.debug(
            "Current: {}, Target: {}".format(self._current_level, self._target_level)
        )
        return self._current_level

    @property
    def is_closed(self):
        logger.debug("blinds is_closed called")
        logger.debug(
            "Current: {}, Target: {}".format(self._current_level, self._target_level)
        )

        return self._current_level == 0

    @property
    def is_closing(self):
        logger.debug("blinds is_closing called")
        logger.debug(
            "Current: {}, Target: {}".format(self._current_level, self._target_level)
        )

        if self._current_level != 0 and self._target_level == 0:
            return True
        return False

    @property
    def is_opening(self):
        logger.debug("blinds is_opening called")
        logger.debug(
            "Current: {}, Target: {}".format(self._current_level, self._target_level)
        )

        if self._current_level != 100 and self._target_level == 100:
            return True
        return False

    def open_cover(self, **kwargs):
        logger.debug("blinds open_cover called")
        logger.debug(
            "Current: {}, Target: {}".format(self._current_level, self._target_level)
        )

        self._current_level = 100
        self._target_level = 100

    def close_cover(self, **kwargs):
        logger.debug("blinds close_cover called")
        logger.debug(
            "Current: {}, Target: {}".format(self._current_level, self._target_level)
        )

        self._current_level = 0
        self._target_level = 0

    def set_cover_position(self, **kwargs):
        logger.debug("blinds set_cover_position {}".format(kwargs))
        logger.debug(kwargs["position"])
        logger.debug(
            "Current: {}, Target: {}".format(self._current_level, self._target_level)
        )

        if "position" in kwargs:
            position = kwargs["position"]
            if position >= 0 and position <= 100:
                self._target_level = position
                self._current_level = position
                logger.debug(
                    "Now: Current: {}, Target: {}".format(
                        self._current_level, self._target_level
                    )
                )

    async def async_will_remove_from_hass(self) -> None:
        ikea_blinds_mock.counter = ikea_blinds_mock.counter - 1

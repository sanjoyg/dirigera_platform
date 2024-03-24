import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.helpers.entity import DeviceInfo

logger = logging.getLogger("custom_components.dirigera_platform")


class ikea_bulb_mock(LightEntity):
    counter = 0

    def __init__(self) -> None:
        logger.debug("ikea_bulb mock ctor...")
        ikea_bulb_mock.counter = ikea_bulb_mock.counter + 1

        self._manufacturer = "IKEA of Sweden"
        self._unique_id = "L1907151129080101_" + str(ikea_bulb_mock.counter)
        self._model = "mock bulb"
        self._sw_version = "mock sw"
        self._name = "mock"

        self._name = "Mock Light {}".format(ikea_bulb_mock.counter)
        self._supported_color_modes = [
            ColorMode.BRIGHTNESS,
            ColorMode.COLOR_TEMP,
            ColorMode.HS,
        ]

        if len(self._supported_color_modes) > 1:
            # If there are more color modes which means we have either temperature
            # or HueSaturation. then lets make sure BRIGHTNESS is not part of it
            # as per above documentation
            self._supported_color_modes.remove(ColorMode.BRIGHTNESS)
            
        if len(self._supported_color_modes) == 0:
            logger.debug("Color modes array is zero, setting to UNKNOWN")
            self._supported_color_modes = [ColorMode.UNKNOWN]
        else:
            if ColorMode.HS in self._supported_color_modes:
                self._color_mode = ColorMode.HS
            elif ColorMode.COLOR_TEMP in self._supported_color_modes:
                self._color_mode = ColorMode.COLOR_TEMP
            elif ColorMode.BRIGHTNESS in self._supported_color_modesor_modes:
                self._color_mode = ColorMode.BRIGHTNESS

        self._color_temp = 3000
        self._min_color_temp = 2202
        self._max_color_temp = 4000
        self._color_hue = 0.0
        self._color_saturation = 0.0
        self._brightness = 100
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

    def set_state(self):
        pass

    @property
    def name(self) -> str:
        return self._name

    @property
    def brightness(self):
        return int((self._brightness / 100) * 255)

    @property
    def max_color_temp_kelvin(self):
        return self._max_color_temp

    @property
    def min_color_temp_kelvin(self):
        return self._min_color_temp

    @property
    def color_temp_kevin(self):
        return self._color_temp

    @property
    def hs_color(self):
        return (self._color_hue, self._color_saturation)

    @property
    def is_on(self):
        return self._is_on

    @property
    def supported_color_modes(self):
        logger.debug("returning supported colors")
        return self._supported_color_modes

    @property
    def color_mode(self):
        logger.debug("Returning color mode")
        return self._color_mode 
    
    def update(self):
        logger.debug("mock update for {}...".format(self._name))
        pass

    def turn_on(self, **kwargs):
        logger.debug("turn_on...")
        logger.debug(kwargs)

        logger.debug("Request to turn on...")
        self._is_on = True
        logger.debug(kwargs)
        if ATTR_BRIGHTNESS in kwargs:
            # brightness requested
            logger.debug("Request to set brightness...")
            brightness = int(kwargs[ATTR_BRIGHTNESS])
            logger.debug("Set brightness : {}".format(brightness))
            self._brightness = int((brightness / 255) * 100)

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            # color temp requested
            # If request is white then brightness is passed
            logger.debug("Request to set color temp...")
            ct = kwargs[ATTR_COLOR_TEMP_KELVIN]
            logger.debug("Set CT : {}".format(ct))
            self._color_temp = ct

        if ATTR_HS_COLOR in kwargs:
            logger.debug("Request to set color HS")
            hs_tuple = kwargs[ATTR_HS_COLOR]
            self._color_hue = hs_tuple[0]
            self._color_saturation = hs_tuple[1]

    def turn_off(self, **kwargs):
        logger.debug("turn_off...")
        self._is_on = False

    async def async_will_remove_from_hass(self) -> None:
        ikea_bulb_mock.counter = ikea_bulb_mock.counter - 1

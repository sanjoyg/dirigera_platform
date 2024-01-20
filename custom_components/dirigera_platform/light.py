from homeassistant import config_entries, core
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity
)

import dirigera
from .const import DOMAIN
from .mocks.ikea_bulb_mock import ikea_bulb_mock

import logging
logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("LIGHT async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger.debug(config)

    hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    lights = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":   
        logger.warning("Setting up mock bulbs")
        mock_bulb1 = ikea_bulb_mock(hub,"sanjoy")
        mock_bulb2 = ikea_bulb_mock(hub,"ekta")
        lights = [mock_bulb1,mock_bulb2] 
    else:
        hub_lights = await hass.async_add_executor_job(hub.get_lights)
        lights = [ikea_bulb(hub, light) for light in hub_lights]

    logger.debug("Found {} light entities to setup...".format(len(lights)))
    async_add_entities(lights)

class ikea_bulb(LightEntity):
    def __init__(self, hub, hub_light) -> None:
        logger.debug("ikea_bulb ctor...")
        self._hub = hub 
        self._hub_light = hub_light
        self.set_state()

    def set_state(self):
        # Set Color capabilities
        color_modes = []
        can_receive = self._hub_light.capabilities.can_receive
        logger.debug("Got can_receive in state")
        logger.debug(can_receive)
        for cap in can_receive:
            if cap == "lightLevel":
                color_modes.append(ColorMode.BRIGHTNESS)
            elif cap == "colorTemperature":
                color_modes.append(ColorMode.COLOR_TEMP)
            elif cap == "colorHue" or cap == "colorSaturation":
                color_modes.append(ColorMode.HS)
        
        self._supported_color_modes = color_modes
        logger.debug("supported color mode set to ")
        logger.debug(self._supported_color_modes)

    @property
    def name(self) -> str:
        return self._hub_light.attributes.custom_name

    @property
    def brightness(self):
        scaled = int((self._hub_light.attributes.light_level/100)*255)
        logger.debug("scaled brightness : {}".format(scaled))

    @property
    def max_color_temp_kelvin(self):
        return self._hub_light.attributes.color_temperature_min
    
    @property
    def min_color_temp_kelvin(self):
        return self._hub_light.attributes.color_temperature_max
    
    @property
    def color_temp_kelvin(self):
        return self._hub_light.attributes.color_temperature

    @property
    def hs_color(self):
        return (self._hub_light.attributes.hue, self._hub_light.attributes.saturation)
    
    @property
    def available(self):
        return self._hub_light.is_reachable
    
    @property
    def is_on(self):
        return self._hub_light.attributes.is_on

    @property
    def supported_color_modes(self):
        return self._supported_color_modes

    def update(self):
        logger.debug("update...")
        try:
            self._hub_light = self._hub.get_light_by_id(self._hub_light.id)
            self.set_state()
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")

    def turn_on(self, **kwargs):
        logger.debug("light turn_on...")
        logger.debug(kwargs)

        try:
            self._hub_light.set_light(True)

            if ATTR_BRIGHTNESS in kwargs:
                # brightness requested
                logger.debug("Request to set brightness...")
                brightness = int(kwargs[ATTR_BRIGHTNESS]) 
                logger.debug("Set brightness : {}".format(brightness))
                logger.debug("scaled brightness : {}".format(int((brightness/255)*100)))
                self._hub_light.set_light_level(int((brightness/255)*100))

            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                # color temp requested
                # If request is white then brightness is passed
                logger.debug("Request to set color temp...")
                ct = kwargs[ATTR_COLOR_TEMP_KELVIN]
                logger.debug("Set CT : {}".format(ct))
                self._hub_light.set_color_temperature(ct)

            if ATTR_HS_COLOR in kwargs:
                logger.debug("Request to set color HS")
                hs_tuple = kwargs[ATTR_HS_COLOR]
                self._hue = hs_tuple[0]
                self._saturation = hs_tuple[1]
                self._hub_light.set_color_temperature(self._hue, self._saturation)

        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")

    def turn_off(self, **kwargs):
        logger.debug("light turn_off...")
        try:
            self._hub_light.set_light(False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
import logging
import dirigera

from dirigera import Hub
from homeassistant import config_entries, core
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_HIDE_DEVICE_SET_BULBS
from .mocks.ikea_bulb_mock import ikea_bulb_mock
from .hub_event_listener import hub_event_listener

logger = logging.getLogger("custom_components.dirigera_platform")


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("LIGHT Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger.debug(config)

    # hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    hub = Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    #Backward compatibility
    hide_device_set_bulbs = True
    if CONF_HIDE_DEVICE_SET_BULBS in config:
        hide_device_set_bulbs = config[CONF_HIDE_DEVICE_SET_BULBS]

    logger.debug(f"found setting hide_device_set_bulbs : {hide_device_set_bulbs}")
    lights = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":
        logger.warning("Setting up mock bulbs")
        mock_bulb1 = ikea_bulb_mock()
        lights = [mock_bulb1]
    else:
        hub_lights = await hass.async_add_executor_job(hub.get_lights)
        all_lights = [ikea_bulb(hub, light) for light in hub_lights]
        logger.debug("Found {} total of all light entities to setup...".format(len(all_lights)))
        
        device_sets  = {}
        lights = []
        for light in all_lights:
            if len(light._json_data.device_set) > 0:
                for one_set in light._json_data.device_set:
                    id = one_set['id']
                    name = one_set['name']

                    target_device_set = None 
                    if id not in device_sets:
                        logger.debug(f"Found new device set {name}")
                        device_sets[id] = device_set_model(id, name)
                    
                    target_device_set = device_sets[id]
                    target_device_set.add_light(light)

                    if not hide_device_set_bulbs:
                        lights.append(light)
            else:
                lights.append(light)

        logger.debug(f"Found {len(device_sets.keys())} device_sets")
        logger.debug(f"Found {len(lights)} lights to setup...")
        async_add_entities([ikea_bulb_device_set(hub, device_sets[key]) for key in device_sets])

    async_add_entities(lights)
    logger.debug("LIGHT Complete async_setup_entry")

class device_set_model:
    def __init__(self, id, name):
        logger.debug(f"device_set ctor {id} : {name}")
        self._lights = []
        self._name = name 
        self._id = id 
        
    @property
    def id(self):
        return self._id 
    
    @property
    def name(self):
        return self._name 
    
    def get_lights(self) -> list:
        return self._lights
    
    def add_light(self, bulb):
        logger.debug(f"Adding {bulb.name} to device_set : {self.name}")
        self._lights.append(bulb)

class ikea_bulb(LightEntity):
    
    def __init__(self, hub, json_data) -> None:
        logger.debug("ikea_bulb ctor...")
        self._hub = hub
        self._json_data = json_data
        self.set_state()

    def set_state(self):
        # Set Color capabilities
        color_modes = []
        can_receive = self._json_data.capabilities.can_receive
        logger.debug("Got can_receive in state")
        logger.debug(can_receive)
        self._color_mode = ColorMode.ONOFF
        for cap in can_receive:
            if cap == "lightLevel":
                color_modes.append(ColorMode.BRIGHTNESS)
            elif cap == "colorTemperature":
                color_modes.append(ColorMode.COLOR_TEMP)
            elif cap == "colorHue" or cap == "colorSaturation":
                color_modes.append(ColorMode.HS)

        # Based on documentation here
        # https://developers.home-assistant.io/docs/core/entity/light#color-modes
        if len(color_modes) > 1:
            # If there are more color modes which means we have either temperature
            # or HueSaturation. then lets make sure BRIGHTNESS is not part of it
            # as per above documentation
            color_modes.remove(ColorMode.BRIGHTNESS)

        if len(color_modes) == 0:
            logger.debug("Color modes array is zero, setting to UNKNOWN")
            self._supported_color_modes = [ColorMode.ONOFF]
        else:
            self._supported_color_modes = color_modes
            if ColorMode.HS in self._supported_color_modes:
                self._color_mode = ColorMode.HS
            elif ColorMode.COLOR_TEMP in self._supported_color_modes:
                self._color_mode = ColorMode.COLOR_TEMP
            elif ColorMode.BRIGHTNESS in self._supported_color_modes:
                self._color_mode = ColorMode.BRIGHTNESS

        logger.debug("supported color mode set to:")
        logger.debug(self._supported_color_modes)
        logger.debug("color mode set to:")
        logger.debug(self._color_mode)

    @property
    def unique_id(self):
        logger.debug("unique id called...")
        return self._json_data.id

    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def device_info(self) -> DeviceInfo:
        logger.debug("device info called...")

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
    def brightness(self):
        scaled = int((self._json_data.attributes.light_level / 100) * 255)
        return scaled

    @property
    def max_color_temp_kelvin(self):
        return self._json_data.attributes.color_temperature_min

    @property
    def min_color_temp_kelvin(self):
        return self._json_data.attributes.color_temperature_max

    @property
    def color_temp_kelvin(self):
        return self._json_data.attributes.color_temperature

    @property
    def hs_color(self):
        return (
            self._json_data.attributes.color_hue,
            self._json_data.attributes.color_saturation * 100,
        )

    @property
    def is_on(self):
        return self._json_data.attributes.is_on

    @property
    def supported_color_modes(self):
        return self._supported_color_modes

    @property
    def color_mode(self):
        return self._color_mode

    # Introduced this for update call from device_set       
    def sync_update(self):
        try:
            self._json_data = self._hub.get_light_by_id(self._json_data.id)
            self.set_state()
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")
        
    async def async_update(self):
        try:
            self._json_data = await self.hass.async_add_executor_job(self._hub.get_light_by_id, self._json_data.id)
            self.set_state()
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")
        
    async def async_turn_on(self, **kwargs):
        logger.debug("light turn_on...")
        logger.debug(kwargs)

        try:
            await self.hass.async_add_executor_job(self._json_data.set_light,True)

            if ATTR_BRIGHTNESS in kwargs:
                # brightness requested
                logger.debug("Request to set brightness...")
                brightness = int(kwargs[ATTR_BRIGHTNESS])
                logger.debug("Set brightness : {}".format(brightness))
                logger.debug(
                    "scaled brightness : {}".format(int((brightness / 255) * 100))
                )
                await self.hass.async_add_executor_job(self._json_data.set_light_level,int((brightness / 255) * 100))

            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                # color temp requested
                # If request is white then brightness is passed
                logger.debug("Request to set color temp...")
                ct = kwargs[ATTR_COLOR_TEMP_KELVIN]
                logger.debug("Set CT : {}".format(ct))
                await self.hass.async_add_executor_job(self._json_data.set_color_temperature,ct)

            if ATTR_HS_COLOR in kwargs:
                logger.debug("Request to set color HS")
                hs_tuple = kwargs[ATTR_HS_COLOR]
                self._color_hue = hs_tuple[0]
                self._color_saturation = hs_tuple[1] / 100
                # Saturation is 0 - 1 at IKEA
               
                await self.hass.async_add_executor_job(self._json_data.set_light_color,self._color_hue, self._color_saturation)

        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_turn_off(self, **kwargs):
        logger.debug("light turn_off...")
        try:
            await self.hass.async_add_executor_job(self._json_data.set_light,False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

# IKEA Device Set - Works wierdly
# There is a post available to set the state but the GET for state
# is not available, it would need to be derived from whichever is bulb/light
# is available

class ikea_bulb_device_set(LightEntity):
    
    def __init__(self, hub, device_set: device_set_model) -> None:
        logger.debug("ikea_bulb device_set ctor...")
        self._hub = hub
        self._device_set = device_set
        self._patch_url = f"/devices/set/{device_set.id}?deviceType=light"    
         
    @property
    def unique_id(self):
        return self._device_set.id

    @property
    def available(self):
        for light in self._device_set.get_lights():
            if light.available:
                return True 
        return False 

    @property
    def device_info(self) -> DeviceInfo:
        logger.debug("device info device_set called...")

        # Register the device for updates
        hub_event_listener.register(self.unique_id, self)

        # Also register the associated bulbs id with self, 
        # cause they are never visible to HASS
        for light in self._device_set.get_lights():
            hub_event_listener.register(light.unique_id, [self, light])

        return DeviceInfo(
            identifiers={("dirigera_platform", self._device_set.id)},
            name=self._device_set.name ,
            manufacturer="IKEA",
            model="Device Set",
            sw_version="1.0",
        )

    @property
    def name(self):
        return self._device_set.name 
    
    # Help function to return attribute name of first available light.
    # If none is available then return of the first
    def  get_attribute_value(self, attr_name : str):
        for light in self._device_set.get_lights():
            if not light.available:
                continue 
            return getattr(light,attr_name)
        
        # We are here means no light is available
        if len(self._device_set.get_lights()) > 0:
            return getattr(self._device_set.get_lights()[0], attr_name)
        logger.error("error, device set requested for {attr_name} while no lights are associated with it")
     

    @property
    def brightness(self):
        return self.get_attribute_value("brightness")

    @property
    def max_color_temp_kelvin(self):
        return self.get_attribute_value("max_color_temp_kelvin")

    @property
    def min_color_temp_kelvin(self):
        return self.get_attribute_value("min_color_temp_kelvin")

    @property
    def color_temp_kelvin(self):
        return self.get_attribute_value("color_temp_kelvin")

    @property
    def hs_color(self):
        return self.get_attribute_value("hs_color")

    @property
    def is_on(self):
        return self.get_attribute_value("is_on")

    @property
    def supported_color_modes(self):
        return self.get_attribute_value("supported_color_modes")

    @property
    def color_mode(self):
        return self.get_attribute_value("color_mode")
            
    async def async_update(self):
        try:
            for light in self._device_set.get_lights():
                await self.hass.async_add_executor_job(light.sync_update)
        except Exception as ex:
            logger.error("error encountered running update on device_set : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    def patch_command(self, key_val : dict):
        data = [{"attributes" : key_val}]
        try:
            self._hub.patch(self._patch_url, data=data)
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_turn_on(self, **kwargs):
        logger.debug("light device_set turn_on...")
        logger.debug(kwargs)

        try:
            await self.hass.async_add_executor_job(self.patch_command,{"isOn": True})

            if ATTR_BRIGHTNESS in kwargs:
                # brightness requested
                logger.debug("Request to device_set set brightness...")
                brightness = int(kwargs[ATTR_BRIGHTNESS])
                logger.debug("Set brightness : {}".format(brightness))
                logger.debug(
                    "scaled brightness : {}".format(int((brightness / 255) * 100))
                )
                await self.hass.async_add_executor_job(self.patch_command, {"lightLevel" : int((brightness / 255) * 100)})

            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                # color temp requested
                # If request is white then brightness is passed
                logger.debug("Request to device_set set color temp...")
                ct = kwargs[ATTR_COLOR_TEMP_KELVIN]
                logger.debug("Set CT : {}".format(ct))
                await self.hass.async_add_executor_job(self.patch_command, {"colorTemperature" : ct})

            if ATTR_HS_COLOR in kwargs:
                logger.debug("Request to set color HS device_set")
                hs_tuple = kwargs[ATTR_HS_COLOR]
                self._color_hue = hs_tuple[0]
                self._color_saturation = hs_tuple[1] / 100
                # Saturation is 0 - 1 at IKEA
               
                await self.hass.async_add_executor_job(self.patch_command,{ "colorHue" : self._color_hue, "colorSaturation" : self._color_saturation})

        except Exception as ex:
            logger.error("error encountered turning on device_set : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_turn_off(self, **kwargs):
        logger.debug("light device_set turn_off...")
        try:
            await self.hass.async_add_executor_job(self.patch_command, {"isOn": False})
        except Exception as ex:
            logger.error("error encountered turning off device_set : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

import logging
from typing import Optional

from dirigera import Hub
from dirigera.devices.device import Room
from dirigera.devices.light import Light

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

from .const import DOMAIN, CONF_HIDE_DEVICE_SET_BULBS, PLATFORM
from .hub_event_listener import hub_event_listener, registry_entry

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

    all_lights = hass.data[DOMAIN][PLATFORM].lights 
    logger.debug("Found {} total of all light entities to setup...".format(len(all_lights)))
        
    device_sets  = {}
    lights = []
    for light in all_lights:
        if len(light._json_data.device_set) > 0:
            for one_set in light._json_data.device_set:
                id = one_set['id']
                name = one_set['name']
                # Use the room of the first light encountered in the set as the 'suggested area' for HA
                suggested_room = light._json_data.room

                target_device_set = None 
                
                if id not in device_sets:
                    logger.debug(f"Found new device set {name}")
                    device_sets[id] = device_set_model(id, name, suggested_room)
                
                target_device_set = device_sets[id]
                target_device_set.add_light(light)
                
                #if not hide_device_set_bulbs:
                lights.append(light)
        else:
            lights.append(light)

    logger.debug(f"Found {len(device_sets.keys())} device_sets")
    logger.debug(f"Found {len(lights)} lights to setup...")
    async_add_entities([ikea_bulb_device_set(hub, device_sets[key], device_sets[key].get_lights()[0] ) for key in device_sets])

    async_add_entities(lights)
    logger.debug("LIGHT Complete async_setup_entry")

class device_set_model:
    def __init__(self, id, name, suggested_room: Optional[Room]):
        logger.debug(f"device_set ctor {id} : {name}")
        self._lights = []
        self._name = name 
        self._id = id
        self._suggested_room = suggested_room
        
    @property
    def id(self):
        return self._id 
    
    @property
    def name(self):
        return self._name

    @property
    def suggested_room(self) -> Optional[Room]:
        return self._suggested_room
    
    def get_lights(self) -> list:
        return self._lights
    
    def add_light(self, bulb):
        logger.debug(f"Adding {bulb.name} to device_set : {self.name}")
        self._lights.append(bulb)

class ikea_bulb(LightEntity):
    
    def __init__(self, hub, json_data : Light) -> None:
        logger.debug("ikea_bulb ctor...")
        self._hub = hub
        self._json_data = json_data
        self._ignore_update = False 

        # Register the device for updates
        hub_event_listener.register(self._json_data.id, registry_entry(self))

        self.set_state()

    # When changing brightness a random update is sent by hub with brightness level before
    # the actual value is sent. So this is a hack to ignore that random update
    @property
    def should_ignore_update(self):
        return self._ignore_update
    
    def reset_ignore_update(self):
        self._ignore_update = False 

    def set_state(self):
        # Set Color capabilities
        logger.debug("Set State of bulb..")
        color_modes = []
        can_receive = self._json_data.capabilities.can_receive
        #logger.debug("Got can_receive in state")
        #logger.debug(can_receive)
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

        #logger.debug("supported color mode set to:")
        #logger.debug(self._supported_color_modes)
        #logger.debug("color mode set to:")
        #logger.debug(self._color_mode)

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

        return DeviceInfo(
            identifiers={("dirigera_platform", self._json_data.id)},
            name=self.name,
            manufacturer=self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model,
            sw_version=self._json_data.attributes.firmware_version,
            suggested_area=self._json_data.room.name if self._json_data.room is not None else None,
        )

    @property
    def name(self):  
        if self._json_data.attributes.custom_name is None or len(self._json_data.attributes.custom_name) == 0:
            return self.unique_id
        return self._json_data.attributes.custom_name
    
    @property
    def brightness(self):
        # This is called by HASS so should be in the range
        # of 0-100
        scaled = int((self.light_level/ 100) * 255)
        return scaled

    @property
    def light_level(self):
        # This is the state of the HUB so in 1-255 range
        return self._json_data.attributes.light_level 
    
    @light_level.setter
    def light_level(self, value):
        scaled = int((value/255)*100)
        if scaled < 1:
            scaled = 1
        elif scaled > 100:
            scaled = 100
        self._json_data.attributes.light_level = scaled

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
    def color_temperature(self):
        return self._json_data.attributes.color_temperature
    
    @color_temperature.setter
    def color_temperature(self, value):
        self._json_data.attributes.color_temperature = value 
    
    @property
    def hs_color(self):
        return ( self.color_hue, self.color_saturation * 100)

    @property
    def color_hue(self):
        return self._json_data.attributes.color_hue 
    
    @color_hue.setter
    def color_hue(self, value) :
        self.json_data.attributes.color_hue = value 
    
    @property
    def color_saturation(self):
        return self._json_data.attributes.color_saturation
    
    @color_saturation.setter
    def color_saturation(self, value):
        self._json_data.attributes.color_saturation = value 
    
    @property
    def is_on(self):
        return self._json_data.attributes.is_on

    @property
    def supported_color_modes(self):
        return self._supported_color_modes

    @property
    def color_mode(self):
        return self._color_mode
    
    @color_mode.setter
    def color_mode(self, value):
        self._color_mode = value 

    async def async_update(self):
        try:
            logger.debug("async update called on bulb..")
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
            # Probably change
            self.reset_ignore_update()
            await self.hass.async_add_executor_job(self._json_data.set_light,True)

            if ATTR_BRIGHTNESS in kwargs:
                # brightness requested
                # The setter will move the HASS value of 0-100 to 1-255
                self.light_level = int(kwargs[ATTR_BRIGHTNESS])
                logger.debug("scaled brightness : {}".format(self.light_level))
                # update
                await self.hass.async_add_executor_job(self._json_data.set_light_level,self.light_level)
                self._ignore_update = True 

            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                # color temp requested
                # If request is white then brightness is passed
                logger.debug("Request to set color temp...")
                ct = kwargs[ATTR_COLOR_TEMP_KELVIN]
                logger.debug("Set CT : {}".format(ct))
                await self.hass.async_add_executor_job(self._json_data.set_color_temperature,ct)
                self._ignore_update = True 

            if ATTR_HS_COLOR in kwargs:
                logger.debug("Request to set color HS")
                hs_tuple = kwargs[ATTR_HS_COLOR]
                self._color_hue = hs_tuple[0]
                self._color_saturation = hs_tuple[1] / 100
                # Saturation is 0 - 1 at IKEA
               
                await self.hass.async_add_executor_job(self._json_data.set_light_color,self._color_hue, self._color_saturation)
                self._ignore_update = True 
            self.async_schedule_update_ha_state(False)
        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_turn_off(self, **kwargs):
        logger.debug("light turn_off...")
        try:
            self.reset_ignore_update()
            await self.hass.async_add_executor_job(self._json_data.set_light,False)
            self.async_schedule_update_ha_state(False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

# IKEA Device Set - Works wierdly
# There is a post available to set the state but the GET for state
# is not available, it would need to be derived from whichever is bulb/light
# is available. Also the way the app behaves is replicated. The first bulb
# in the set is what the state of the group is thus, that is what we also 
# replicate

class ikea_bulb_device_set(LightEntity):
    def __init__(self, hub, device_set: device_set_model, first_bulb: ikea_bulb) -> None:
        logger.debug("ikea_bulb device_set ctor...")
        logger.debug(f"Setting up device_set {device_set.id} with first bulb {first_bulb.unique_id}")
        self._hub = hub
        self._controller = first_bulb
        self._device_set = device_set
        self._patch_url = f"/devices/set/{device_set.id}?deviceType=light"    

        # Update cascade entity
        registry_entry_of_bulb = hub_event_listener.get_registry_entry(first_bulb.unique_id)
        registry_entry_of_bulb.cascade_entity = self

    @property
    def should_poll(self):
        return False 
    
    @property
    def unique_id(self):
        return self._device_set.id

    @property
    def available(self):
        return self._controller.available

    @property
    def device_info(self) -> DeviceInfo:

        # Register the device for updates
        hub_event_listener.register(self.unique_id, self)
        
        return DeviceInfo(
            identifiers={("dirigera_platform", self._device_set.id)},
            name=self._device_set.name ,
            manufacturer="IKEA",
            model="Device Set",
            sw_version="1.0",
            suggested_area=self._device_set.suggested_room.name if self._device_set.suggested_room is not None else None,
        )

    @property
    def name(self):
        return self._device_set.name 
    
    @property
    def brightness(self):
        return self._controller.brightness

    @property
    def max_color_temp_kelvin(self):
        return self._controller.max_color_temp_kelvin

    @property
    def min_color_temp_kelvin(self):
        return self._controller.min_color_temp_kelvin
    
    @property
    def color_temp_kelvin(self):
        return self._controller.color_temp_kelvin

    @property
    def hs_color(self):
        return self._controller.hs_color

    @property
    def is_on(self):
        return self._controller.is_on

    @property
    def supported_color_modes(self):
        return self._controller.supported_color_modes

    @property
    def color_mode(self):
        return self._controller.color_mode

    async def async_update(self):
        try:
            logger.debug("Update of device_set....")
            #for light in self._device_set.get_lights():
            #    await light.async_update()

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

    # As indicated the turn on / brightness / color etc can be set by a patch command
    # the corresponding get doesnt work 
    async def async_turn_on(self, **kwargs):
        logger.debug("light device_set turn_on...")
        logger.debug(kwargs)

        try:
            self._controller.reset_ignore_update()
            await self.hass.async_add_executor_job(self.patch_command,{"isOn": True})

            if ATTR_BRIGHTNESS in kwargs:
                # brightness requested
                # the brightness sent by HASS will be in the range of 0-100 which has to be scaled
                # to 1-255

                logger.debug("Request to device_set set brightness...")
                level = int(kwargs[ATTR_BRIGHTNESS])

                # This is in the 1-100 level so scale it 
                logger.debug("Set brightness : {}".format(level))
                logger.debug("Set scaled brightness : {}".format(int((level / 255) * 100)))
                await self.hass.async_add_executor_job(self.patch_command, {"lightLevel" : int((level / 255) * 100)})
                self._controller._ignore_update = True 

            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                # color temp requested
                # If request is white then brightness is passed
                logger.debug("Request to device_set set color temp...")
                ct = kwargs[ATTR_COLOR_TEMP_KELVIN]
                logger.debug("Set CT : {}".format(ct))
                await self.hass.async_add_executor_job(self.patch_command, {"colorTemperature" : ct})
                self._controller._ignore_update = True 

            if ATTR_HS_COLOR in kwargs:
                logger.debug("Request to set color HS device_set")
                hs_tuple = kwargs[ATTR_HS_COLOR]
                self._color_hue = hs_tuple[0]
                self._color_saturation = hs_tuple[1] / 100
                # Saturation is 0 - 1 at IKEA
                self._controller._ignore_update = True 
                
                await self.hass.async_add_executor_job(self.patch_command,{ "colorHue" : self._color_hue, "colorSaturation" : self._color_saturation})

        except Exception as ex:
            logger.error("error encountered turning on device_set : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_turn_off(self, **kwargs):
        self._controller.reset_ignore_update()
        logger.debug("light device_set turn_off...")
        try:
            await self.hass.async_add_executor_job(self.patch_command, {"isOn": False})
        except Exception as ex:
            logger.error("error encountered turning off device_set : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")
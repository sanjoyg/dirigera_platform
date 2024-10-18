import logging 
from enum import Enum

from .dirigera_lib_patch import HubX
from .scene import ikea_scene
from .light import ikea_bulb
from .base_classes import (
    ikea_blinds_device,
    ikea_starkvind_air_purifier_device,
    ikea_outlet_device,
    ikea_vindstyrka_device, 
    ikea_controller_device,
    ikea_open_close_device, 
    ikea_motion_sensor_device, 
    ikea_water_sensor_device    
)

from dirigera.devices.scene import Trigger, TriggerDetails, EndTriggerEvent

logger = logging.getLogger("custom_components.dirigera_platform")

class HubDeviceType(Enum):
    EMPTY_SCENE         = "empty_scene"
    SCENE               = "scene"
    LIGHT               = "light"
    BLIND               = "blinds"
    AIR_PURIFIER        = "air_purifier"
    OUTLET              = "outlet"
    ENVIRONMENT_SENSOR  = "environment_sensor"
    CONTROLLER          = "controller"
    OPEN_CLOSE_SENSOR   = "open_close"
    MOTION_SENSOR       = "motion_sensor"
    WATER_SENSOR        = "water_sensor"

class ikea_gateway:
    def __init__(self):
        Trigger.update_forward_refs()
        TriggerDetails.update_forward_refs()
        EndTriggerEvent.update_forward_refs()
        
        logger.debug("dirigera_platform init...")
        self.devices = {}

    async def make_devices(self, hass, ip, token):
        hub: HubX = HubX(token, ip)
        
        #Scenes
        scenes = await hass.async_add_executor_job(hub.get_scenes)
        logger.debug(f"Found {len(scenes)} scenes...")
        empty_scenes = []
        non_empty_scenes = []
        for scene in scenes:
            if scene.name.startswith("dirigera_integration_empty_scene_"):
                empty_scenes.append(ikea_scene(hub,scene))
            else:
                non_empty_scenes.append(ikea_scene(hub,scene))

        self.devices[HubDeviceType.EMPTY_SCENE] = empty_scenes        
        self.devices[HubDeviceType.SCENE] = non_empty_scenes

        #Light
        lights = await hass.async_add_executor_job(hub.get_lights)
        logger.debug(f"Found {len(lights)} total of all light devices to setup...")
        self.devices[HubDeviceType.LIGHT] = [ikea_bulb(hub, light) for light in lights]
        
        #Cover
        blinds = await hass.async_add_executor_job(hub.get_blinds)
        logger.debug(f"Found {len(lights)} total of all blinds devices to setup...")
        self.devices[HubDeviceType.BLIND] = [ikea_blinds_device(hass, hub, b) for b in blinds]
        
        #Air Purifier
        air_purifiers = await hass.async_add_executor_job(hub.get_air_purifiers)
        logger.debug(f"Found {len(air_purifiers)} total of all air purifiers devices to setup...")
        self.devices[HubDeviceType.AIR_PURIFIER] = [ikea_starkvind_air_purifier_device(hass, hub, a) for a in air_purifiers]

        #Outlets
        outlets = await hass.async_add_executor_job(hub.get_outlets)
        logger.debug(f"Found {len(outlets)} total of all outlets devices to setup...")
        self.devices[HubDeviceType.OUTLET] = [ ikea_outlet_device(hass, hub, x) for x in outlets ]
        
        #Environment Sensor
        environment_sensors = await hass.async_add_executor_job(hub.get_environment_sensors)
        logger.debug(f"Found {len(environment_sensors)} total of all environment devices entities to setup...")
        self.devices[HubDeviceType.ENVIRONMENT_SENSOR] = [ikea_vindstyrka_device(hass, hub, env_device) for env_device in environment_sensors]

        #Controllers
        controllers = await hass.async_add_executor_job(hub.get_controllers)
        logger.debug(f"Found {len(controllers)} total of all controllers devices to setup...")
        self.devices[HubDeviceType.CONTROLLER] = [ikea_controller_device(hass, hub, x) for x in controllers]
        
        #Open Close Sensors
        open_close_sensors = await hass.async_add_executor_job(hub.get_open_close_sensors)
        logger.debug(f"Found {len(open_close_sensors)} total of all open_close devices to setup...")
        self.devices[HubDeviceType.OPEN_CLOSE_SENSOR] = [ikea_open_close_device(hass, hub, x) for x in open_close_sensors]
        
        #Motion Sensors
        motion_sensors = await hass.async_add_executor_job(hub.get_motion_sensors)
        logger.debug(f"Found {len(motion_sensors)} total of all motion_sensors devices to setup...")
        self.devices[HubDeviceType.MOTION_SENSOR] = [ikea_motion_sensor_device(hass, hub, x) for x in motion_sensors]
        
        #Water Sensors
        water_sensors = await hass.async_add_executor_job(hub.get_water_sensors)
        logger.debug(f"Found {len(water_sensors)} total of all water_sensors devices to setup...")
        self.devices[HubDeviceType.WATER_SENSOR] = [ikea_water_sensor_device(hass, hub, x) for x in water_sensors]

    def get_devices(self, key):
        if key not in self.devices:
            self.devices[key]=[]
        return self.devices[key]
    
    @property
    def empty_scenes(self):
        return self.get_devices(HubDeviceType.EMPTY_SCENE)
    
    @property
    def scenes(self):
        return self.get_devices(HubDeviceType.SCENE)
    
    @property
    def lights(self):
        return self.get_devices(HubDeviceType.LIGHT)
    
    @property
    def blinds(self):
        return self.get_devices(HubDeviceType.BLIND)
    
    @property
    def air_purifiers(self):
        return self.get_devices(HubDeviceType.AIR_PURIFIER)
    
    @property
    def outlets(self):
        return self.get_devices(HubDeviceType.OUTLET)
    
    @property
    def environment_sensors(self):
        return self.get_devices(HubDeviceType.ENVIRONMENT_SENSOR)
    
    @property
    def controllers(self):
        return self.get_devices(HubDeviceType.CONTROLLER)
    
    @property
    def open_close_sensors(self):
        return self.get_devices(HubDeviceType.OPEN_CLOSE_SENSOR)

    @property
    def motion_sensors(self):
        return self.get_devices(HubDeviceType.MOTION_SENSOR)
    
    @property
    def water_sensors(self):
        return self.get_devices(HubDeviceType.WATER_SENSOR)
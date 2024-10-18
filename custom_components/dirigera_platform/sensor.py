import logging

from .dirigera_lib_patch import HubX

from .base_classes import (
    battery_percentage_sensor,
    ikea_vindstyrka_temperature,
    ikea_vindstyrka_humidity,
    ikea_vindstyrka_pm25,
    ikea_vindstyrka_voc_index,
    WhichPM25,
    ikea_starkvind_air_purifier_sensor,
    current_amps_sensor ,
    current_active_power_sensor,
    current_voltage_sensor,
    total_energy_consumed_sensor,
    energy_consumed_at_last_reset_sensor ,
    total_energy_consumed_last_updated_sensor,
    total_energy_consumed_sensor,
    time_of_last_energy_reset_sensor
)
from .ikea_gateway import ikea_gateway

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, PLATFORM

logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    logger.debug("Staring async_setup_entry in SENSOR...")

    config = hass.data[DOMAIN][config_entry.entry_id]

    hub = HubX(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    platform: ikea_gateway = hass.data[DOMAIN][PLATFORM]

    # Precuationary delete all empty scenes
    if len(platform.empty_scenes) > 0:
        await hass.async_add_executor_job(hub.delete_empty_scenes)

    await add_controllers_sensors(hass, async_add_entities, hub, platform.controllers)
    await add_environment_sensors(async_add_entities, platform.environment_sensors)
    await add_outlet_power_attrs(async_add_entities, platform.outlets)

    # Add battery sensors
    battery_sensors = []
    battery_sensors.extend([battery_percentage_sensor(x) for x in platform.motion_sensors])
    battery_sensors.extend([battery_percentage_sensor(x) for x in platform.open_close_sensors])
    battery_sensors.extend([battery_percentage_sensor(x) for x in platform.water_sensors])
    battery_sensors.extend([battery_percentage_sensor(x) for x in platform.environment_sensors if getattr(x,"battery_percentage",None) is not None])
    battery_sensors.extend([battery_percentage_sensor(x) for x in platform.blinds if getattr(x,"battery_percentage",None) is not None])

    logger.debug(f"Found {len(battery_sensors)} battery sensors...")
    async_add_entities(battery_sensors)

    await add_air_purifier_sensors(async_add_entities, platform.air_purifiers)
    logger.debug("sensor Complete async_setup_entry")

async def add_environment_sensors(async_add_entities, env_devices):
    env_sensors = []
    for env_device in env_devices:
        # For each device setup up multiple entities
        # Some non IKEA environment sensors only have some of the attributes
        # hence check if it exists and then add
        if getattr(env_device,"current_temperature") is not None:
            env_sensors.append(ikea_vindstyrka_temperature(env_device))
        if getattr(env_device,"current_r_h") is not None:
            env_sensors.append(ikea_vindstyrka_humidity(env_device))
        if getattr(env_device,"current_p_m25") is not None:
            env_sensors.append(ikea_vindstyrka_pm25(env_device, WhichPM25.CURRENT))
        if getattr(env_device,"max_measured_p_m25") is not None:
            env_sensors.append(ikea_vindstyrka_pm25(env_device, WhichPM25.MAX))
        if getattr(env_device,"min_measured_p_m25") is not None:
            env_sensors.append(ikea_vindstyrka_pm25(env_device, WhichPM25.MIN))
        if getattr(env_device,"voc_index") is not None:
            env_sensors.append(ikea_vindstyrka_voc_index(env_device))

    logger.debug("Found {} env entities to setup...".format(len(env_sensors)))

    async_add_entities(env_sensors)

async def add_outlet_power_attrs(async_add_entities, outlets):
    # Add sensors for the outlets
    power_entities = []
    power_attrs=["current_amps","current_active_power","current_voltage","total_energy_consumed","energy_consumed_at_last_reset","time_of_last_energy_reset","total_energy_consumed_last_updated"]
    # Some outlets like INSPELNING Smart plug have ability to report power, so add those as well
    logger.debug("Looking for extra attributes of power/current/voltage in outlet....")
    for outlet in outlets:
        for attr in power_attrs:
            if hasattr(outlet._json_data.attributes, attr) and getattr(outlet._json_data.attributes, attr, None) is not None:
                power_entities.append(eval(f"{attr}_sensor(outlet)"))

    logger.debug(f"Found {len(power_entities)}, power attribute sensors for outlets")
    async_add_entities(power_entities)

async def add_air_purifier_sensors(async_add_entities, air_purifiers):
    #Now Air Purifier Sensors
    air_purifier_entities = []
    for air_purifier in air_purifiers:
        air_purifier_entities.append(
            ikea_starkvind_air_purifier_sensor(
                device=air_purifier,
                prefix="Filter Lifetime",
                device_class=SensorDeviceClass.DURATION,
                native_value_prop="filter_lifetime",
                native_uom="min",
                icon_name="mdi:clock-time-eleven-outline",
            )
        )

        air_purifier_entities.append(
            ikea_starkvind_air_purifier_sensor(
                device=air_purifier,
                prefix="Filter Elapsed Time",
                device_class=SensorDeviceClass.DURATION,
                native_value_prop="filter_elapsed_time",
                native_uom="min",
                icon_name="mdi:timelapse",
            )
        )

        air_purifier_entities.append(
            ikea_starkvind_air_purifier_sensor(
                device=air_purifier,
                prefix="Current pm25",
                device_class=SensorDeviceClass.PM25,
                native_value_prop="current_p_m25",
                native_uom="µg/m³",
                icon_name="mdi:molecule",
            )
        )

        air_purifier_entities.append(
            ikea_starkvind_air_purifier_sensor(
                device=air_purifier,
                prefix="Motor Runtime",
                device_class=SensorDeviceClass.DURATION,
                native_value_prop="motor_runtime",
                native_uom="min",
                icon_name="mdi:run-fast",
            )
        )

    async_add_entities(air_purifier_entities)

async def add_controllers_sensors(hass, async_add_entities, hub, controllers):
    logger.debug("Starting to add controller sensors...")
    # Controllers with more one button are returned as spearate controllers
    # their uniqueid has _1, _2 suffixes. Only the primary controller has
    # battery % attribute which we shall use to identify
    controller_entities = []
    for controller in controllers:
        # Hack to create empty scene so that we can associate it the controller
        # so that click of buttons on the controller can generate events on the hub
        clicks_supported = controller._json_data.capabilities.can_send
        clicks_supported = [ x for x in clicks_supported if x.endswith("Press") ]

        if len(clicks_supported) == 0:
            logger.debug(f"Ignoring controller for scene creation : {controller._json_data.id} as no press event supported : {controller._json_data.capabilities.can_send}")
        else:
            logger.debug(f"Will be creating empty scene for {controller._json_data.id}")
            await hass.async_add_executor_job(hub.create_empty_scene,controller._json_data.id, clicks_supported)

        if getattr(controller._json_data.attributes,"battery_percentage",None) is not None:
            controller_entities.append(controller)

    logger.debug("Found {} controller devices to setup...".format(len(controller_entities)))
    async_add_entities(controller_entities)
import logging

from dirigera import Hub
from dirigera.devices.outlet import Outlet

from homeassistant import config_entries, core
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .mocks.ikea_outlet_mock import ikea_outlet_mock
from .base_classes import ikea_base_device, ikea_base_device_sensor, current_amps_sensor , current_active_power_sensor, current_voltage_sensor, total_energy_consumed_sensor, energy_consumed_at_last_reset_sensor , total_energy_consumed_last_updated_sensor, total_energy_consumed_sensor, time_of_last_energy_reset_sensor
logger = logging.getLogger("custom_components.dirigera_platform")


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("SWITCH Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    # hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    hub = Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    outlets = []
    extra_entities = []
    
    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":
        logger.warning("Setting up mock outlets...")
        mock_outlet1 = ikea_outlet_mock(hub, "mock_outlet1")
        outlets = [mock_outlet1]
    else:
        hub_outlets : list[Outlet]  = await hass.async_add_executor_job(hub.get_outlets)
        
        extra_attrs=["current_amps","current_active_power","current_voltage","total_energy_consumed","energy_consumed_at_last_reset","time_of_last_energy_reset","total_energy_consumed_last_updated"]
        # Some outlets like INSPELNING Smart plug have ability to report power, so add those as well
        logger.debug("Looking for extra attributes of power/current/voltage in outlet....")
        for hub_outlet in hub_outlets:
            outlet = ikea_outlet(hass, hub, hub_outlet)
            switch_sensor = ikea_outlet_switch_sensor(outlet)
            outlets.append(switch_sensor)
            #for attr in extra_attrs:
                #if getattr(hub_outlet.attributes,attr) is not None:
                    #extra_entities.append(eval(f"{attr}_sensor(outlet)"))
                    
    logger.debug("Found {} outlet entities to setup...".format(len(outlets)))
    async_add_entities(outlets)
    logger.debug(f"Found {len(extra_entities)} extra entities for outlet...")
    if len(extra_entities) > 0:
        async_add_entities(extra_entities)
        
    logger.debug("SWITCH Complete async_setup_entry")

class ikea_outlet(ikea_base_device):
    def __init__(self, hass, hub, json_data):
        super().__init__(hass, hub, json_data, hub.get_outlet_by_id)

    async def async_turn_on(self):
        logger.debug("outlet turn_on")
        try:
            await self._hass.async_add_executor_job(self._json_data.set_on, True)
        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    async def async_turn_off(self):
        logger.debug("outlet turn_off")
        try:
            await self._hass.async_add_executor_job(self._json_data.set_on, False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

class ikea_outlet_switch_sensor(ikea_base_device_sensor, SwitchEntity):
    def __init__(self, device):
        super().__init__(device = device, name = device.name )
        
    @property
    def is_on(self):
        return self._device.is_on

    async def async_turn_on(self):
        logger.debug("sensor: outlet turn_on")
        await self._device.async_turn_on()

    async def async_turn_off(self):
        logger.debug("sensor: outlet turn_off")
        await self._device.async_turn_off()
import logging
from dirigera import Hub
from homeassistant import config_entries, core
from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError

from .const import DOMAIN
from .mocks.ikea_blinds_mock import ikea_blinds_mock
from .common_classes import ikea_base_device

logger = logging.getLogger("custom_components.dirigera_platform")


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("BLINDS Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    # hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    hub = Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    blinds = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":
        logger.warning("Setting up mock blinds...")
        mock_blind1 = ikea_blinds_mock(hub, "mock_blind1")
        blinds = [mock_blind1]
    else:
        hub_blinds = await hass.async_add_executor_job(hub.get_blinds)
        blinds = [IkeaBlinds(hass, hub, b) for b in hub_blinds]

    logger.debug("Found {} blinds entities to setup...".format(len(blinds)))
    async_add_entities(blinds)
    logger.debug("BLINDS Complete async_setup_entry")

class IkeaBlinds(ikea_base_device, CoverEntity):
    def __init__(self, hass, hub, json_data):
        logger.debug("IkeaBlinds ctor...")
        super().__init__(hass, hub, json_data, hub.get_blinds_by_id)

    @property
    def device_class(self) -> str:
        return CoverDeviceClass.BLIND

    @property
    def supported_features(self):
        return (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
        )

    @property
    def current_cover_position(self):
        return 100 - self.blinds_current_level

    @property
    def target_cover_position(self):
        return 100 - self.blinds_target_level

    @property
    def is_closed(self):
        if self.current_cover_position is None:
            return False
        return self.current_cover_position == 0

    @property
    def is_closing(self):
        if self.current_cover_position is None or self.target_cover_position is False:
            return False

        if self.current_cover_position != 0 and self.target_cover_position == 0:
            return True

        return False

    @property
    def is_opening(self):
        if self.current_cover_position is None or self.target_cover_position is False:
            return False

        if self.current_cover_position != 100 and self.target_cover_position == 100:
            return True

        return False

    async def async_open_cover(self, **kwargs):
        await self.hass.async_add_executor_job(self._json_data.set_target_level, 0)

    async def async_close_cover(self, **kwargs):
        await self.hass.async_add_executor_job(self._json_data.set_target_level, 100)

    async def async_set_cover_position(self, **kwargs):
        position = int(kwargs["position"])
        if position >= 0 and position <= 100:
            await self.hass.async_add_executor_job(self._json_data.set_target_level,100 - position)

    async def async_update(self):
        logger.debug("cover update...")
        try:
            self._json_data = await self.hass.async_add_executor_job(self._hub.get_blinds_by_id, self._json_data.id)
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")
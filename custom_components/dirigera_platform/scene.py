"""Imports scenes from Dirigera as scene entities in HA."""

import logging
from typing import Any

from dirigera import Hub
from dirigera.devices.scene import Scene as DirigeraScene

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .icons import to_hass_icon
from .base_classes import ikea_base_device

logger = logging.getLogger("custom_components.dirigera_platform")

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create scene entities from Dirigera scene."""
    config = hass.data[DOMAIN][entry.entry_id]
    hub = Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    # TODO: Add mock scenes
    if config[CONF_IP_ADDRESS] == "mock":
        return

    scenes: list[DirigeraScene] = await hass.async_add_executor_job(hub.get_scenes)
    entities: list[IkeaScene] = [IkeaScene(hass, hub, s) for s in scenes]
    logger.debug("Found %d scenes", len(entities))
    async_add_entities(entities)


class IkeaScene(ikea_base_device, Scene):
    """Implements scene entity for a Dirigera scene."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, hub: Hub, dirigera_scene: DirigeraScene) -> None:
        logger.debug("IkeaScena ctor...")
        super(ikea_base_device).__init__(hass, hub, dirigera_scene, hub.get_scene_by_id)

    def icon(self) -> str:
        """Return suitable replacement icon."""
        return to_hass_icon(self._json_data.info.icon)

    async def async_activate(self, **kwargs: Any) -> None:
        """Trigger Dirigera Scene."""
        logger.debug("Activating scene '%s' (%s)", self.name, self.unique_id)
        await self.hass.async_add_executor_job(self._dirigera_scene.trigger)
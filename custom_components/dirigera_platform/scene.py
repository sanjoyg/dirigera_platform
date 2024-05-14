"""Imports scenes from Dirigera as scene entities in HA."""

import logging
from typing import Any

from dirigera import Hub
from dirigera.devices.scene import Scene as DirigeraScene
from dirigera.devices.scene import Trigger, TriggerDetails

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .icons import to_hass_icon

logger = logging.getLogger("custom_components.dirigera_platform")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create scene entities from Dirigera scene."""
    config = hass.data[DOMAIN][entry.entry_id]
    hub = Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    Trigger.update_forward_refs()
    TriggerDetails.update_forward_refs()

    # TODO: Add mock scenes
    if config[CONF_IP_ADDRESS] == "mock":
        return

    scenes: list[DirigeraScene] = await hass.async_add_executor_job(hub.get_scenes)
    entities: list[IkeaScene] = [IkeaScene(hub, s) for s in scenes]
    logger.debug("Found %d scenes", len(entities))
    async_add_entities(entities)


class IkeaScene(Scene):
    """Implements scene entity for a Dirigera scene."""

    _attr_has_entity_name = True

    def __init__(self, hub: Hub, dirigera_scene: DirigeraScene) -> None:
        """Initialize."""
        self._hub = hub
        self._dirigera_scene = dirigera_scene
        self._attr_unique_id = dirigera_scene.id

    @property
    def name(self) -> str:
        """Return name from Dirigera."""
        return self._dirigera_scene.info.name

    @property
    def icon(self) -> str:
        """Return suitable replacement icon."""
        return to_hass_icon(self._dirigera_scene.info.icon)

    async def async_activate(self, **kwargs: Any) -> None:
        """Trigger Dirigera Scene."""
        logger.debug("Activating scene '%s' (%s)", self.name, self.unique_id)
        await self.hass.async_add_executor_job(self._dirigera_scene.trigger)

    async def async_update(self) -> None:
        """Fetch updated scene definition from Dirigera."""
        logger.debug("Updating scene '%s' (%s)", self.name, self.unique_id)
        try:
            self._dirigera_scene = await self.hass.async_add_executor_job(
                self._hub.get_scene_by_id, self.unique_id
            )
        except Exception as ex:
            logger.error(
                "Error encountered on update of '%s' (%s)", self.name, self.unique_id
            )
            logger.error(ex)
            raise HomeAssistantError from ex

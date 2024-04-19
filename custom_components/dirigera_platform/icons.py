"""Mapping icons from Dirigera to similar icons in Home Assistant."""

import logging

from dirigera.devices.scene import Icon

logger = logging.getLogger("custom_components.dirigera_platform")

# Mapping is mostly AI generated - some suggestions can likely be improved
# HASS icons: https://pictogrammers.com/library/mdi/
# Dirigera icons: https://github.com/Leggin/dirigera/blob/main/src/dirigera/devices/scene.py
icon_mapping: dict[Icon, str] = {
    Icon.SCENES_ARRIVE_HOME: "mdi:home-variant",
    Icon.SCENES_BOOK: "mdi:book",
    Icon.SCENES_BRIEFCASE: "mdi:briefcase",
    Icon.SCENES_BRIGHTNESS_UP: "mdi:lightbulb",
    Icon.SCENES_BROOM: "mdi:broom",
    Icon.SCENES_CAKE: "mdi:cake",
    Icon.SCENES_CLAPPER: "mdi:movie-open",
    Icon.SCENES_CLEAN_SPARKLES: "mdi:creation",
    Icon.SCENES_CUTLERY: "mdi:silverware-fork-knife",
    Icon.SCENES_DISCO_BALL: "mdi:ceiling-light",
    Icon.SCENES_GAME_PAD: "mdi:gamepad",
    Icon.SCENES_GIFT_BAG: "mdi:gift",
    Icon.SCENES_GIFT_BOX: "mdi:gift",
    Icon.SCENES_HEADPHONES: "mdi:headphones",
    Icon.SCENES_HEART: "mdi:heart",
    Icon.SCENES_HOME_FILLED: "mdi:home",
    Icon.SCENES_HOT_DRINK: "mdi:cup",
    Icon.SCENES_LADLE: "mdi:cup",
    Icon.SCENES_LEAF: "mdi:leaf",
    Icon.SCENES_LEAVE_HOME: "mdi:door",
    Icon.SCENES_MOON: "mdi:moon",
    Icon.SCENES_MUSIC_NOTE: "mdi:musical-note",
    Icon.SCENES_PAINTING: "mdi:palette",
    Icon.SCENES_POPCORN: "mdi:popcorn",
    Icon.SCENES_POT_WITH_LID: "mdi:pot",
    Icon.SCENES_SPEAKER_GENERIC: "mdi:speaker",
    Icon.SCENES_SPRAY_BOTTLE: "mdi:spray",
    Icon.SCENES_SUITCASE: "mdi:suitcase",
    Icon.SCENES_SUITCASE_2: "mdi:suitcase",
    Icon.SCENES_SUN_HORIZON: "mdi:weather-sunset",
    Icon.SCENES_TREE: "mdi:tree",
    Icon.SCENES_TROPHY: "mdi:trophy",
    Icon.SCENES_WAKE_UP: "mdi:alarm",
    Icon.SCENES_WEIGHTS: "mdi:dumbbell",
    Icon.SCENES_YOGA: "mdi:yoga",
}


def to_hass_icon(dirigera_icon: Icon) -> str:
    """Return suitable replacement icon."""
    hass_icon: str = icon_mapping[dirigera_icon]
    if hass_icon is None:
        logger.warning("Unknown icon %s", str(dirigera_icon))
        return "mdi:help"
    return hass_icon

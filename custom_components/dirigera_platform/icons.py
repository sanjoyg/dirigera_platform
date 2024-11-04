"""Mapping icons from Dirigera to similar icons in Home Assistant."""

import logging

from dirigera.devices.scene import Icon

logger = logging.getLogger("custom_components.dirigera_platform")

# Mapping is mostly AI generated - some suggestions can likely be improved
# HASS icons: https://pictogrammers.com/library/mdi/
# Dirigera icons: https://github.com/Leggin/dirigera/blob/main/src/dirigera/devices/scene.py
icon_mapping: dict[Icon, str] = {
    Icon.SCENES_ARRIVE_HOME: "mdi:home-import-outline",
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
    Icon.SCENES_GIFT_BAG: "mdi:shopping",
    Icon.SCENES_GIFT_BOX: "mdi:gift",
    Icon.SCENES_HEADPHONES: "mdi:headphones",
    Icon.SCENES_HEART: "mdi:heart",
    Icon.SCENES_HOME_FILLED: "mdi:home",
    Icon.SCENES_HOT_DRINK: "mdi:cup",
    Icon.SCENES_LADLE: "mdi:silverware-spoon",
    Icon.SCENES_LEAF: "mdi:leaf",
    Icon.SCENES_LEAVE_HOME: "mdi:home-export-outline",
    Icon.SCENES_MOON: "mdi:moon-waning-crescent",
    Icon.SCENES_MUSIC_NOTE: "mdi:music-note",
    Icon.SCENES_PAINTING: "mdi:palette",
    Icon.SCENES_POPCORN: "mdi:popcorn",
    Icon.SCENES_POT_WITH_LID: "mdi:pot",
    Icon.SCENES_SPEAKER_GENERIC: "mdi:speaker",
    Icon.SCENES_SPRAY_BOTTLE: "mdi:spray",
    Icon.SCENES_SUITCASE: "mdi:suitcase",
    Icon.SCENES_SUITCASE_2: "mdi:briefcase",
    Icon.SCENES_SUN_HORIZON: "mdi:weather-sunset",
    Icon.SCENES_TREE: "mdi:pine-tree",
    Icon.SCENES_TROPHY: "mdi:trophy",
    Icon.SCENES_WAKE_UP: "mdi:alarm",
    Icon.SCENES_WEIGHTS: "mdi:dumbbell",
    Icon.SCENES_YOGA: "mdi:yoga",
}

ikea_to_hass_mapping: dict[str, str] = {
    "scenes_arrive_home": "mdi:home-import-outline",
    "scenes_book": "mdi:book",
    "scenes_briefcase": "mdi:briefcase",
    "scenes_brightness_up": "mdi:lightbulb",
    "scenes_broom": "mdi:broom",
    "scenes_cake": "mdi:cake",
    "scenes_clapper": "mdi:movie-open",
    "scenes_clean_sparkles": "mdi:creation",
    "scenes_cutlery": "mdi:silverware-fork-knife",
    "scenes_disco_ball": "mdi:ceiling-light",
    "scenes_game_pad": "mdi:gamepad",
    "scenes_gift_bag": "mdi:shopping",
    "scenes_gift_box": "mdi:gift",
    "scenes_headphones": "mdi:headphones",
    "scenes_heart": "mdi:heart",
    "scenes_home_filled": "mdi:home",
    "scenes_hot_drink": "mdi:cup",
    "scenes_ladle": "mdi:silverware-spoon",
    "scenes_leaf": "mdi:leaf",
    "scenes_leave_home": "mdi:home-export-outline",
    "scenes_moon": "mdi:moon-waning-crescent",
    "scenes_music_note": "mdi:music-note",
    "scenes_painting": "mdi:palette",
    "scenes_popcorn": "mdi:popcorn",
    "scenes_pot_with_lid": "mdi:pot",
    "scenes_speaker_generic": "mdi:speaker",
    "scenes_spray_bottle": "mdi:spray",
    "scenes_suitcase": "mdi:suitcase",
    "scenes_suitcase_2": "mdi:briefcase",
    "scenes_sun_horizon": "mdi:weather-sunset",
    "scenes_tree": "mdi:pine-tree",
    "scenes_trophy": "mdi:trophy",
    "scenes_wake_up": "mdi:alarm",
    "scenes_weights": "mdi:dumbbell",
    "scenes_yoga": "mdi:yoga"
}

def ikea_to_hass_icon(ikea_icon) -> str:
    if ikea_icon in ikea_to_hass_mapping:
        return ikea_to_hass_mapping[ikea_icon]
    
    logger.warning(f"Unknown icon {ikea_icon}")
    return "mdi:help" 

def to_hass_icon(dirigera_icon: Icon) -> str:
    """Return suitable replacement icon."""
    hass_icon: str = icon_mapping[dirigera_icon]
    if hass_icon is None:
        logger.warning("Unknown icon %s", str(dirigera_icon))
        return "mdi:help"
    return hass_icon

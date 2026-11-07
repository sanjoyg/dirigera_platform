DOMAIN = "dirigera_platform"
PLATFORM = "dirigera_platform"
CONF_HIDE_DEVICE_SET_BULBS = "hide_device_set_bulbs"
DISCOVERY_COORDINATOR = "discovery_coordinator"

from homeassistant import const as ha_const

# Home Assistant 2026.7 added UnitOfDensity / UnitOfRatio; the CONCENTRATION_* constants they replace are
# deprecated and removed in Home Assistant 2027.8. hacs.json sets no minimum version, so releases before 2026.7
# (which only have the old constants) keep working.
if hasattr(ha_const, "UnitOfDensity") and hasattr(ha_const, "UnitOfRatio"):
    UNIT_MICROGRAMS_PER_CUBIC_METER = ha_const.UnitOfDensity.MICROGRAMS_PER_CUBIC_METER
    UNIT_PARTS_PER_MILLION = ha_const.UnitOfRatio.PARTS_PER_MILLION
else:
    UNIT_MICROGRAMS_PER_CUBIC_METER = ha_const.CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    UNIT_PARTS_PER_MILLION = ha_const.CONCENTRATION_PARTS_PER_MILLION

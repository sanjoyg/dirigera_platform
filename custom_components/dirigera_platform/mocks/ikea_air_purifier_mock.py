from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import HomeAssistantError
from homeassistant.components.fan import FanEntity, FanEntityFeature

import logging
import datetime
import math
from dirigera.devices.air_purifier import FanModeEnum
from ..sensor import ikea_vindstyrka_device
from ..const import DOMAIN

logger = logging.getLogger("custom_components.dirigera_platform")


class ikea_starkvind_air_purifier_mock_device:
    counter = 0

    def __init__(self) -> None:
        ikea_starkvind_air_purifier_mock_device.counter = (
            ikea_starkvind_air_purifier_mock_device.counter + 1
        )
        self._name = "MOCK Air Purifier " + str(
            ikea_starkvind_air_purifier_mock_device.counter
        )
        self._unique_id = "AP1907151129080101_" + str(
            ikea_starkvind_air_purifier_mock_device.counter
        )
        self._updated_at = None
        self._motor_state = 20
        self._status_light = True
        self._child_lock = True
        self._fan_mode = "auto"
        logger.debug("Air purifer Mock Device ctor complete...")

    def update(self):
        if (
            self._updated_at is None
            or (datetime.datetime.now() - self._updated_at).total_seconds() > 10
        ):
            try:
                logger.info("AirPurifier Mock Update called...")
                self._updated_at = datetime.datetime.now()
            except Exception as ex:
                logger.error("error encountered running update on : {}".format(self.name))
                logger.error(ex)
                raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    @property
    def available(self):
        return True

    @property
    def is_on(self):
        logger.debug("ikea_starkvind_air_purifier_mock_device is_on called...")
        if self.available and self.motor_state > 0:
            return True
        return False

    @property
    def device_info(self) -> DeviceInfo:
        logger.info("Got device_info call on airpurifier mock...")
        return DeviceInfo(
            identifiers={("dirigera_platform", self._unique_id)},
            name=self._name,
            manufacturer="MOCK",
            model="Mock 1.0",
            sw_version="Mock SW 1.0",
            suggested_area="Kitchen",
        )

    @property
    def name(self) -> str:
        logger.info("Returning name as {} airpurifier mock...".format(self._name))
        return self._name

    @property
    def unique_id(self):
        logger.info(
            "Returning unique_id as {} airpurifier mock...".format(self._unique_id)
        )
        return self._unique_id

    @property
    def supported_features(self):
        logger.debug("AirPurifier supported features called...")
        return FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED

    @property
    def motor_state(self) -> int:
        return self._motor_state

    @property
    def percentage(self) -> int:
        # Scale the 1-50 into
        return math.ceil(self.motor_state * 100 / 50)

    @property
    def fan_mode_sequence(self) -> str:
        return "lowMediumHighAuto"

    @property
    def preset_modes(self):
        return [e.value for e in FanModeEnum]

    @property
    def preset_mode(self) -> str:
        return self._fan_mode

    @property
    def speed_count(self):
        return 50

    @property
    def motor_runtime(self):
        return 30

    @property
    def filter_alarm_status(self) -> bool:
        return False

    @property
    def filter_elapsed_time(self) -> int:
        return 60

    @property
    def filter_lifetime(self) -> int:
        return 90

    @property
    def current_p_m25(self) -> int:
        return 241

    @property
    def status_light(self) -> bool:
        logger.debug("air purifier mock status_light : {}".format(self._status_light))
        return self._status_light

    @property
    def child_lock(self) -> bool:
        logger.debug("air purifier mock child_lock : {}".format(self._child_lock))
        return self._child_lock

    def set_percentage(self, percentage: int) -> None:
        # Convert percent to speed
        desired_speed = math.ceil(percentage * 50 / 100)
        logger.debug(
            "set_percentage got : {}, scaled to : {}".format(percentage, desired_speed)
        )
        self._motor_state = desired_speed

    def set_status_light(self, status: bool) -> None:
        logger.debug("set_status_light : {}".format(status))
        self._status_light = status

    def set_child_lock(self, status: bool) -> None:
        logger.debug("set_child_lock : {}".format(status))
        self._child_lock = status

    def set_fan_mode(self, preset_mode: FanModeEnum) -> None:
        logger.debug("set_fan_mode : {}".format(preset_mode.value))
        self._fan_mode = str(preset_mode.value)
        if preset_mode == FanModeEnum.AUTO:
            self._motor_state = 1
        elif preset_mode == FanModeEnum.HIGH:
            self._motor_state = 50
        elif preset_mode == FanModeEnum.MEDIUM:
            self._motor_state = 25
        elif preset_mode == FanModeEnum.LOW:
            self._motor_state = 10
        else:
            logger.debug("Unknown fan_mode called...")

    def set_preset_mode(self, preset_mode: str):
        logger.debug("set_preset_mode : {}".format(preset_mode))
        mode_to_set = None
        if preset_mode == FanModeEnum.AUTO.value:
            mode_to_set = FanModeEnum.AUTO
        elif preset_mode == FanModeEnum.HIGH.value:
            mode_to_set = FanModeEnum.HIGH
        elif preset_mode == FanModeEnum.MEDIUM.value:
            mode_to_set = FanModeEnum.MEDIUM
        elif preset_mode == FanModeEnum.LOW.value:
            mode_to_set = FanModeEnum.LOW

        if mode_to_set is None:
            logger.error("Non defined preset used to set : {}".format(preset_mode))
            return

        logger.debug("set_preset_mode equated to : {}".format(mode_to_set.value))
        self.set_fan_mode(mode_to_set)

    def turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None:
        logger.debug(
            "Airpurifier call to turn_on with percentage: {}, preset_mode: {}".format(
                percentage, preset_mode
            )
        )
        if preset_mode is not None:
            self.set_preset_mode(preset_mode)
        elif percentage is not None:
            self.set_percentage(percentage)
        else:
            logger.debug(
                "We were asked to be turned on but percentage and preset were not set, using last know"
            )
            if self.preset_mode is not None:
                self.set_preset_mode(self.preset_mode)
            elif self.percentage is not None:
                self.set_percentage(self.percentage)
            else:
                logger.debug("No last known value, setting to auto")
                self.set_preset_mode("auto")

    def turn_off(self, **kwargs) -> None:
        self.set_percentage(0)

    async def async_will_remove_from_hass(self) -> None:
        ikea_starkvind_air_purifier_mock_device.counter = (
            ikea_starkvind_air_purifier_mock_device.counter - 1
        )

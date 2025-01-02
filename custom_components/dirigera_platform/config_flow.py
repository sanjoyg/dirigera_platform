import logging
import string
from typing import Any, Dict

from dirigera.hub.auth import get_token, random_code, send_challenge
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.components.light import PLATFORM_SCHEMA
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_HIDE_DEVICE_SET_BULBS

logger = logging.getLogger("custom_components.dirigera_platform")

HUB_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): cv.string, 
    vol.Optional(CONF_HIDE_DEVICE_SET_BULBS, default=True): cv.boolean
    })

NULL_SCHEMA = vol.Schema({})


def get_dirigera_token_step_one(ip_address):
    logger.debug("In generate token step one ")
    ALPHABET = f"_-~.{string.ascii_letters}{string.digits}"
    CODE_LENGTH = 128
    code_verifier = random_code(ALPHABET, CODE_LENGTH)
    code = send_challenge(ip_address, code_verifier)
    logger.debug("returning from generate token step one")
    return code, code_verifier


def get_dirigera_token_step_two(ip_address, code, code_verifier):
    logger.debug("in generated token step two ")
    token = get_token(ip_address, code, code_verifier)
    logger.debug("returning from generate token step two")
    return token


class dirigera_platform_config_flow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.ip = None
        self.code = None
        self.hide_device_set_bulbs = True 
        self.code_verifier = None

    async def async_step_user(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        logger.debug("CONFIG async_step_user called....")

        errors: Dict[str, str] = {}

        if user_input is not None and CONF_IP_ADDRESS in user_input:
            logger.debug("async step init user input is not none...")
            logger.debug("user_input is ")
            logger.debug(user_input)

            self.ip = user_input[CONF_IP_ADDRESS]
            self.hide_device_set_bulbs = user_input[CONF_HIDE_DEVICE_SET_BULBS]

            if self.ip is None or len(self.ip.strip()) == 0:
                logger.debug("IP specified is blank...")
                errors["base"] = "ip_not_specified"
            else:
                try:
                    logger.debug("Moving to second step....")
                    if self.ip == "mock":
                        logger.warning(
                            "Using mock ip, skipping token generation step 1"
                        )
                    else:
                        (
                            self.code,
                            self.code_verifier,
                        ) = await core.async_get_hass().async_add_executor_job(
                            get_dirigera_token_step_one, self.ip
                        )
                    return self.async_show_form(
                        step_id="action", data_schema=NULL_SCHEMA, errors=errors
                    )
                except Exception as ex:
                    logger.error("Failed to connect to dirigera hub")
                    logger.error(ex)
                    errors["base"] = "hub_connection_fail"

        return self.async_show_form(
            step_id="user", data_schema=HUB_SCHEMA, errors=errors
        )

    async def async_step_action(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        logger.debug("CONFIG async_step_action called....")
        # Since IP is specified we will try and get the auth token an set that up in
        # the config for use at a later time
        errors: Dict[str, str] = {}
        logger.debug("ip {}".format(self.ip))

        # Try and get the token step_2
        try:
            if self.ip == "mock":
                logger.warning("Using mock ip, skipping token generation step 2")
                token = "mock"
            else:
                token = await core.async_get_hass().async_add_executor_job(
                    get_dirigera_token_step_two, self.ip, self.code, self.code_verifier
                )
                logger.info("Successful generating token")

            user_input[CONF_IP_ADDRESS] = self.ip
            user_input[CONF_TOKEN] = token
            user_input[CONF_HIDE_DEVICE_SET_BULBS] = self.hide_device_set_bulbs

            return self.async_create_entry(
                title="IKEA Dirigera Hub : {}".format(user_input[CONF_IP_ADDRESS]),
                data=user_input,
            )
        except Exception as ex:
            logger.error("Failed to connect to dirigera hub")
            logger.error(ex)
            errors["base"] = "hub_connection_fail"

        return self.async_show_form(
            step_id="user", data_schema=NULL_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        logger.debug("OPTIONS flow handler init...")
        logger.debug(config_entry.data)

        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        # Called when configure is called from an existing configured integration
        # The first screen that is shown, asl called after IP when submitted

        logger.error("OPTIONS async_step_init called....")
        logger.error(user_input)

        errors: Dict[str, str] = {}

        if user_input is not None:
            logger.error("async step init user input is not none...")
            logger.error("user_input is ")
            logger.error(user_input)

            self.ip = user_input[CONF_IP_ADDRESS]
            self.hide_device_set_bulbs = user_input[CONF_HIDE_DEVICE_SET_BULBS]
            logger.debug(f"IN THIS STEP hide.. set {self.hide_device_set_bulbs}")

            if self.ip is None or len(self.ip.strip()) == 0:
                logger.debug("IP specified is blank...")
                errors["base"] = "ip_not_specified"
            else:
                try:
                    logger.error("Moving to second step....")
                    if self.ip == "mock":
                        logger.warning(
                            "Using mock ip, skipping token generation step 1"
                        )
                    else:
                        (
                            self.code,
                            self.code_verifier,
                        ) = await core.async_get_hass().async_add_executor_job(
                            get_dirigera_token_step_one, self.ip
                        )
                    return self.async_show_form(
                        step_id="action", data_schema=NULL_SCHEMA, errors=errors
                    )
                except Exception as ex:
                    logger.error("Failed to connect to dirigera hub")
                    logger.error(ex)
                    errors["base"] = "hub_connection_fail"

        return self.async_show_form(
            step_id="init", data_schema=HUB_SCHEMA, errors=errors
        )

    async def async_step_action(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        logger.debug("CONFIG async_step_action called....")
        logger.debug(user_input)
        # Since IP is specified we will try and get the auth token an set that up in
        # the config for use at a later time
        errors: Dict[str, str] = {}
        logger.error("ip {}".format(self.ip))
        logger.error(f"hide device set bulbs {self.hide_device_set_bulbs}")
        # Try and get the token step_2
        try:
            if self.ip == "mock":
                logger.warning("Using mock ip, skipping token generation step 2")
                token = "mock"
            else:
                token = await core.async_get_hass().async_add_executor_job(
                    get_dirigera_token_step_two, self.ip, self.code, self.code_verifier
                )
                logger.info("Successful generating token")
                logger.error(token)

            user_input[CONF_IP_ADDRESS] = self.ip
            user_input[CONF_TOKEN] = token
            user_input[CONF_HIDE_DEVICE_SET_BULBS] = self.hide_device_set_bulbs
            logger.error("before create entry...")
            logger.error(user_input)

            self.hass.config_entries.async_update_entry(self.config_entry, data=user_input,
                                                        title="IKEA Dirigera Hub : {}".format(user_input[CONF_IP_ADDRESS]),)
            #return self.async_create_entry(title=None, data=None)
            #return self.config_entry.async_update_entry(user_input)
            return self.async_create_entry(
                title="IKEA Dirigera Hub : {}".format(user_input[CONF_IP_ADDRESS]),
                data=user_input,
            )
        except Exception as ex:
            logger.error("Failed to connect to dirigera hub")
            logger.error(ex)
            errors["base"] = "hub_connection_fail"

        return self.async_show_form(
            step_id="init", data_schema=NULL_SCHEMA, errors=errors
        )

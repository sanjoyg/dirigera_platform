import logging
import voluptuous as vol
import string 

import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import PLATFORM_SCHEMA
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant import data_entry_flow
from homeassistant import config_entries, core
from homeassistant.core import callback

from dirigera.hub.auth import random_code, send_challenge, get_token

from typing import Any, Dict
from .const import DOMAIN

import logging
logger = logging.getLogger("custom_components.dirigera_platform")

HUB_SCHEMA = vol.Schema ({
    vol.Required(CONF_IP_ADDRESS): cv.string
})

NULL_SCHEMA = vol.Schema ({})

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
        self.code_verifier = None 

    async def async_step_user( self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        logger.debug("CONFIG async_step_user called....")
        
        errors: Dict[str, str] = {}

        if user_input is not None and CONF_IP_ADDRESS in user_input:
            logger.debug("async step init user input is not none...")
            logger.debug("user_input is ")
            logger.debug(user_input)
           
            self.ip = user_input[CONF_IP_ADDRESS]

            if self.ip is None or len(self.ip.strip()) == 0:
                logger.debug("IP specified is blank...")
                errors["base"] = "ip_not_specified"
            else:
                try:
                    logger.debug("Moving to second step....")
                    if self.ip == "mock":
                        logger.warning("Using mock ip, skipping token generation step 1")
                    else:
                        self.code, self.code_verifier = await core.async_get_hass().async_add_executor_job(get_dirigera_token_step_one,self.ip)
                    return self.async_show_form(step_id="action", data_schema=NULL_SCHEMA, errors=errors)
                except Exception as ex:
                    logger.error("Failed to connect to dirigera hub")
                    logger.error(ex)
                    errors["base"] = "hub_connection_fail"

        return self.async_show_form(step_id="user", data_schema=HUB_SCHEMA, errors=errors)

    async def async_step_action( self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
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
                token = await core.async_get_hass().async_add_executor_job(get_dirigera_token_step_two,self.ip, self.code, self.code_verifier)
                logger.info("Successful generating token")
                logger.debug(token)
            
            user_input[CONF_IP_ADDRESS] = self.ip
            user_input[CONF_TOKEN] = token 
            
            return self.async_create_entry(title="IKEA Dirigera Hub : {}".format(user_input[CONF_IP_ADDRESS]), data=user_input)
        except Exception as ex:
            logger.error("Failed to connect to dirigera hub")
            logger.error(ex)
            errors["base"] = "hub_connection_fail"

        return self.async_show_form(step_id="user", data_schema=NULL_SCHEMA, errors=errors)

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

    async def async_step_init( self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        logger.debug("OPTIONS async_step_init called....")
        
        errors: Dict[str, str] = {}

        if user_input is not None:
            logger.debug("async step init user input is not none...")
            logger.debug("user_input is ")
            logger.debug(user_input)
           
            self.ip = user_input[CONF_IP_ADDRESS]

            if self.ip is None or len(self.ip.strip()) == 0:
                logger.debug("IP specified is blank...")
                errors["base"] = "ip_not_specified"
            else:
                try:
                    logger.debug("Moving to second step....")
                    if self.ip == "mock":
                        logger.warning("Using mock ip, skipping token generation step 1")
                    else:
                        self.code, self.code_verifier = await core.async_get_hass().async_add_executor_job(get_dirigera_token_step_one,self.ip)
                    return self.async_show_form(step_id="action", data_schema=NULL_SCHEMA, errors=errors)
                except Exception as ex:
                    logger.error("Failed to connect to dirigera hub")
                    logger.error(ex)
                    errors["base"] = "hub_connection_fail"

        return self.async_show_form(step_id="init", data_schema=HUB_SCHEMA, errors=errors)
    
    async def async_step_action( self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
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
                token = await core.async_get_hass().async_add_executor_job(get_dirigera_token_step_two,self.ip, self.code, self.code_verifier)
                logger.info("Successful generating token")
                logger.debug(token)
            
            user_input[CONF_IP_ADDRESS] = self.ip
            user_input[CONF_TOKEN] = token 
            
            return self.async_create_entry(title="IKEA Dirigera Hub : {}".format(user_input[CONF_IP_ADDRESS]), data=user_input)
        except Exception as ex:
            logger.error("Failed to connect to dirigera hub")
            logger.error(ex)
            errors["base"] = "hub_connection_fail"

        return self.async_show_form(step_id="init", data_schema=NULL_SCHEMA, errors=errors)
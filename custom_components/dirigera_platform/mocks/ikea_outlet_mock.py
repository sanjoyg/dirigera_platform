from homeassistant.components.switch import SwitchEntity

import logging

logger = logging.getLogger("custom_components.dirigera_platform")

class ikea_outlet_mock(SwitchEntity):
    counter = 0
    def __init__(self, hub, hub_outlet):
        self._hub = hub 
        self._hub_outlet = hub_outlet
        ikea_outlet_mock.counter = ikea_outlet_mock.counter + 1
        self._name = "ikea_outlet_{}".format(ikea_outlet_mock.counter)
        self._is_on = False 

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_on(self):
        return self._is_on
    
    def turn_on(self):
        self._is_on = True
    
    def turn_off(self):
        self._is_on = False 
    
    def update(self):
        pass
        

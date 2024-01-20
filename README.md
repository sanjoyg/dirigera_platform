# IKEA Dirigera Hub Integration
This custom components help integrating HomeAssistant with the new IKEA Dirigera hub. This integration is a scaffolding on the great work done by Nicolas Hilberg  at https://github.com/Leggin/dirigera

## Pre-requisite
1. Identify the IP of the gateway - Usually looking at the client list in your home router interface will give that.

## Installing
- Like all add-on installation goto the "HACS" option in the left menu bar in home assistant
- Select Integration and add custom repository and enter this repositoy

## Using the integration
1. One you get to add integration and get to the configuration screen, the IP of the gateway will be requested. 
   **IMPORTANT**
   Before hitting enter be near the IKEA Dirigera hub as post entering IP a request to press the action button on the hub

2. Once you get the screen requesting to press the action button, physically press the button once and then click on submit

3. If the IP is right and action button has been pressed, then the integration will be added and all devices registed will be shows. At this time the following device types are supported
    a. Lights
    b. Outlets

## Testing installation with mock
1. If you enter the IP as "mock" then mock bulbs and outlet will be adedd.
2. Once you verify that the bulbs and outlets are added feel free to delete the integration

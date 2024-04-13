## IKEA Dirigera Hub Integration
This custom components help integrating HomeAssistant with the new IKEA Dirigera hub. This integration is a scaffolding on the great work done by Nicolas Hilberg  at https://github.com/Leggin/dirigera

Supports
* Lights
* Outlets
* Open/Close Sensors
* Motion Sensor
* Environment Sensor
* FYRTUR Blinds               
* STYRBAR Remotes      
* AirPurifier
* STARKVIND AirPurifier
* VALLHORN Motion Sensors

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
    c. Motion Sensor
    d. VindStyrka Environment Sensor
    e. Blinds               
    f. STYRBAR Remotes      
    g. AirPurifier

## Testing installation with mock
1. If you enter the IP as "mock" then mock bulbs and outlet will be added.
2. Once you verify that the bulbs and outlets are added feel free to delete the integration

Here is how it looks

1. After you have downloaded the integration from HACS and go to Setting -> Integration -> ADD INTEGRATION to add the dirigera integration, the following screen will come up

![](https://github.com/sanjoyg/dirigera_platform/blob/main/screenshots/config-ip-details.png)

To test the integration, enter the IP as "mock". The check-box indicates if the bulbs/lights associated with a device-set should be visible as entities or not

![](https://github.com/sanjoyg/dirigera_platform/blob/main/screenshots/config-mock.png)

The integration would prompt to press the action button on the hub

![](https://github.com/sanjoyg/dirigera_platform/blob/main/screenshots/config-press-action.png)

Since this is mock, we would get a success message

![](https://github.com/sanjoyg/dirigera_platform/blob/main/screenshots/config-hub-setup-complete-mock.png)

Once this is complete you would see two bulbs and two outlets appearing.

![](https://github.com/sanjoyg/dirigera_platform/blob/main/screenshots/mock-lights.png)
![](https://github.com/sanjoyg/dirigera_platform/blob/main/screenshots/mock-outlets.png)

## Raising Issue

Now I dont have access to all sensors, hence what will be useful is when you raise an issue also supply to the JSON that the hub returns.
To get the JSON do the following

* Go to Developer -> Service and invoke dirigera_platform.dump_data without any parameters
* Look at the HASS log which would have the JSON. 
* If you see any platform errors include that as well



# heating-control-system
A Raspberry Pi based heating control system for a combi boiler.

The problem:

Our ?? combi boiler is located in the loft.  It gets irritating for my wife, especially in the winter months when it is very cold up there, to clamber up the rickety loft hatch stairs to turn on the heating and make adjustments to the clock.  We already had an old style thermostat () but this was placed in the hallway - not the best placement.

The solution:

A 'smart thermostat'.  I was not happy with the drawbacks of a lot of the proprietary systems I could purchase such as Hive and Nest.  I wanted a more open system where I could build in features and functions over time.  Such as control via telephone (using my existing Digium Asterisk telecommunications server), email control, scheduling using Google Calendar or similar.  433Mhz remote control using my existing controller for my plug sockets etc.

This code is a work in progress.

It works as a client/server model whereby one Raspberry Pi 3 is located in the loft (the server), connected to the combi boiler via a relay, with another Raspberry Pi 3 located in the lounge (a client) which acts as a thermostat with a temperature sensor.

I plan on having multiple clients throughout the rooms in my house so that the system can assess temperatures in different rooms and calculate the average temperature.

**Current features with this code:**

_Via telephone_

I have programmed my Digium Asterisk telecommunications server to recognise my own and my wifes mobile telephone numbers.  When we call the house, we are offered menu of choices.  We can also dial extension 100 from any interal house telephone to reach the same menu:

*Press 1 to check heating status (tells us if heating is currently on or off and tells us the current temperature in the lounge)
*Press 2 to turn on heating
*Press 3 to turn off heating
*Press 4 to set target temperature (we enter a 2 digit temperature in degrees c which is then set as target for the lounge)
*Press 5 to call house telephone

_Via 433Mhz remote control_

We have a remote control which is used to turn on and off various 433Mhz plug sockets throughout the house.  This rmeote control has 2 unused buttons on it so I have used one as a means to turn on the heating and the other to turn off the heating.  This is achived via my existing SDR system which is constantly listening for 433Mhz wireless transmissions.

_Via Linux command line interface_

All features can be used from the Linux command line.  In fact it is these commands which are executed by Asterisk and the SDR.  They all act as clients.

To start the server on the lot based Raspberry Pi 3:

python3.5 thermostat.py server null

python3.5 thermostat.py client send_temperature lounge
python3.5 thermostat.py client get_heating_on_off_status cli
python3.5 thermostat.py client set_target_temperature lounge 21

# evohome-indigo-plugin
 Python 3 version of indigo plugin to support Honeywell Evohome to work with Indigo version 2023.1.0 onwards that requires all plugns to run in Python 3

This plugin was derived from the previous Honeywell plugin, and is a direct replacement functionally for that for european Evohome users. It utilises the Evohome python client
available https://github.com/watchforstock/evohome-client which only supports the European API calls.

If your Evhome Credentials work at https://international.mytotalconnectcomfort.com/Account/Login then you should be able to use the plugin. This will not work with the Wifi Thermostat or the Redlink Gateways used in the US.
 
 Documentation is here
 
 But the process is add your evohome credentials to the plugin config and enable debugging (for now)
 Please do take care entering your credentials, as you can find the retry limit exceeded (each time to hit save on the config dialog it will make a logon attempt)

 Dump the device ids to the event window via the Log Evohome device ID's in the plugin menu
 
 If that looks OK and shows all of your zones and location info
 
 Create the devices from the plugin menu, and they should match your zones, location info, Hot Water if you have it and the controller itself (showing system mode)

 I have seen the situation once when the devices do not start automatically the first time (they show a temp of zero)
 It make refresh automatically at the next refresh cycle (30's is the default, configurable in the plugin config)
 If it does not the restart the plugin and it should continue from that point forward.  If you do experience this please capture any event log details.

All Actions SHOULD work in the same way as the Honeywell plugin, but please test, and don't hold me responsible for your energy bill, it is at your risk :-)

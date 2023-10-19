# evohome-indigo-plugin
 Python 3 version of indigo plugin
 Documentation to follow but the process is add your evohome credentials to the plugin config and enable debugging (for now)
 Dump the device ids to the event window via the Log Evohome device ID's in the plugin menu
 If that looks OK and shows all of your zones and locaiton info
 create the devices again from the plugin menu

 I have seen the situation once when the devices do not start automatically the first time (they show a temp of zero)
 It make refresh automatically at the next refresh cycle (30's is the default, configurable in the plugin config)
 If it does not the restart the plugin and it should continue from that point forward.  If you do experience this please capture any event log details.

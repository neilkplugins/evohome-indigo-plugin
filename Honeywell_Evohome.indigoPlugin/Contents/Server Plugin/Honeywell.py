#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Based on Nlagaros Honeywell plugin

import indigo
from evohomeclient2 import EvohomeClient

try:
	import json
except:
	import simplejson as json

import sys
import os
import time
from datetime import datetime, timedelta
import logging
import requests

eventTimer = 5
errorTimer = 60
reqTimeout = 5

class Honeywell(object):

	######################################################################################
	# class init & del
	def __init__(self, plugin):
		self.plugin = plugin
		self.needToGetPluginPrefs = True
		self.timer_refresh = None 	# timestamp of last token refresh
		self.timer_events = None 	# timestamp of last event poll
		self.timer_full = None 		# timestamp of last device fetch
		self.timer_lasttry = None 	# timestamp of last token attempt
		self.token_refresh = None
		#self.token_life = 120
		self.evohome = False
		self.evohome_UserID = None
		self.evohome_Password = None
		self.evohomeStatus = False
		self.evohome_timer_full = None
		self.evohome_token_refresh = None
		self.deviceList = []
		self.interval = None
		self.maxErrors = None

	def __del__(self):
		pass

	def startup(self):
		self.plugin.debugLog("Evohome Plugin Startup...")

		logging.getLogger("requests").setLevel(logging.WARNING)

		self.closedPrefsConfigUi(None, None)
		self.start_evohome()

	def deviceStartComm(self, dev):
		self.plugin.debugLog("Starting device: %s" % dev.name)
		if dev.id not in self.deviceList:
			self.deviceList.append(dev.id)
			dev.stateListOrDisplayStateIdChanged()

	def deviceStopComm(self, device):
		self.plugin.debugLog("Stopping device: %s" % device.name)
		if device.id in self.deviceList:
			self.deviceList.remove(device.id)

	def restartPlugin(self):
		HoneywellPlug = indigo.server.getPlugin("com.barn.indigoplugin.Honeywell_Evohome")
		HoneywellPlug.restart (waitUntilDone = True)
		exit()

	def start_evohome(self):

		self.plugin.debugLog("Starting Evohome......")
		self.evohomeStatus = True
		try:
			if self.plugin.pluginPrefs['refresh_token']=='':
				client = EvohomeClient(self.plugin.pluginPrefs['evohome_UserID'], self.plugin.pluginPrefs['evohome_Password'],)
			else:
				client = EvohomeClient(self.plugin.pluginPrefs['evohome_UserID'], self.plugin.pluginPrefs['evohome_Password'], refresh_token=self.plugin.pluginPrefs['refresh_token'], access_token=self.plugin.pluginPrefs['access_token'], access_token_expires=datetime.strptime(self.plugin.pluginPrefs['access_token_expires'],"%Y-%m-%d %H:%M:%S.%f"))
		except Exception as error:
				self.evohomeStatus = False
				self.plugin.errorLog("[%s] Cannot read Evohome data " % time.asctime())
				self.plugin.debugLog(str(error))
				return

		self.plugin.debugLog("Refresh token expires [%s]" % client.access_token_expires)

		self.plugin.pluginPrefs['refresh_token']=client.refresh_token
		self.plugin.pluginPrefs['access_token']=client.access_token
		self.plugin.pluginPrefs['access_token_expires']=str(client.access_token_expires)
		indigo.server.log("[%s] Authenticated to Evohome API (Initial Call)." % time.asctime())
		self.evohome_timer_full = time.time()

		if self.evohomeStatus == True:
			self.evohome_initDevice()
			self.evohome_get_all(client)
		else:
			self.plugin.errorLog("[%s] Error: Cannot authenticate to Evohome API.  Retrying in %s ..." % (time.asctime(), self.interval))


	######################################################################################
	# Concurrent Thread Start
	def runConcurrentThread(self):
		self.plugin.debugLog("Running Concurrent Thread")
		self.evohome_timer_full = time.time()

		while self.plugin.StopThread == False:

			#if self.evohomeStatus == True:
			if (time.time() - self.evohome_timer_full) > int(self.interval):
				content = self.get_evohome_data()
				if isinstance(content, EvohomeClient):
					self.evohome_get_all(content)
				else:
					self.plugin.errorLog("[%s] Failed to retrieve Evohome data. Aborting update and trying again in %s seconds" % (time.asctime(), self.interval))
				self.evohome_timer_full = time.time()


			self.plugin.sleep(15)

	def initDevice(self, dev):
		indigo.server.log("Initializing thermostat device: %s" % dev.name)

		self.updateStateOnServer (dev, "temperatureInput1", 0)
		self.updateStateOnServer (dev, "humidityInput1", 0)
		self.updateStateOnServer (dev, "indoorTemperatureStatus", "")
		self.updateStateOnServer (dev, "macID", "")
		self.updateStateOnServer (dev, "maxHeatSetpoint", "")
		self.updateStateOnServer (dev, "minHeatSetpoint", "")
		self.updateStateOnServer (dev, "name", "")
		self.updateStateOnServer (dev, "nextTime", "")
		self.updateStateOnServer (dev, "outdoorHumidity", 0)
		self.updateStateOnServer (dev, "outdoorHumidityAvailable", False)
		self.updateStateOnServer (dev, "outdoorHumidityStatus", "")
		self.updateStateOnServer (dev, "scheduleCapable", False)
		#self.updateStateOnServer (dev, "scheduleCoolSp", 0)
		self.updateStateOnServer (dev, "scheduleHeatSp", 0)
		self.updateStateOnServer (dev, "setpointStatus", "")
		self.updateStateOnServer (dev, "thermostatAllowedModes", "")
		self.updateStateOnServer (dev, "thermostatMode", "")
		self.updateStateOnServer (dev, "thermostatModelType", "")
		self.updateStateOnServer (dev, "thermostatVersion", "")
		self.updateStateOnServer (dev, "lastUpdate", "")


	def evohome_initDevice(self):
		for dev in indigo.devices.iter("self.evohomeLocation"):
			if dev.enabled:
				indigo.server.log("Initializing thermostat device: %s" % dev.name)
				self.evohome_initLocation(dev)

	def evohome_initLocation(self, dev):
		content = self.get_evohome_data()
		self.updateStateOnServer(dev, "name", content.installation_info[0]['locationInfo']['name'])
		#for temperatureControlSystem in gateway["temperatureControlSystems"]:
		found = False
		for dev in indigo.devices.iter("self.evohomeController"):
			if dev.address == str(content.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['systemId']):
				found = True
				try: self.updateStateOnServer(dev, "modelType", content.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['modelType'])
				except: self.de (dev, "modelType")
				break
		if found == False:
			self.plugin.errorLog("[%s] Missing evohome Controller: [%s]" % (time.asctime(), str(content.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['systemId'])))

		if "dhw" in content.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['zones']:
			found = False
			for dev in indigo.devices.iter("self.evohomeDHW"):
				if dev.address == content.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]:
					found = True
					self.updateStateOnServer(dev, "name", "Domestic Hot Water")
					self.updateStateOnServer(dev, "modelType", "DHW")
					self.updateStateOnServer(dev, "zoneType", "DomesticHotWater")
					break
			if found == False:
				self.plugin.errorLog("[%s] Missing evohome DHW: [%s]" % (time.asctime(), content.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]))

		for zone in content.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]["zones"]:
			found = False
			for dev in indigo.devices.iter("self.evohomeZone"):
				if dev.address == zone["zoneId"]:
					found = True
					try: self.updateStateOnServer(dev, "name", zone["name"])
					except: self.de (dev, "name")
					try: self.updateStateOnServer(dev, "modelType", zone["modelType"])
					except: self.de (dev, "modelType")
					try: self.updateStateOnServer(dev, "zoneType", zone["zoneType"])
					except: self.de (dev, "zoneType")
					try: self.updateStateOnServer(dev, "maxHeatSetpoint", zone["setpointCapabilities"]["maxHeatSetpoint"])
					except: self.de (dev, "maxHeatSetpoint")
					try: self.updateStateOnServer(dev, "minHeatSetpoint", zone["setpointCapabilities"]["minHeatSetpoint"])
					except: self.de (dev, "minHeatSetpoint")
					break
			if found == False:
				self.plugin.errorLog("[%s] Missing evohome Zone: [%s] %s" % (time.asctime(), zone["zoneId"], zone["name"]))


	def evohome_get_all(self,content):
		for dev in indigo.devices.iter("self.evohomeLocation"):
			if dev.enabled:

				self.evohome_updateDevice(dev,content)


	def evohome_updateDevice(self, ldev,content):

		#for gateway in content["gateways"]:
		status=content.locations[0].status()
		for temperatureControlSystem in status['gateways'][0]["temperatureControlSystems"]:
			found = False
			for dev in indigo.devices.iter("self.evohomeController"):
				if dev.address == temperatureControlSystem["systemId"]:
					found = True
					dev.setErrorStateOnServer(None)
					try: self.updateStateOnServer(dev, "activeFaults", str(temperatureControlSystem["activeFaults"]))
					except: self.updateStateOnServer(dev, "activeFaults", "")
					try: self.updateStateOnServer(dev, "systemMode", temperatureControlSystem["systemModeStatus"]["mode"])
					except: self.de (dev, "systemMode")
					try: self.updateStateOnServer(dev, "systemModePermanent", bool(temperatureControlSystem["systemModeStatus"]["isPermanent"]))
					except: self.de (dev, "systemModePermanent")
					if dev.states["systemMode"] == 'AutoWithEco':
						try: self.updateStateOnServer(dev, "systemModeUntil", zone["systemModeStatus"]["timeUntil"][11:16])
						except: self.updateStateOnServer(dev, "systemModeUntil", "")
					elif dev.states["systemMode"] in ['Away', 'DayOff', 'Custom']:
						try: self.updateStateOnServer(dev, "systemModeUntil", zone["systemModeStatus"]["timeUntil"][0:10])
						except: self.updateStateOnServer(dev, "systemModeUntil", "")
					break
			if found == False:
				self.plugin.errorLog("[%s] Missing evohome Controller: [%s]" % (time.asctime(), temperatureControlSystem["systemId"]))
				dev.setErrorStateOnServer("controller error")

			if "dhw" in temperatureControlSystem:
				found = False
				for dev in indigo.devices.iter("self.evohomeDHW"):
					if dev.address == temperatureControlSystem["dhw"]["dhwId"]:
						found = True
						dev.setErrorStateOnServer(None)

						try: self.updateStateOnServer(dev, "activeFaults", str(temperatureControlSystem["dhw"]["activeFaults"]))
						except: self.updateStateOnServer(dev, "activeFaults", "")
						try:
							if temperatureControlSystem["dhw"]["temperatureStatus"]["isAvailable"] == True:
								self.updateStateOnServer(dev, "temperatureInput1", temperatureControlSystem["dhw"]["temperatureStatus"]["temperature"])
								try: self.updateStateOnServer(dev, "zoneMode", temperatureControlSystem["dhw"]["stateStatus"]["mode"])
								except: self.de (dev, "zoneMode")
								if temperatureControlSystem["dhw"]["stateStatus"]["state"] == 'Off':
									self.updateStateOnServer(dev, "zoneState", 'Off')
									self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.Off)
								elif temperatureControlSystem["dhw"]["stateStatus"]["state"] == 'On':
									self.updateStateOnServer(dev, "zoneState", 'On')
									if dev.states["zoneMode"] == 'FollowSchedule':
										self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramHeat)
									else:
										self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.Heat)
								try: self.updateStateOnServer(dev, "zoneModeUntil", temperatureControlSystem["dhw"]["stateStatus"]["until"][11:16])
								except: self.updateStateOnServer(dev, "zoneModeUntil", "")
								if dev.states["zoneState"] == "On":
									self.updateStateOnServer(dev, "hvacHeaterIsOn", 1)
								else:
									self.updateStateOnServer(dev, "hvacHeaterIsOn", 0)
							else:
								dev.setErrorStateOnServer("DHW error")
						except:
							self.de (dev, "temperatureStatus")
						break
				if found == False:
					self.plugin.errorLog("[%s] Missing evohome DHW: [%s]" % (time.asctime(), temperatureControlSystem["dhw"]["dhwId"]))
					dev.setErrorStateOnServer("DHW error")

			for zone in temperatureControlSystem["zones"]:
				found = False
				for dev in indigo.devices.iter("self.evohomeZone"):
					if dev.address == zone["zoneId"]:
						found = True
						dev.setErrorStateOnServer(None)

						try: self.updateStateOnServer(dev, "activeFaults", str(zone["activeFaults"]))
						except: self.updateStateOnServer(dev, "activeFaults", "")
						try:
							if zone["temperatureStatus"]["isAvailable"] == True:
								self.updateStateOnServer(dev, "temperatureInput1", zone["temperatureStatus"]["temperature"])
								try: self.updateStateOnServer(dev, "setpointHeat", zone["setpointStatus"]["targetHeatTemperature"])
								except: self.de (dev, "setpointHeat")
								try:
									self.updateStateOnServer(dev, "setpointMode", zone["setpointStatus"]["setpointMode"])
									if zone["setpointStatus"]["setpointMode"] in ['PermanentOverride', 'TemporaryOverride']:
										self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.Heat)
									elif zone["setpointStatus"]["setpointMode"] == 'FollowSchedule':
										self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramHeat)
								except:
									self.de (dev, "setpointMode")
								try: self.updateStateOnServer(dev, "setpointUntil", zone["setpointStatus"]["until"][11:16])
								except: self.updateStateOnServer(dev, "setpointUntil", "")
								if float(dev.states["temperatureInput1"]) < (dev.states["setpointHeat"]):
									self.updateStateOnServer(dev, "hvacHeaterIsOn", 1)
								else:
									self.updateStateOnServer(dev, "hvacHeaterIsOn", 0)
							else:
								dev.setErrorStateOnServer("zone error")
						except:
							self.de (dev, "temperatureStatus")
						break
				if found == False:
					self.plugin.errorLog("[%s] Missing evohome Zone: [%s] %s" % (time.asctime(), zone["zoneId"], zone["name"]))
					dev.setErrorStateOnServer("zone error")


	def de(self, dev, value):
		self.plugin.errorLog ("[%s] No value found for device: %s, field: %s" % (time.asctime(), dev.name, value))
		dev.setErrorStateOnServer("missing error")


	######################################################################################
	# Plugin Preferences
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			self.plugin.debugLog("[%s] Getting plugin preferences." % time.asctime())

			try:
				self.plugin.debug = self.plugin.pluginPrefs['showDebugInLog']
			except:
				self.plugin.debug = False

			try:
				self.UIChanges = self.plugin.pluginPrefs["UIChanges"]
			except:
				self.UIChanges = 'Temporary'

			try:
				if (self.evohome != self.plugin.pluginPrefs["evohome"]) or \
					(self.evohome_userID != self.plugin.pluginPrefs["evohome_UserID"]) or \
					(self.evohome_Password != self.plugin.pluginPrefs["evohome_Password"]):
					self.evohome = self.plugin.pluginPrefs["evohome"]
					self.evohome_UserID = self.plugin.pluginPrefs["evohome_UserID"]
					self.evohome_Password = self.plugin.pluginPrefs["evohome_Password"]
					if self.evohome == True:
						self.start_evohome()
			except:
				pass

			try:
				self.interval = self.plugin.pluginPrefs["interval"]
			except:
				self.interval = 30

			try:
				self.maxErrors = self.plugin.pluginPrefs["maxErrors"]
			except:
				self.maxErrors = 5

			indigo.server.log("[%s] Processed plugin preferences." % time.asctime())
			return True

	def actionControlThermostat(self, action, dev):

		if self.evohomeStatus == False:
			self.plugin.errorLog("[%s]: Error performing %s: %s" % (time.asctime(),action.thermostatAction,dev.name ))
			return
		client=self.get_evohome_data()

		if action.thermostatAction == indigo.kThermostatAction.SetHeatSetpoint and dev.deviceTypeId == 'evohomeZone':
			if ((float(action.actionValue) >= float(dev.states["minHeatSetpoint"])) and
				(float(action.actionValue) <= float(dev.states["maxHeatSetpoint"]))):
				indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, action.actionValue))

				#postdata = {'HeatSetpointValue':action.actionValue, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
				zone = client.locations[0]._gateways[0]._control_systems[0].zones[dev.states['name']]
				zone.set_temperature(action.actionValue)
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, action.actionValue, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))
		elif action.thermostatAction == indigo.kThermostatAction.IncreaseHeatSetpoint and dev.deviceTypeId == 'evohomeZone':
			newSetpoint = dev.states["setpointHeat"] + float(action.actionValue)
			if ((newSetpoint >= float(dev.states["minHeatSetpoint"])) and (newSetpoint <= float(dev.states["maxHeatSetpoint"]))):
				indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, newSetpoint))

				#postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
				zone = client.locations[0]._gateways[0]._control_systems[0].zones[dev.states['name']]
				zone.set_temperature(newSetpoint)
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))

		elif action.thermostatAction == indigo.kThermostatAction.DecreaseHeatSetpoint and dev.deviceTypeId == "evohomeZone":
			newSetpoint = dev.states["setpointHeat"] - float(action.actionValue)
			if ((newSetpoint >= float(dev.states["minHeatSetpoint"])) and (newSetpoint <= float(dev.states["maxHeatSetpoint"]))):
				indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, newSetpoint))

				#postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
				zone = client.locations[0]._gateways[0]._control_systems[0].zones[dev.states['name']]
				zone.set_temperature(newSetpoint)
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))


		elif action.thermostatAction == indigo.kThermostatAction.SetHvacMode:
			if action.actionMode == indigo.kHvacMode.Cool:
				indigo.server.log("[%s]: Honeywell Evohome does not support Cool mode" % dev.name)
			elif action.actionMode == indigo.kHvacMode.HeatCool:
				indigo.server.log("[%s]: Honeywell Evohome does not support Auto Heat/Cool mode" % dev.name)
			elif action.actionMode == indigo.kHvacMode.Heat:
				indigo.server.log("[%s]: Honeywell Evohome does not support Cool mode" % dev.name)
			elif action.actionMode == indigo.kHvacMode.Off:
				indigo.server.log("[%s]: Honeywell Evohome does not support HVAC off mode" % dev.name)
			elif action.actionMode == indigo.kHvacMode.ProgramHeatCool:
				indigo.server.log("[%s]: Honeywell Evohome does not support Auto Heat/Cool mode" % dev.name)
			elif action.actionMode == indigo.kHvacMode.ProgramCool:
				indigo.server.log("[%s]: Honeywell Evohome does not support Cool mode" % dev.name)
			elif action.actionMode == indigo.kHvacMode.ProgramHeat:
				indigo.server.log("[%s]: Honeywell Evohome does not support Cool mode" % dev.name)
			elif action.thermostatAction == indigo.kThermostatAction.SetFanMode:
					indigo.server.log("[%s]: Honeywell Evohome does not support Fan mode" % dev.name)

			elif action.thermostatAction in [indigo.kThermostatAction.RequestStatusAll,
				indigo.kThermostatAction.RequestMode,
				indigo.kThermostatAction.RequestEquipmentState,
				indigo.kThermostatAction.RequestTemperatures,
				indigo.kThermostatAction.RequestHumidities,
				indigo.kThermostatAction.RequestDeadbands,
				indigo.kThermostatAction.RequestSetpoints]:
				indigo.server.log("[%s]: Requesting Status..." % dev.name)


		if dev.deviceTypeId in ['evohomeDHW', 'evohomeZone', 'evohomeController']:
			self.evohome_get_all (client)
		return

	def evohome_actionCustomControl(self, pluginAction, action):
		if self.evohomeStatus == False:
			dev= indigo.devices[pluginAction.deviceId]
			self.plugin.errorLog("[%s]: Error performing %s: %s" % (time.asctime(),pluginAction.description, dev.name))

			return
		client=self.get_evohome_data()
		dev = indigo.devices[pluginAction.deviceId]

		if action == "actionSystemModeSet":
			setting = pluginAction.props.get("setting")
			if setting == "Auto1":
				#postdata = {'SystemMode':'Auto', 'Permanent':True, 'TimeUntil':None}
				client.set_status_normal()
				indigo.server.log("[%s]: Setting SystemMode to: Auto" % dev.name)
			elif setting == "AutoWithEco":
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 1 or Duration > 24:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (1-24)" % (time.asctime(), Duration))
						return
					else:
						#TODO Maybe bug here over duration when a day later
						until = (datetime.utcnow() + timedelta(hours=Duration))
						client.set_status_eco(until)
						indigo.server.log("[%s]: Setting SystemMode to: Auto with Eco until: %s" % (dev.name, until))

				else:
					client.set_status_eco()
					indigo.server.log("[%s]: Setting SystemMode to: Auto with Eco" % dev.name)
			elif setting in ['AutoWithReset', 'HeatingOff']:
				#postdata = {'SystemMode':setting, 'Permanent':True, 'TimeUntil':None}
				indigo.server.log("[%s]: Setting SystemMode to: %s" % (dev.name, setting))
			elif setting in ['Away', 'DayOff', 'Custom']:
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 1 or Duration > 99:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (1-99)" % (time.asctime(), Duration))
						return
					else:
						until = (datetime.utcnow() + timedelta(days=Duration))
						if setting=="Away":
							client.set_status_away(until=until)
						elif setting=="DayOff":
							client.set_status_dayoff(until=until)
						else:
							client.set_status_custom(until=until)
						indigo.server.log("[%s]: Setting SystemMode to: %s until: %s" % (dev.name, setting, until))
				else:
					if setting == "Away":
						client.set_status_away(until=None)
					elif setting == "DayOff":
						client.set_status_dayoff(until=None)
					else:
						client.set_status_custom(until=None)
					indigo.server.log("[%s]: Setting SystemMode to: %s" % (dev.name, setting))

		elif action == "actionZoneSetpointMode":
			setting = pluginAction.props.get("setting")
			zone=client.locations[0]._gateways[0]._control_systems[0].zones[dev.states['name']]
			if setting == 'FollowSchedule':
				#postdata = {'HeatSetpointValue':None, 'SetpointMode':'FollowSchedule', 'TimeUntil':None}
				zone.cancel_temp_override()
				indigo.server.log("[%s]: Setting Zone Setpoint Mode to: %s" % (dev.name, setting))
			elif setting == 'TemporaryOverride':
				Duration = int(pluginAction.props.get("Duration"))
				if Duration < 10 or Duration > 1440:
					self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
					return
				else:
					t1 = (datetime.utcnow() + timedelta(minutes=Duration))
					r1 = int(t1.strftime("%M"))
					t2 = t1.replace(minute=r1-(r1%10))
					until = t2

					#postdata = {'HeatSetpointValue':dev.states["setpointHeat"], 'SetpointMode':'TemporaryOverride', 'TimeUntil':until}
					zone.set_temperature(dev.states["setpointHeat"],until)
					indigo.server.log("[%s]: Setting Heat Setpoint to: %s until: %s" % (dev.name, setting, until))
			elif setting == 'PermanentOverride':
				#postdata = {'HeatSetpointValue':dev.states["setpointHeat"], 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
				zone.set_temperature(dev.states["setpointHeat"])
				indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, setting))


		elif action == "actionZoneSetpoint":
			setting = float(pluginAction.props.get("setting"))
			zone=client.locations[0]._gateways[0]._control_systems[0].zones[dev.states['name']]

			if ((setting >= float(dev.states["minHeatSetpoint"])) and (setting <= float(dev.states["maxHeatSetpoint"]))):
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 10 or Duration > 1440:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
						return
					else:
						t1 = (datetime.utcnow() + timedelta(minutes=Duration))
						r1 = int(t1.strftime("%M"))
						t2 = t1.replace(minute=r1-(r1%10))
						until = t2

						#postdata = {'HeatSetpointValue':setting, 'SetpointMode':'TemporaryOverride', 'TimeUntil':until}
						zone.set_temperature(setting, until)

						indigo.server.log("[%s]: Setting Heat Setpoint to: %s until: %s" % (dev.name, setting, until))
				else:
					#postdata = {'HeatSetpointValue':setting, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
					zone.set_temperature(setting)

					indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, setting))

			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, setting, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))
				return

		elif action == "actionZoneSetpointIncrease":
			setting = pluginAction.props.get("setting")
			zone=client.locations[0]._gateways[0]._control_systems[0].zones[dev.states['name']]

			newSetpoint = dev.states["setpointHeat"] + float(setting)
			if ((newSetpoint >= float(dev.states["minHeatSetpoint"])) and (newSetpoint <= float(dev.states["maxHeatSetpoint"]))):
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 10 or Duration > 1440:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
						return
					else:
						t1 = (datetime.utcnow() + timedelta(minutes=Duration))
						r1 = int(t1.strftime("%M"))
						t2 = t1.replace(minute=r1-(r1%10))
						until = t2

						#postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'TemporaryOverride', 'TimeUntil':until}
						zone.set_temperature(newSetpoint, until)

						indigo.server.log("[%s]: Setting Heat Setpoint to: %s until: %s" % (dev.name, newSetpoint, until))
				else:
					#postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
					zone.set_temperature(newSetpoint)

					indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, newSetpoint))
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))
				return

		elif action == "actionZoneSetpointDecrease":
			setting = pluginAction.props.get("setting")
			newSetpoint = dev.states["setpointHeat"] - float(setting)
			zone=client.locations[0]._gateways[0]._control_systems[0].zones[dev.states['name']]

			if ((newSetpoint >= float(dev.states["minHeatSetpoint"])) and (newSetpoint <= float(dev.states["maxHeatSetpoint"]))):
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 10 or Duration > 1440:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
						return
					else:
						t1 = (datetime.utcnow() + timedelta(minutes=Duration))
						r1 = int(t1.strftime("%M"))
						t2 = t1.replace(minute=r1-(r1%10))
						until = t2

						#postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'TemporaryOverride', 'TimeUntil':until}
						zone.set_temperature(newSetpoint, until)

						indigo.server.log("[%s]: Setting Heat Setpoint to: %s until: %s" % (dev.name, newSetpoint, until))
				else:
					#postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
					zone.set_temperature(newSetpoint)

					indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, newSetpoint))

			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))
				return

		elif action == "actionDHWMode":
			setting = pluginAction.props.get("setting")
			if setting == 'FollowSchedule':
				#postdata = {'state':None, 'mode':'FollowSchedule', 'untilTime':None}
				client.set_dhw_auto()
				indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s" % (dev.name, setting))
			# TODO I don't think a temporary overide without a state is required, may be removed

			elif setting == 'TemporaryOverride':
				Duration = int(pluginAction.props.get("Duration"))
				if Duration < 10 or Duration > 1440:
					self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
					return
				else:
					t1 = (datetime.utcnow() + timedelta(minutes=Duration))
					r1 = int(t1.strftime("%M"))
					t2 = t1.replace(minute=r1-(r1%10))
					until = t2
					#postdata = {'state':dev.states["zoneState"], 'mode':'TemporaryOverride', 'untilTime':until}

					indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s until: %s" % (dev.name, setting, until))
			elif setting == 'PermanentOverride':
				#postdata = {'state':dev.states["zoneState"], 'mode':'PermanentOverride', 'untilTime':None}
				indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s" % (dev.name, setting))


		elif action == "actionDHWState":
			setting = pluginAction.props.get("setting")
			if bool(pluginAction.props.get("Timing")) == False:
				Duration = int(pluginAction.props.get("Duration"))
				if Duration < 10 or Duration > 1440:
					self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
					return
				else:
					t1 = (datetime.utcnow() + timedelta(minutes=Duration))
					r1 = int(t1.strftime("%M"))
					t2 = t1.replace(minute=r1-(r1%10))
					until = t2
					#postdata = {'state':setting, 'mode':'TemporaryOverride', 'untilTime':until}
					if setting == 'On':
						client.set_dhw_on(until)
					else:
						client.set_dhw_off(until)

					indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s until: %s" % (dev.name, setting, until))
			else:
				#postdata = {'state':setting, 'mode':'PermanentOverride', 'untilTime':None}
				if setting == 'On':
					client.set_dhw_on()
				else:
					client.set_dhw_off()
				indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s" % (dev.name, setting))

		self.evohome_get_all(client)
		return


	def dumpEvohomeTCC(self):

		client = self.get_evohome_data()
		try:
			test = client.installation_info[0]['locationInfo']['name']
		except Exception as error:
			self.plugin.debugLog("No data returned by Evohome client")
			self.plugin.debugLog(error)

			return

		indigo.server.log("┌────────────────────────┬─────────────────┬─────────────────┬──────────────────┬───────────────────┐")
		indigo.server.log("│        Location        │    System ID    │    Device ID    │       Name       │       Model       │")
		indigo.server.log("├────────────────────────┼─────────────────┼─────────────────┼──────────────────┼───────────────────┤")
		indigo.server.log("│ %s │ %s │ %s │ %s │ %s │" % (client.installation_info[0]['locationInfo']['name'].ljust(22), str(
			client.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['systemId']).ljust(15),
											  "".ljust(15), "".ljust(16),
											  client.installation_info[0]['gateways'][0]['temperatureControlSystems'][
												  0]['modelType'].ljust(17)))
		for device in client.temperatures():
			if device['thermostat'] == 'DOMESTIC_HOT_WATER':
				indigo.server.log("│ %s │ %s │ %s │ %s │ %s │" % (client.installation_info[0]['locationInfo']['name'].ljust(22),
													  str(client.installation_info[0]['gateways'][0][
															  'temperatureControlSystems'][0]['systemId']).ljust(15),
													  device["id"].ljust(15), "".ljust(16),
													  "DomesticHotWater".ljust(17)))
			else:
				indigo.server.log("│ %s │ %s │ %s │ %s │ %s │" % (client.installation_info[0]['locationInfo']['name'].ljust(22),
													  str(client.installation_info[0]['gateways'][0][
															  'temperatureControlSystems'][0]['systemId']).ljust(15),
													  device["id"].ljust(15), device["name"].ljust(16),
													  "HeatingZone".ljust(17)))

		indigo.server.log("└────────────────────────┴─────────────────┴─────────────────┴──────────────────┴───────────────────┘")


	def createEvohomeDevices(self):
		devPropsZone = {'NumHumidityInputs':0, 'SupportsCoolSetpoint':False, 'SupportsHvacFanMode':False, 'ShowCoolHeatEquipmentStateUI':True}
		devPropsDHW = {'NumHumidityInputs':0, 'SupportsHeatSetpoint':False, 'SupportsCoolSetpoint':False, 'SupportsHvacFanMode':False, 'ShowCoolHeatEquipmentStateUI':True}

		client = self.get_evohome_data()

		found = False
		for dev in indigo.devices.iter("self.evohomeLocation"):
			if dev.address == client.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['systemId']:
				found = True
				break
		if found == False:
			dev = indigo.device.create(protocol=indigo.kProtocol.Plugin, address=str(client.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['systemId']), deviceTypeId='evohomeLocation', name='EVO Loc: ' + client.installation_info[0]['locationInfo']['name'])
			indigo.server.log("[%s] Created evohome Location: [%s] %s" % (time.asctime(), dev.address, dev.name))

		found = False
		for dev in indigo.devices.iter("self.evohomeController"):
			if dev.address == str(client.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['systemId']):
				found = True
				break
		if found == False:
			dev = indigo.device.create(protocol=indigo.kProtocol.Plugin, address=str(client.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['systemId']), deviceTypeId='evohomeController', name='EVO Con: ' + client.installation_info[0]['locationInfo']['name'] + ' [' + str(client.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['systemId']) + ']')
			indigo.server.log("[%s] Created evohome Controller: [%s] %s" % (time.asctime(), dev.address, dev.name))

		for device_instance in client.temperatures():
			if device_instance["thermostat"] == "DOMESTIC_HOT_WATER":
				found = False
				for dev in indigo.devices.iter("self.evohomeDHW"):
					if dev.address == str(device_instance["id"]):
						found = True
						break
				if found == False:
					dev = indigo.device.create(protocol=indigo.kProtocol.Plugin, address=str(device_instance["id"]), deviceTypeId='evohomeDHW', props=devPropsDHW, name='EVO DHW: ' + str(client.installation_info[0]['gateways'][0]['temperatureControlSystems'][0]['systemId']))
					indigo.server.log("[%s] Created evohome DHW: [%s] %s" % (time.asctime(), dev.address, dev.name))
			if device_instance["thermostat"] == "EMEA_ZONE":
				found = False
				for dev in indigo.devices.iter("self.evohomeZone"):
					if dev.address == str(device_instance["id"]):
						found = True
						break
				if found == False:
					dev = indigo.device.create(protocol=indigo.kProtocol.Plugin, address=str(device_instance["id"]), deviceTypeId='evohomeZone', props=devPropsZone, name='EVO Zone: ' + device_instance["name"])
					indigo.server.log("[%s] Created evohome Zone: [%s] %s" % (time.asctime(), dev.address, dev.name))

		self.evohome_initDevice()


	def updateStateOnServer(self, dev, state, value):
		if dev.states[state] != value:
			self.plugin.debugLog("Updating Device: %s, State: %s, Value: %s" % (dev.name, state, value))
			dev.updateStateOnServer(state, value)

	######################################################################################
	# UI Validation
	def validatePrefsConfigUi(self, valuesDict):
		self.plugin.debugLog("Vaidating Plugin Configuration")
		self.plugin.debugLog(valuesDict)
		errorsDict = indigo.Dict()

		try:
			client=EvohomeClient(valuesDict['evohome_UserID'],valuesDict['evohome_Password'])
		except Exception as error:
				self.plugin.errorLog("[%s] Cannot read Evohome data using new password/user name details" % time.asctime())
				self.plugin.debugLog(str(error))
				errorsDict["evohome_UserID"] = "Check Evohome Username and Password"
				errorsDict["evohome_Password"] = "Check Evohome Username and Password"
				errorsDict["showAlertText"] = "Unable to connect to the Evohome API with these credentials"
		if len(errorsDict) > 0:
			self.plugin.errorLog("\t Validation Errors")
			return (False, valuesDict, errorsDict)
		else:
			self.plugin.debugLog("\t Validation Succesful")
			self.needToGetPluginPrefs = True
			return (True, valuesDict)


	######################################################################################
	# Create client instance (refresh token is automatically used if valid so avoids rate limiting, and is refreshed if needed)

	def get_evohome_data(self):

		try:
			if self.plugin.pluginPrefs['refresh_token']=='':
				client = EvohomeClient(self.plugin.pluginPrefs['evohome_UserID'], self.plugin.pluginPrefs['evohome_Password'],)
			else:
				client = EvohomeClient(self.plugin.pluginPrefs['evohome_UserID'], self.plugin.pluginPrefs['evohome_Password'], refresh_token=self.plugin.pluginPrefs['refresh_token'], access_token=self.plugin.pluginPrefs['access_token'], access_token_expires=datetime.strptime(self.plugin.pluginPrefs['access_token_expires'],"%Y-%m-%d %H:%M:%S.%f"))
		except Exception as error:
				self.evohomeStatus = False
				self.plugin.errorLog("[%s] Cannot read Evohome data " % time.asctime())
				self.plugin.debugLog(str(error))
				return

		self.plugin.pluginPrefs['refresh_token']=client.refresh_token
		self.plugin.pluginPrefs['access_token']=client.access_token
		self.plugin.pluginPrefs['access_token_expires']=str(client.access_token_expires)
		self.plugin.debugLog("[%s] Authenticated to Evohome API (refresh call) with token expiring %s." % ( time.asctime(),client.access_token_expires))
		self.evohomeStatus = True

		return client
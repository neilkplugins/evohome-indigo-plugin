#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014-2016, SSI. All rights reserved.

import indigo

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
		self.WiFi = False
		self.UserID = None
		self.Password = None
		self.UIChanges = None
		self.WiFiStatus = False
		self.timer_refresh = None 	# timestamp of last token refresh
		self.timer_events = None 	# timestamp of last event poll 
		self.timer_full = None 		# timestamp of last device fetch
		self.timer_lasttry = None 	# timestamp of last token attempt
		self.token_refresh = None
		self.evohome = False
		self.evohome_UserID = None
		self.evohome_Password = None
		self.evohomeStatus = False
		self.evohome_timer_refresh = None
		self.evohome_timer_full = None
		self.evohome_timer_lasttry = None
		self.evohome_token_refresh = None
		self.TCCServer = None
		self.deviceList = []
		self.eventCurrentId = None
		self.eventLatestId = None
		self.errorCount = 0
		self.evohome_errorCount = 0
		#self.myTCC = TCC()
		self.myEvohomeTCC = None
		self.HQ = {}
		self.interval = None
		self.maxErrors = None
		self.access_token='5B26C218-B798-46E9-8C96-0E8E5E7C91B3'

	def __del__(self):
		pass

	def startup(self):
		self.plugin.debugLog("Evohome Plugin Startup...")

		logging.getLogger("requests").setLevel(logging.WARNING)

		self.closedPrefsConfigUi(None, None)
		#self.plugin.updater.checkVersionPoll()

		#if self.WiFi == True:
		#	self.start_WiFi()
		#if self.evohome == True:
		#	self.start_evohome()

	def deviceStartComm(self, dev):
		self.plugin.debugLog("Starting device: %s" % dev.name)
		if dev.id not in self.deviceList:
			self.deviceList.append(dev.id)
			dev.stateListOrDisplayStateIdChanged()

		if self.WiFi == True and dev.deviceTypeId == 'HoneywellThermostat':
			self.plugin.debugLog("[%s] Thermostat: %s, Enabled: %s" % (time.asctime(), dev.name, dev.enabled))
			self.initDevice (dev)
			self.getDevice (dev)

	def deviceStopComm(self, device):
		self.plugin.debugLog("Stopping device: %s" % device.name)
		if device.id in self.deviceList:
			self.deviceList.remove(device.id)

	def restartPlugin(self):
		HoneywellPlug = indigo.server.getPlugin("com.ssi.indigoplugin.Honeywell")
		HoneywellPlug.restart (waitUntilDone = True)
		exit()



	def start_evohome(self):
		# url = "mytotalconnectcomfort.com/WebApi/api/Session"
		#
		# payload = 'username='+self.evohome_UserID+'&password='+self.evohome_Password+'&ApplicationId=91db1612-73fd-4500-91b2-e63b069b185c'
		# headers = {
		# 	'Content-type': 'application/x-www-form-urlencoded'
		# }
		#
		# response = requests.request("POST", url, headers=headers, data=payload)
		# indigo.server.log(response)
		try:
			self.evohomeStatus = True
			#self.evohomeStatus = self.myEvohomeTCC.getTokens (self.plugin.pluginPrefs["TCCServer"], self.evohome_UserID, self.evohome_Password, "evohome")
		except:
			self.evohomeStatus = False

		self.evohome_timer_lasttry = time.time()

		if self.evohomeStatus == True:
			#indigo.server.log("[%s] Authenticated to TCC EMEA API." % time.asctime())
			self.evohome_timer_refresh = time.time()
			self.evohome_timer_full = time.time()
			self.evohome_initDevice ()
			self.evohome_get_all ()
		else:
			self.plugin.errorLog("[%s] Error: Cannot authenticate to TCC EMEA API.  Retrying in 60..." % time.asctime())
			

	######################################################################################
	# Concurrent Thread Start
	def runConcurrentThread(self):
		self.plugin.debugLog("Running Concurrent Thread")

		while self.plugin.StopThread == False:



			# if self.evohome == True:
			# 	#if self.c == True:
			# 	if True == True:
			# 		if (time.time() - self.evohome_timer_full) > int(self.interval):
			# 			self.evohome_get_all()
			# 			self.evohome_timer_full = time.time()
			# 		# refresh token
			# 		if (time.time() - self.evohome_timer_refresh) > (self.myEvohomeTCC.token_life - 120):
			# 			self.evohome_token_refresh = self.myEvohomeTCC.refreshTokens (self.plugin.pluginPrefs["TCCServer"])
			# 			if self.evohome_token_refresh:
			# 				self.evohome_timer_refresh = time.time()
			# 				self.plugin.debugLog("[%s] Evohome Token Refresh" % time.asctime())
			# 			else:
			# 				self.evohome_errorCount = self.evohome_errorCount + 1
			# 				self.plugin.errorLog("[%s] Error: Cannot refresh authentication token" % time.asctime())
			# 				self.evohomeStatus = False
			# 				self.evohome_timer_lasttry = time.time()
			# 	if (time.time() - self.evohome_timer_lasttry) > errorTimer and (self.evohomeStatus == False or self.evohome_errorCount >= int(self.maxErrors)):
			self.start_evohome()

			self.plugin.sleep(1)

	def initDevice(self, dev):
		indigo.server.log("Initializing thermostat device: %s" % dev.name)

		self.updateStateOnServer (dev, "temperatureInput1", 0)
		self.updateStateOnServer (dev, "humidityInput1", 0)
		self.updateStateOnServer (dev, "fanAllowedModes", "")
		self.updateStateOnServer (dev, "fanMode", "")
		self.updateStateOnServer (dev, "fanRunning", False)
		self.updateStateOnServer (dev, "indoorHumidityStatus", "")
		self.updateStateOnServer (dev, "indoorTemperatureStatus", "")
		self.updateStateOnServer (dev, "macID", "")
		self.updateStateOnServer (dev, "maxCoolSetpoint", "")
		self.updateStateOnServer (dev, "maxHeatSetpoint", "")
		self.updateStateOnServer (dev, "minCoolSetpoint", "")
		self.updateStateOnServer (dev, "minHeatSetpoint", "")
		self.updateStateOnServer (dev, "name", "")
		self.updateStateOnServer (dev, "nextTime", "")
		self.updateStateOnServer (dev, "outdoorHumidity", 0)
		self.updateStateOnServer (dev, "outdoorHumidityAvailable", False)
		self.updateStateOnServer (dev, "outdoorHumidityStatus", "")
		self.updateStateOnServer (dev, "scheduleCapable", False)
		self.updateStateOnServer (dev, "scheduleCoolSp", 0)
		self.updateStateOnServer (dev, "scheduleHeatSp", 0)
		self.updateStateOnServer (dev, "setpointStatus", "")
		self.updateStateOnServer (dev, "thermostatAllowedModes", "")
		self.updateStateOnServer (dev, "thermostatMode", "")
		self.updateStateOnServer (dev, "thermostatModelType", "")
		self.updateStateOnServer (dev, "thermostatVersion", "")
		self.updateStateOnServer (dev, "lastUpdate", "")

		self.HQ[dev.id] = {'SetPoint':0, 'OperationMode':0, 'FanMode':0}

	def evohome_initDevice(self):
		for dev in indigo.devices.iter("self.evohomeLocation"):
			if dev.enabled:
				url = self.TCCServer + 'WebAPI/emea/api/v1/location/' + dev.address + '/installationInfo?includeTemperatureControlSystems=True'

				headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.access_token}
				try:
					response = requests.get(url, headers=headers)
				except requests.exceptions.ConnectionError as e:
					self.plugin.errorLog("[%s] Connection Error for: %s" % (time.asctime(), dev.name))
					return False
				if response.status_code == 200:
					indigo.server.log("Initializing thermostat device: %s" % dev.name)
					content = json.loads (response.content)
					self.evohome_initLocation(dev, content)
				else:
					self.plugin.errorLog("[%s] Cannot read device data for: %s" % (time.asctime(), dev.name))
					return False

	def evohome_initLocation(self, dev, content):
		self.updateStateOnServer(dev, "name", content["locationInfo"]["name"])
		for gateway in content["gateways"]:
			for temperatureControlSystem in gateway["temperatureControlSystems"]:
				found = False
				for dev in indigo.devices.iter("self.evohomeController"):
					if dev.address == temperatureControlSystem["systemId"]:
						found = True
						try: self.updateStateOnServer(dev, "modelType", temperatureControlSystem["modelType"])
						except: self.de (dev, "modelType")
						break
				if found == False:
					self.plugin.errorLog("[%s] Missing evohome Controller: [%s]" % (time.asctime(), temperatureControlSystem["systemId"]))

				if "dhw" in temperatureControlSystem:
					found = False
					for dev in indigo.devices.iter("self.evohomeDHW"):
						if dev.address == temperatureControlSystem["dhw"]["dhwId"]:
							found = True
							self.updateStateOnServer(dev, "name", "Domestic Hot Water")
							self.updateStateOnServer(dev, "modelType", "DHW")
							self.updateStateOnServer(dev, "zoneType", "DomesticHotWater")
							break
					if found == False:
						self.plugin.errorLog("[%s] Missing evohome DHW: [%s]" % (time.asctime(), temperatureControlSystem["dhw"]["dhwId"]))

				for zone in temperatureControlSystem["zones"]:
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
	


	def get_eventLatestId(self):
		url = self.TCCServer + 'WebAPI/api/eventLatestId'
		headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.myTCC.access_token}
		response = requests.get(url, headers=headers)
		if response.status_code == 200:
			content = json.loads (response.content)
			self.eventLatestId = content["id"]
			return (True)
		else:
			self.plugin.errorLog ("[%s] Error: %s, Cannot get eventLatestId from Honeywell TCC Web API." % (time.asctime(), response.status_code))
			return (False)

	def getEvents(self):
		if self.eventLatestId > self.eventCurrentId:
			self.plugin.debugLog("eventLatestId: %s, eventCurrentId: %s" % (self.eventLatestId, self.eventCurrentId))
			url = self.TCCServer + 'WebAPI/api/events?eventId=' + str(self.eventCurrentId) + '&numberOfEvents=' + str(self.eventLatestId - self.eventCurrentId)
			headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.myTCC.access_token}
			response = requests.get(url, headers=headers)

			if response.status_code == 200:
				if time.localtime().tm_isdst == 0:
					tz_offset = time.timezone
				elif time.localtime().tm_isdst == 1:
					tz_offset = time.altzone
				self.eventCurrentId = self.eventLatestId
				content = json.loads(response.content)
				for event in content:
					eventData = json.loads(event["json"])
					eventType = event["type"]
					eventId = event["id"]
					deviceId = eventData["deviceId"]
					targetDev = None
					for dev in indigo.devices.iter("self.HoneywellThermostat"):
						if dev.enabled:
							if int(deviceId) == int(dev.address):
								targetDev = dev
								break
					if (targetDev != None) and (targetDev.id in self.deviceList):
						self.plugin.debugLog ("eventType: %s, eventId: %s, deviceId: %s, device: %s" % (eventType, eventId, deviceId, dev.name))
						if eventType == "UIDataEvent":
							self.plugin.debugLog("%s" % eventData)
							created = time.mktime(time.strptime(eventData["created"][:-2], "%Y-%m-%dT%H:%M:%S.%f")) - tz_offset
							self.updateUIDataEvent (dev, eventData)
						elif eventType == "EquipmentStatusEvent":
							self.plugin.debugLog("%s" % eventData)
							self.updateEquipmentStatusEvent (dev, eventData)
						elif eventType == "ConnectionStatusEvent":
							self.plugin.debugLog("%s" % eventData)
							self.updateConnectionStatusEvent (dev, eventData)
						elif eventType == "FanSwitchSettingsEvent":
							self.plugin.debugLog("%s" % eventData)
							created = time.mktime(time.strptime(eventData["created"], "%Y-%m-%dT%H:%M:%SZ")) - tz_offset
							self.updateFanSwitchSettingsEvent (dev, eventData)
						else:
							self.plugin.debugLog("%s" % eventData)

			else:
				self.plugin.errorLog("Error: %s, Cannot get events from Honeywell TCC Web API." % response.status_code)

	def get_all(self):
		for dev in indigo.devices.iter("self.HoneywellThermostat"):
			if dev.enabled:
				if self.getDevice(dev) == False:
					self.plugin.errorLog ("[%s] Failed to retrieve thermostat status for: %s" % (time.asctime(), dev.name))
					self.errorCount = self.errorCount + 1
					dev.setErrorStateOnServer("error")
				else:
					self.errorCount = 0

	def getDevice(self, dev):
		url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '?allData=True'
		headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.myTCC.access_token}
		try:
			response = requests.get(url, headers=headers, timeout=reqTimeout)
		except requests.exceptions.ConnectionError as e:
			self.plugin.debugLog("[%s] Connection Error for: %s" % (time.asctime(), dev.name))
			return False
		except requests.exceptions.Timeout as e:
			self.plugin.debugLog("[%s] Timeout Error for: %s" % (time.asctime(), dev.name))
			return False
		except requests.exceptions.ReadTimeout as e:
			self.plugin.debugLog("[%s] Read Timeout Error for: %s" % (time.asctime(), dev.name))
			return False
		except Exception as e:
			self.plugin.debugLog("[%s] Error for: %s, %s" % (time.asctime(), dev.name, e.message))
			return False

		if response.status_code == 200:
			content = json.loads (response.content)
			self.updateDevice (dev, content)
			return True
		else:
			self.plugin.debugLog("[%s] Cannot read device data for: %s" % (time.asctime(), dev.name))
			return False

	def evohome_get_all(self):
		for dev in indigo.devices.iter("self.evohomeLocation"):
			if dev.enabled:
				if self.evohome_getDevice(dev) == False:
					self.plugin.errorLog ("[%s] Failed to retrieve thermostat status for: %s" % (time.asctime(), dev.name))
					self.evohome_errorCount = self.evohome_errorCount + 1
					dev.setErrorStateOnServer("error")
				else:
					self.evohome_errorCount = 0

	def evohome_getDevice(self, dev):
		url = self.TCCServer + 'WebAPI/emea/api/v1/location/' + dev.address + '/status?includeTemperatureControlSystems=True'
		headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.access_token}
		try:
			response = requests.get(url, headers=headers, timeout=reqTimeout)
		except requests.exceptions.ConnectionError as e:
			self.plugin.errorLog("[%s] Connection Error for: %s" % (time.asctime(), dev.name))
			return False
		except requests.exceptions.Timeout as e:
			self.plugin.debugLog("[%s] Timeout Error for: %s" % (time.asctime(), dev.name))
			return False
		except requests.exceptions.ReadTimeout as e:
			self.plugin.debugLog("[%s] Read Timeout Error for: %s" % (time.asctime(), dev.name))
			return False
		except Exception as e:
			self.plugin.debugLog("[%s] Error for: %s, %s" % (time.asctime(), dev.name, e.message))
			return False

		if response.status_code == 200:
			content = json.loads (response.content)
			self.evohome_updateDevice (dev, content)
			return True
		else:
			self.plugin.errorLog("[%s] Cannot read device data for: %s" % (time.asctime(), dev.name))
			return False

	def triggerEvents(self, dev):
		url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/tracking'
		headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.myTCC.access_token}
		postdata = {'enabled':'true'}
		response = requests.put(url, data=json.dumps(postdata), headers=headers)
		if response.status_code != 200:
			self.plugin.errorLog ("[%s] Error: %s, Cannot start event stream." % (time.asctime(), response.status_code))

	def updateDevice(self, dev, content):
		try:
			if content["isAlive"] == False:
				self.plugin.errorLog("[%s] Error: Lost connection with device: %s" % (time.asctime(), dev.name))
				dev.setErrorStateOnServer("error")
			else:
				self.updateStateOnServer(dev, "lastUpdate", str(time.time()))

				try: self.updateStateOnServer(dev, "macID", content["macID"])
				except: self.de (dev, "macID")
				try: self.updateStateOnServer(dev, "name", content["name"])
				except: self.de (dev, "name")
				try: self.updateStateOnServer(dev, "thermostatModelType", content["thermostatModelType"])
				except: self.de (dev, "thermostatModelType")
				try: self.updateStateOnServer(dev, "thermostatVersion", content["thermostatVersion"])
				except: self.de (dev, "thermostatVersion")

				try:
					if content["thermostat"]["equipmentOutputStatus"] == "Heating":
						self.updateStateOnServer(dev, "hvacHeaterIsOn", 1)
						self.updateStateOnServer(dev, "hvacCoolerIsOn", 0)
					elif content["thermostat"]["equipmentOutputStatus"] == "Cooling":
						self.updateStateOnServer(dev, "hvacHeaterIsOn", 0)
						self.updateStateOnServer(dev, "hvacCoolerIsOn", 1)
					elif content["thermostat"]["equipmentOutputStatus"] == "Off":
						self.updateStateOnServer(dev, "hvacHeaterIsOn", 0)
						self.updateStateOnServer(dev, "hvacCoolerIsOn", 0)
				except:
					pass
					#self.de (dev, "equipmentOutputStatus")



				try: self.updateStateOnServer(dev, "thermostatAllowedModes", ','.join(content["thermostat"]["allowedModes"]))
				except: self.de (dev, "thermostatAllowedModes")
				try: self.updateStateOnServer(dev, "thermostatMode", content["thermostat"]["changeableValues"]["mode"])
				except: self.de (dev, "thermostatMode")

				if "Heat" in dev.states["thermostatAllowedModes"]:
					try: self.updateStateOnServer(dev, "setpointHeat", content["thermostat"]["changeableValues"]["heatSetpoint"]["value"])
					except: self.de (dev, "setpointHeat")
				if "Cool" in dev.states["thermostatAllowedModes"]:
					try: self.updateStateOnServer(dev, "setpointCool", content["thermostat"]["changeableValues"]["coolSetpoint"]["value"])
					except: self.de (dev, "setpointCool")

				try:
					self.updateStateOnServer(dev, "setpointStatus", content["thermostat"]["changeableValues"]["status"])
					self.updateStateOnServer(dev, "nextTime", content["thermostat"]["changeableValues"]["nextTime"])
				except:
					if dev.states["thermostatMode"] == "Heat":
						self.updateStateOnServer(dev, "setpointStatus", content["thermostat"]["changeableValues"]["heatSetpoint"]["status"])
						self.updateStateOnServer(dev, "nextTime", content["thermostat"]["changeableValues"]["heatSetpoint"]["nextTime"])
					elif dev.states["thermostatMode"] == "Cool":
						self.updateStateOnServer(dev, "setpointStatus", content["thermostat"]["changeableValues"]["coolSetpoint"]["status"])
						self.updateStateOnServer(dev, "nextTime", content["thermostat"]["changeableValues"]["coolSetpoint"]["nextTime"])
					else:
						self.updateStateOnServer(dev, "setpointStatus", "")
						self.updateStateOnServer(dev, "nextTime", "")

				try:
					if dev.states["thermostatMode"] == "Heat":
						if dev.states["setpointStatus"] == "Scheduled":
							self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramHeat)
						else:
							self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.Heat)
					elif dev.states["thermostatMode"] == "Cool":
						if dev.states["setpointStatus"] == "Scheduled":
							self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramCool)
						else:
							self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.Cool)
					elif dev.states["thermostatMode"] == "AutoHeat":
						self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramHeat)
					elif dev.states["thermostatMode"] == "AutoCool":
						self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramCool)
					elif dev.states["thermostatMode"] == "Off":
						self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.Off)
				except:
					self.de (dev, "thermostatMode")

				try:
					if content["thermostat"]["indoorTemperatureStatus"] == "Measured":
						self.updateStateOnServer(dev, "temperatureInput1", content["thermostat"]["indoorTemperature"])
					self.updateStateOnServer(dev, "indoorTemperatureStatus", content["thermostat"]["indoorTemperatureStatus"])	
				except:
					self.de (dev, "indoorTermperatureStatus")

				try:
					if content["thermostat"]["indoorHumidityStatus"] == "Measured":
						self.updateStateOnServer(dev, "humidityInput1", content["thermostat"]["indoorHumidity"])
					self.updateStateOnServer(dev, "indoorHumidityStatus", content["thermostat"]["indoorHumidityStatus"])	
				except:
					self.de (dev, "indoorHumidityStatus")

				try:
					if content["fan"]["changeableValues"]["mode"] in ["Auto", "Circulate"]:
						self.updateStateOnServer(dev, "hvacFanMode", indigo.kFanMode.Auto)
					elif content["fan"]["changeableValues"]["mode"] == "On":
						self.updateStateOnServer(dev, "hvacFanMode", indigo.kFanMode.AlwaysOn)
					self.updateStateOnServer(dev, "fanAllowedModes", ','.join(content["fan"]["allowedModes"]))			
					self.updateStateOnServer(dev, "fanMode", content["fan"]["changeableValues"]["mode"])
					self.updateStateOnServer(dev, "fanRunning", content["fan"]["fanRunning"])
				except:
					pass
					#self.de (dev, "fanMode")

				try: self.updateStateOnServer(dev, "maxCoolSetpoint", content["thermostat"]["maxCoolSetpoint"])
				except: self.de (dev, "maxCoolSetpoint")
				try: self.updateStateOnServer(dev, "maxHeatSetpoint", content["thermostat"]["maxHeatSetpoint"])
				except: self.de (dev, "maxHeatSetpoint")
				try: self.updateStateOnServer(dev, "minCoolSetpoint", content["thermostat"]["minCoolSetpoint"])
				except: self.de (dev, "minCoolSetpoint")
				try: self.updateStateOnServer(dev, "minHeatSetpoint", content["thermostat"]["minHeatSetpoint"])
				except: self.de (dev, "minHeatSetpoint")

				try: self.updateStateOnServer(dev, "outdoorHumidity", content["thermostat"]["outdoorHumidity"])
				except: self.de (dev, "outdoorHumidity")
				try: self.updateStateOnServer(dev, "outdoorHumidityStatus", content["thermostat"]["outdoorHumidityStatus"])
				except: self.de (dev, "outdoorHumidityStatus")
				try: self.updateStateOnServer(dev, "outdoorHumidityAvailable", content["thermostat"]["outdootHumidityAvailable"])
				except: self.de (dev, "outdoorHumidityAvailable")

				try: self.updateStateOnServer(dev, "outdoorTemperature", content["thermostat"]["outdoorTemperature"])
				except: self.de (dev, "outdoorTemperature")
				try: self.updateStateOnServer(dev, "outdoorTemperatureStatus", content["thermostat"]["outdoorTemperatureStatus"])
				except: self.de (dev, "outdoorTemperatureStatus")
				try: self.updateStateOnServer(dev, "outdoorTemperatureAvailable", content["thermostat"]["outdoorTemperatureAvailable"])
				except: self.de (dev, "outdoorTemperatureAvailable")

				try: self.updateStateOnServer(dev, "scheduleCapable", content["thermostat"]["scheduleCapable"])
				except: self.de (dev, "scheduleCapable")
				try: self.updateStateOnServer(dev, "scheduleCoolSp", content["thermostat"]["scheduleCoolSp"])
				except: self.de (dev, "scheduleCoolSp")
				try: self.updateStateOnServer(dev, "scheduleHeatSp", content["thermostat"]["scheduleHeatSp"])
				except: self.de (dev, "scheduleHeatSp")


		except:
			pass

	def evohome_updateDevice(self, ldev, content):
		#indigo.server.log("%s" % content)
		for gateway in content["gateways"]:
			for temperatureControlSystem in gateway["temperatureControlSystems"]:
				found = False
				for dev in indigo.devices.iter("self.evohomeController"):
					if dev.address == temperatureControlSystem["systemId"]:
						found = True
						try: self.updateStateOnServer(dev, "activeFaults", temperatureControlSystem["activeFaults"])
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

				if "dhw" in temperatureControlSystem:
					found = False
					for dev in indigo.devices.iter("self.evohomeDHW"):
						if dev.address == temperatureControlSystem["dhw"]["dhwId"]:
							found = True
							try: self.updateStateOnServer(dev, "activeFaults", temperatureControlSystem["dhw"]["activeFaults"])
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
									dev.setErrorStateOnServer("error")
							except:
								self.de (dev, "temperatureStatus")
							break
					if found == False:
						self.plugin.errorLog("[%s] Missing evohome DHW: [%s]" % (time.asctime(), temperatureControlSystem["dhw"]["dhwId"]))

				for zone in temperatureControlSystem["zones"]:
					found = False
					for dev in indigo.devices.iter("self.evohomeZone"):
						if dev.address == zone["zoneId"]:
							found = True
							try: self.updateStateOnServer(dev, "activeFaults", zone["activeFaults"])
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
									dev.setErrorStateOnServer("error")
							except:
								self.de (dev, "temperatureStatus")
							break
					if found == False:
						self.plugin.errorLog("[%s] Missing evohome Zone: [%s] %s" % (time.asctime(), zone["zoneId"], zone["name"]))


	def updateUIDataEvent(self, dev, content):
		if self.HQ[dev.id]['OperationMode'] == 0:
			try:
				if content["systemSwitchPosition"] == "Heat":
					if content["statusHeat"] == "Scheduled":
						self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramHeat)
					else:
						self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.Heat)
				elif content["systemSwitchPosition"] == "Cool":
					if content["statusCool"] == "Scheduled":
						self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramCool)
					else:
						self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.Cool)
				elif content["systemSwitchPosition"] == "AutoHeat":
					self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramHeat)
				elif content["systemSwitchPosition"] == "AutoCool":
					self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.ProgramCool)
				elif content["systemSwitchPosition"] == "Off":
					self.updateStateOnServer(dev, "hvacOperationMode", indigo.kHvacMode.Off)
			except:
				pass

			try: self.updateStateOnServer(dev, "thermostatMode", content["systemSwitchPosition"])
			except: pass
		else:
			self.plugin.debugLog ("[%s] Ignoring OperationMode update for device: %s, [Q=%s]" % (time.asctime(), dev.name, self.HQ[dev.id]['OperationMode']))
			self.HQ[dev.id]['OperationMode'] = self.HQ[dev.id]['OperationMode'] - 1

		if dev.states["thermostatMode"] == "Heat":
			try: self.updateStateOnServer(dev, "nextTime", content["heatNextTime"])
			except: pass
			try: self.updateStateOnServer(dev, "setpointStatus", content["statusHeat"])
			except: pass
		elif dev.states["thermostatMode"] == "Cool":
			try: self.updateStateOnServer(dev, "nextTime", content["coolNextTime"])
			except: pass
			try: self.updateStateOnServer (dev, "setpointStatus", content["statusCool"])
			except: pass

		if self.HQ[dev.id]['SetPoint'] == 0:
			try: self.updateStateOnServer(dev, "setpointCool", content["coolSetpoint"])
			except: pass
			try: self.updateStateOnServer(dev, "setpointHeat", content["heatSetpoint"])
			except: pass
		else:
			self.plugin.debugLog ("[%s] Ignoring SetPoint update for device: %s, [Q=%s]" % (time.asctime(), dev.name, self.HQ[dev.id]['SetPoint']))
			self.HQ[dev.id]['SetPoint'] = self.HQ[dev.id]['SetPoint'] - 1

		try: self.updateStateOnServer(dev, "temperatureInput1", content["displayedTemp"])
		except: pass
		try: self.updateStateOnServer(dev, "indoorTemperatureStatus", content["displayedTempStatus"])
		except: pass

		try: self.updateStateOnServer(dev, "humidityInput1", content["indoorHumidity"])
		except: pass
		try: self.updateStateOnServer(dev, "indoorHumidityStatus", content["indoorHumidityStatus"])
		except: pass

		try: self.updateStateOnServer(dev, "maxCoolSetpoint", content["coolUpperSetpointLimit"])
		except: pass
		try: self.updateStateOnServer(dev, "maxHeatSetpoint", content["heatUpperSetpointLimit"])
		except: pass
		try: self.updateStateOnServer(dev, "minCoolSetpoint", content["coolLowerSetpointLimit"])
		except: pass
		try: self.updateStateOnServer(dev, "minHeatSetpoint", content["heatLowerSetpointLimit"])
		except: pass

		try: self.updateStateOnServer(dev, "outdoorTemperature", content["outdoorTemp"])
		except: pass
		try: self.updateStateOnServer(dev, "outdoorTemperatureStatus", content["outdoorTempStatus"])
		except: pass
		try: self.updateStateOnServer(dev, "outdoorHumidity", content["outdoorHumidity"])
		except: pass
		try: self.updateStateOnServer(dev, "outdoorHumidityStatus", content["outdoorHumidityStatus"])
		except: pass

		try: self.updateStateOnServer(dev, "scheduleCapable", content["scheduleCapable"])
		except: pass
		try: self.updateStateOnServer(dev, "scheduleCoolSp", content["scheduleCoolSetpoint"])
		except: pass
		try: self.updateStateOnServer(dev, "scheduleHeatSp", content["scheduleHeatSetpoint"])
		except: pass

	def updateEquipmentStatusEvent(self, dev, content):
		try:
			if content["equipmentStatus"] == "Heating":
				self.updateStateOnServer(dev, "hvacHeaterIsOn", 1)
				self.updateStateOnServer(dev, "hvacCoolerIsOn", 0)
			elif content["equipmentStatus"] == "Cooling":
				self.updateStateOnServer(dev, "hvacHeaterIsOn", 0)
				self.updateStateOnServer(dev, "hvacCoolerIsOn", 1)
			elif content["equipmentStatus"] == "Off":
				self.updateStateOnServer(dev, "hvacHeaterIsOn", 0)
				self.updateStateOnServer(dev, "hvacCoolerIsOn", 0)
		except:
			pass

		try:
			if content["fanStatus"] == "On":
				self.updateStateOnServer(dev, "fanRunning", True)
			elif content["fanStatus"] == "Off":
				self.updateStateOnServer(dev, "fanRunning", False)
		except:
			pass

	def updateConnectionStatusEvent(self, dev, content):
		try:
			self.plugin.debugLog("[%s] Connection Status: %s for device %s" (time.asctime(), content["connectionStatus"], dev.name))
			if content["connectionStatus"] == "ConnectionLost":
				self.plugin.errorLog("[%s] Error: Lost connection with device: %s" % (time.asctime(), dev.name))
				dev.setErrorStateOnServer("error")
		except:
			pass

	def updateFanSwitchSettingsEvent(self, dev, content):
		if self.HQ[dev.id]['FanMode'] == 0:
			try:
				if content["fanMode"] in ["Auto", "Circulate"]:
					self.updateStateOnServer(dev, "hvacFanMode", indigo.kFanMode.Auto)
				elif content["fanMode"] == "On":
					self.updateStateOnServer(dev, "hvacFanMode", indigo.kFanMode.AlwaysOn)
				self.updateStateOnServer(dev, "fanMode", content["fanMode"])
			except:
				pass
		else:
			self.plugin.debugLog ("[%s] Ignoring FanMode update for device: %s, [Q=%s]" % (time.asctime(), dev.name, self.HQ[dev.id]['FanMode']))
			self.HQ[dev.id]['FanMode'] = self.HQ[dev.id]['FanMode'] - 1


	def de (self, dev, value):
		self.plugin.errorLog ("[%s] No value found for device: %s, field: %s" % (time.asctime(), dev.name, value))


	######################################################################################
	# Plugin Preferences
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			self.plugin.debugLog("[%s] Getting plugin preferences." % time.asctime())

			try:		
				self.plugin.debug = self.plugin.pluginPrefs['showDebugInLog']
			except:
				self.plugin.debug = False

			if self.plugin.pluginPrefs["TCCServer"] == "NA":
				self.TCCServer = "https://tccna.honeywell.com/"
			elif self.plugin.pluginPrefs["TCCServer"] == "EU":
				self.TCCServer = "https://tcceu.honeywell.com/"
			elif self.plugin.pluginPrefs["TCCServer"] == "QA":
				self.TCCServer = "https://qtccna.honeywell.com/sandbox/"

			try:
				if (self.WiFi != self.plugin.pluginPrefs["Wi-Fi"]) or \
					(self.UserID != self.plugin.pluginPrefs["UserID"]) or \
					(self.Password != self.plugin.pluginPrefs["Password"]):
					self.WiFi = self.plugin.pluginPrefs["Wi-Fi"]
					self.UserID = self.plugin.pluginPrefs["UserID"]
					self.Password = self.plugin.pluginPrefs["Password"]
					if self.WiFi == True:
						self.start_WiFi()
			except:
				pass

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
		headers = {'content-type':'application/json'}
		if self.WiFi:
			if self.WiFiStatus == False:
				return
			h_HoneywellThermostat = {'Authorization':'Bearer ' + self.myTCC.access_token}
		if self.evohome:
			if self.evohomeStatus == False:
				return
			h_evohome = {'Authorization':'Bearer ' + self.access_token}

		if action.thermostatAction == indigo.kThermostatAction.SetHeatSetpoint and dev.deviceTypeId in ['HoneywellThermostat', 'evohomeZone']:
			if ((float(action.actionValue) >= float(dev.states["minHeatSetpoint"])) and
				(float(action.actionValue) <= float(dev.states["maxHeatSetpoint"]))):
				indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, action.actionValue))
				if dev.deviceTypeId == 'HoneywellThermostat':
					headers.update(h_HoneywellThermostat)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/heatSetpoint?changeTag=Indigo'
					postdata = {'value':action.actionValue, 'status':self.UIChanges, 'nextTime':dev.states["nextTime"]}
					self.HQ[dev.id]['SetPoint'] = self.HQ[dev.id]['SetPoint'] + 1
				elif dev.deviceTypeId == 'evohomeZone':
					headers.update(h_evohome)
					url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureZone/' + dev.address + '/heatSetpoint'
					postdata = {'HeatSetpointValue':action.actionValue, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
				response = requests.put(url, data=json.dumps(postdata), headers=headers)
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, action.actionValue, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))
		elif action.thermostatAction == indigo.kThermostatAction.IncreaseHeatSetpoint and dev.deviceTypeId in ['HoneywellThermostat', 'evohomeZone']:
			newSetpoint = dev.states["setpointHeat"] + float(action.actionValue)
			if ((newSetpoint >= float(dev.states["minHeatSetpoint"])) and (newSetpoint <= float(dev.states["maxHeatSetpoint"]))):
				indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, newSetpoint))
				if dev.deviceTypeId == 'HoneywellThermostat':
					headers.update(h_HoneywellThermostat)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/heatSetpoint?changeTag=Indigo'
					postdata = {'value':newSetpoint, 'status':self.UIChanges, 'nextTime':dev.states["nextTime"]}
					self.HQ[dev.id]['SetPoint'] = self.HQ[dev.id]['SetPoint'] + 1
				elif dev.deviceTypeId == 'evohomeZone':
					headers.update(h_evohome)
					url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureZone/' + dev.address + '/heatSetpoint'
					postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
				response = requests.put(url, data=json.dumps(postdata), headers=headers)
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseHeatSetpoint and dev.deviceTypeId in ['HoneywellThermostat', 'evohomeZone']:
			newSetpoint = dev.states["setpointHeat"] - float(action.actionValue)
			if ((newSetpoint >= float(dev.states["minHeatSetpoint"])) and (newSetpoint <= float(dev.states["maxHeatSetpoint"]))):
				indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, newSetpoint))
				if dev.deviceTypeId == 'HoneywellThermostat':
					headers.update(h_HoneywellThermostat)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/heatSetpoint?changeTag=Indigo'
					postdata = {'value':newSetpoint, 'status':self.UIChanges, 'nextTime':dev.states["nextTime"]}
					self.HQ[dev.id]['SetPoint'] = self.HQ[dev.id]['SetPoint'] + 1
				elif dev.deviceTypeId == 'evohomeZone':
					headers.update(h_evohome)
					url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureZone/' + dev.address + '/heatSetpoint'
					postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
				response = requests.put(url, data=json.dumps(postdata), headers=headers)
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))

		elif action.thermostatAction == indigo.kThermostatAction.SetCoolSetpoint and dev.deviceTypeId == 'HoneywellThermostat':
			if ((float(action.actionValue) >= float(dev.states["minCoolSetpoint"])) and
				(float(action.actionValue) <= float(dev.states["maxCoolSetpoint"]))):
				headers.update(h_HoneywellThermostat)
				url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/coolSetpoint?changeTag=Indigo'
				indigo.server.log("[%s]: Setting Cool Setpoint to: %s" % (dev.name, action.actionValue))
				postdata = {'value':action.actionValue, 'status':self.UIChanges, 'nextTime':dev.states["nextTime"]}
				response = requests.put(url, data=json.dumps(postdata), headers=headers)
				self.HQ[dev.id]['SetPoint'] = self.HQ[dev.id]['SetPoint'] + 1
			else:
				self.plugin.errorLog ("[%s]: Cannot set cool setpoint [%s] outside limits [%s,%s]" % (dev.name, action.actionValue, dev.states["minCoolSetpoint"], dev.states["maxCoolSetpoint"]))
		elif action.thermostatAction == indigo.kThermostatAction.IncreaseCoolSetpoint and dev.deviceTypeId == 'HoneywellThermostat':
			newSetpoint = dev.states["setpointCool"] + float(action.actionValue)
			if ((newSetpoint >= float(dev.states["minCoolSetpoint"])) and (newSetpoint <= float(dev.states["maxCoolSetpoint"]))):
				headers.update(h_HoneywellThermostat)
				url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/coolSetpoint?changeTag=Indigo'
				indigo.server.log("[%s]: Setting Cool Setpoint to: %s" % (dev.name, newSetpoint))
				postdata = {'value':newSetpoint, 'status':self.UIChanges, 'nextTime':dev.states["nextTime"]}
				response = requests.put(url, data=json.dumps(postdata), headers=headers)
				self.HQ[dev.id]['SetPoint'] = self.HQ[dev.id]['SetPoint'] + 1
			else:
				self.plugin.errorLog ("[%s]: Cannot set cool setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minCoolSetpoint"], dev.states["maxCoolSetpoint"]))
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseCoolSetpoint and dev.deviceTypeId == 'HoneywellThermostat':
			newSetpoint = dev.states["setpointCool"] - float(action.actionValue)
			if ((newSetpoint >= float(dev.states["minCoolSetpoint"])) and (newSetpoint <= float(dev.states["maxCoolSetpoint"]))):
				headers.update(h_HoneywellThermostat)
				url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/coolSetpoint?changeTag=Indigo'
				indigo.server.log("[%s]: Setting Cool Setpoint to: %s" % (dev.name, newSetpoint))
				postdata = {'value':newSetpoint, 'status':self.UIChanges, 'nextTime':dev.states["nextTime"]}
				response = requests.put(url, data=json.dumps(postdata), headers=headers)
				self.HQ[dev.id]['SetPoint'] = self.HQ[dev.id]['SetPoint'] + 1
			else:
				self.plugin.errorLog ("[%s]: Cannot set cool setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minCoolSetpoint"], dev.states["maxCoolSetpoint"]))

		elif action.thermostatAction == indigo.kThermostatAction.SetHvacMode:
			if action.actionMode == indigo.kHvacMode.Cool:
				if dev.deviceTypeId == 'HoneywellThermostat':
					headers.update(h_HoneywellThermostat)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/mode?changeTag=Indigo'
					indigo.server.log("[%s]: Setting HVAC Mode to: Cool" % dev.name)
					response = requests.put(url, data=json.dumps("Cool"), headers=headers)
			elif action.actionMode == indigo.kHvacMode.HeatCool:
				indigo.server.log("[%s]: Honeywell Thermostat does not support Auto Heat/Cool mode" % dev.name)
			elif action.actionMode == indigo.kHvacMode.Heat:
				if dev.deviceTypeId == 'HoneywellThermostat':
					headers.update(h_HoneywellThermostat)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/mode?changeTag=Indigo'
					indigo.server.log("[%s]: Setting HVAC Mode to: Heat" % dev.name)
					response = requests.put(url, data=json.dumps("Heat"), headers=headers)
				elif dev.deviceTypeId == 'evohomeZone':
					headers.update(h_evohome)
					url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureZone/' + dev.address + '/heatSetpoint'
					indigo.server.log("[%s]: Setting HVAC Mode to: Heat" % dev.name)
					postdata = {'HeatSetpointValue':dev.states["setpointHeat"], 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
					response = requests.put(url, data=json.dumps(postdata), headers=headers)
				elif dev.deviceTypeId == 'evohomeDHW':
					headers.update(h_evohome)
					url = self.TCCServer + 'WebAPI/emea/api/v1/domesticHotWater/' + dev.address + '/state'
					indigo.server.log("[%s]: Setting Domestic Hot Water State to: On" % dev.name)
					postdata = {'state':'On', 'mode':'PermanentOverride', 'untilTime':None}
					response = requests.put(url, data=json.dumps(postdata), headers=headers)

			elif action.actionMode == indigo.kHvacMode.Off:
				if dev.deviceTypeId == 'HoneywellThermostat':
					headers.update(h_HoneywellThermostat)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/mode?changeTag=Indigo'
					indigo.server.log("[%s]: Setting HVAC Mode to: Off" % dev.name)
					response = requests.put(url, data=json.dumps("Off"), headers=headers)					
				elif dev.deviceTypeId == 'evohomeDHW':
					headers.update(h_evohome)
					url = self.TCCServer + 'WebAPI/emea/api/v1/domesticHotWater/' + dev.address + '/state'
					indigo.server.log("[%s]: Setting Domestic Hot Water State to: Off" % dev.name)
					postdata = {'state':'Off', 'mode':'PermanentOverride', 'untilTime':None}
					response = requests.put(url, data=json.dumps(postdata), headers=headers)

			elif action.actionMode == indigo.kHvacMode.ProgramHeatCool:
				indigo.server.log("[%s]: Honeywell Thermostat does not support Auto Heat/Cool mode" % dev.name)

			elif action.actionMode == indigo.kHvacMode.ProgramCool:
				if dev.deviceTypeId == 'HoneywellThermostat':
					headers.update(h_HoneywellThermostat)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/mode?changeTag=Indigo'
					indigo.server.log("[%s]: Setting HVAC Mode to: Program Cool" % dev.name)
					response = requests.put(url, data=json.dumps("Cool"), headers=headers)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/coolSetpoint?changeTag=Indigo'
					indigo.server.log("[%s]: Setting Cool Setpoint to: %s" % (dev.name, dev.states["scheduleCoolSp"]))
					postdata = {'value':dev.states["scheduleCoolSp"], 'status':'Scheduled', 'nextTime':dev.states["nextTime"]}
					response = requests.put(url, data=json.dumps(postdata), headers=headers)
			elif action.actionMode == indigo.kHvacMode.ProgramHeat:
				if dev.deviceTypeId == 'HoneywellThermostat':
					headers.update(h_HoneywellThermostat)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/mode?changeTag=Indigo'
					indigo.server.log("[%s]: Setting HVAC Mode to: Program Heat" % dev.name)
					response = requests.put(url, data=json.dumps("Heat"), headers=headers)
					url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/heatSetpoint?changeTag=Indigo'
					indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, dev.states["scheduleHeatSp"]))
					postdata = {'value':dev.states["scheduleHeatSp"], 'status':'Scheduled', 'nextTime':dev.states["nextTime"]}
					response = requests.put(url, data=json.dumps(postdata), headers=headers)
				elif dev.deviceTypeId == 'evohomeZone':
					headers.update(h_evohome)
					url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureZone/' + dev.address + '/heatSetpoint'
					indigo.server.log("[%s]: Setting HVAC Mode to: Follow Schedule" % dev.name)
					postdata = {'HeatSetpointValue':None, 'SetpointMode':'FollowSchedule', 'TimeUntil':None}
					response = requests.put(url, data=json.dumps(postdata), headers=headers)
				elif dev.deviceTypeId == 'evohomeDHW':
					headers.update(h_evohome)
					url = self.TCCServer + 'WebAPI/emea/api/v1/domesticHotWater/' + dev.address + '/state'
					indigo.server.log("[%s]: Setting Domestic Hot Water State to: Follow Schedule" % dev.name)
					postdata = {'state':None, 'mode':'FollowSchedule', 'untilTime':None}
					response = requests.put(url, data=json.dumps(postdata), headers=headers)

			if dev.deviceTypeId == 'HoneywellThermostat':
				self.HQ[dev.id]['OperationMode'] = self.HQ[dev.id]['OperationMode'] + 1
	
		elif action.thermostatAction == indigo.kThermostatAction.SetFanMode:
			if dev.deviceTypeId == 'HoneywellThermostat':
				headers.update(h_HoneywellThermostat)
				url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/fan/changeableValues'
				if action.actionMode == indigo.kFanMode.Auto:
					indigo.server.log("[%s]: Setting Fan Mode to: Auto On/Off" % dev.name)
					postdata = {'mode':'Auto'}
					response = requests.put(url, data=json.dumps(postdata), headers=headers)
				elif action.actionMode == indigo.kFanMode.AlwaysOn:
					indigo.server.log("[%s]: Setting Fan Mode to: Always On" % dev.name)
					postdata = {'mode':'On'}
					response = requests.put(url, data=json.dumps(postdata), headers=headers)
				self.HQ[dev.id]['FanMode'] = self.HQ[dev.id]['FanMode'] + 1

		elif action.thermostatAction in [indigo.kThermostatAction.RequestStatusAll,
			indigo.kThermostatAction.RequestMode,
			indigo.kThermostatAction.RequestEquipmentState,
			indigo.kThermostatAction.RequestTemperatures,
			indigo.kThermostatAction.RequestHumidities,
			indigo.kThermostatAction.RequestDeadbands,
			indigo.kThermostatAction.RequestSetpoints]:
			indigo.server.log("[%s]: Requesting Status..." % dev.name)

		if dev.deviceTypeId == 'HoneywellThermostat':
			self.getDevice (dev)
		elif dev.deviceTypeId in ['evohomeDHW', 'evohomeZone', 'evohomeController']:
			self.evohome_get_all ()
		return

	def actionCustomControl(self, pluginAction, action):
		if self.WiFiStatus == False:
			return
		dev = indigo.devices[pluginAction.deviceId]
		headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.myTCC.access_token}

		if action == "actionSetpointStatus":
			if "Cool" in dev.states["thermostatMode"]:
				cValue = "coolSetpoint"
				spValue = dev.states["setpointCool"]
				schValue = dev.states["scheduleCoolSp"]
			elif "Heat" in dev.states["thermostatMode"]:
				cValue = "heatSetpoint"
				spValue = dev.states["setpointHeat"]
				schValue = dev.states["scheduleHeatSp"]
			else:
				return
			url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/' + cValue + '?changeTag=Indigo'
			setting = pluginAction.props.get("setting")
			if setting == "Scheduled":
				indigo.server.log("[%s]: Setting Setpoint Status to: Scheduled" % dev.name)
				postdata = {'value':schValue, 'status':'Scheduled', 'nextTime':dev.states["nextTime"]}
			elif setting == "Temporary":
				indigo.server.log("[%s]: Setting Setpoint Status to: Temporary Hold" % dev.name)
				postdata = {'value':spValue, 'status':'Temporary', 'nextTime':dev.states["nextTime"]}
			elif setting == "Hold":
				indigo.server.log("[%s]: Setting Setpoint Status to: Permanent Hold" % dev.name)
				postdata = {'value':spValue, 'status':'Hold', 'nextTime':dev.states["nextTime"]}
			response = requests.put(url, data=json.dumps(postdata), headers=headers)
			if response.status_code != 201:
				self.plugin.errorLog("[%s]: Cannnot set Setpoint Status for: %s" % (time.asctime(), dev.name))

		elif action == "actionZoneSetpoint":
			settingType = pluginAction.props.get("settingType")
			setting = pluginAction.props.get("setting")
			if pluginAction.props.get("Timing") == True:
				Timing = 'Hold'
			else:
				Timing = 'Temporary'
			Duration = pluginAction.props.get("Duration")
			indigo.server.log("[%s]: Setting %s Setpoint to: %s" % (dev.name, settingType, setting))
			url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '/thermostat/changeableValues/' + settingType + 'Setpoint?changeTag=Indigo'
			postdata = {'value':setting, 'status':Timing, 'nextTime':'2000-01-01T' + Duration + ':00'}
			response = requests.put(url, data=json.dumps(postdata), headers=headers)
			if response.status_code != 201:
				self.plugin.errorLog("[%s]: Cannnot set Setpoint for: %s" % (time.asctime(), dev.name))


		self.getDevice (dev)
		return

	def evohome_actionCustomControl(self, pluginAction, action):
		if self.evohomeStatus == False:
			return
		dev = indigo.devices[pluginAction.deviceId]
		headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.access_token}

		if action == "actionSystemModeSet":
			url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureControlSystem/' + dev.address + '/mode'
			setting = pluginAction.props.get("setting")
			if setting == "Auto1":
				postdata = {'SystemMode':'Auto', 'Permanent':True, 'TimeUntil':None}
				indigo.server.log("[%s]: Setting SystemMode to: Auto" % dev.name)
			elif setting == "AutoWithEco":
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 1 or Duration > 24:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (1-24)" % (time.asctime(), Duration))
						return
					else:
						until = (datetime.utcnow() + timedelta(hours=Duration)).strftime("%Y-%m-%dT%H:00:00Z")					
						postdata = {'SystemMode':setting, 'Permanent':False, 'TimeUntil':until}
						indigo.server.log("[%s]: Setting SystemMode to: Auto with Eco until: %s" % (dev.name, until))
				else:
					postdata = {'SystemMode':setting, 'Permanent':True, 'TimeUntil':None}
					indigo.server.log("[%s]: Setting SystemMode to: Auto with Eco" % dev.name)
			elif setting in ['AutoWithReset', 'HeatingOff']:
				postdata = {'SystemMode':setting, 'Permanent':True, 'TimeUntil':None}
				indigo.server.log("[%s]: Setting SystemMode to: %s" % (dev.name, setting))
			elif setting in ['Away', 'DayOff', 'Custom']:
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 1 or Duration > 99:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (1-99)" % (time.asctime(), Duration))
						return
					else:
						until = (datetime.utcnow() + timedelta(days=Duration)).strftime("%Y-%m-%dT00:00:00Z")
						postdata = {'systemMode':setting, 'Permanent':False, 'TimeUntil':until}
						indigo.server.log("[%s]: Setting SystemMode to: %s until: %s" % (dev.name, setting, until))
				else:
					postdata = {'SystemMode':setting, 'Permanent':True, 'TimeUntil':None}
					indigo.server.log("[%s]: Setting SystemMode to: %s" % (dev.name, setting))
			response = requests.put(url, data=json.dumps(postdata), headers=headers)
			if response.status_code != 201:
				self.plugin.errorLog("[%s]: Cannnot set SystemMode for: %s" % (time.asctime(), dev.name))

		elif action == "actionZoneSetpointMode":
			setting = pluginAction.props.get("setting")
			url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureZone/' + dev.address + '/heatSetpoint'
			if setting == 'FollowSchedule':
				postdata = {'HeatSetpointValue':None, 'SetpointMode':'FollowSchedule', 'TimeUntil':None}
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
					until = t2.strftime("%Y-%m-%dT%H:%M:00Z")
					postdata = {'HeatSetpointValue':dev.states["setpointHeat"], 'SetpointMode':'TemporaryOverride', 'TimeUntil':until}
					indigo.server.log("[%s]: Setting Heat Setpoint to: %s until: %s" % (dev.name, setting, until))
			elif setting == 'PermanentOverride':
				postdata = {'HeatSetpointValue':dev.states["setpointHeat"], 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
				indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, setting))
			response = requests.put(url, data=json.dumps(postdata), headers=headers)
			if response.status_code != 201:
				self.plugin.errorLog("[%s]: Cannnot set setpointMode for: %s" % (time.asctime(), dev.name))

		elif action == "actionZoneSetpoint":
			setting = float(pluginAction.props.get("setting"))
			if ((setting >= float(dev.states["minHeatSetpoint"])) and (setting <= float(dev.states["maxHeatSetpoint"]))):
				url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureZone/' + dev.address + '/heatSetpoint'
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 10 or Duration > 1440:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
						return
					else:
						t1 = (datetime.utcnow() + timedelta(minutes=Duration))
						r1 = int(t1.strftime("%M"))
						t2 = t1.replace(minute=r1-(r1%10))
						until = t2.strftime("%Y-%m-%dT%H:%M:00Z")
						postdata = {'HeatSetpointValue':setting, 'SetpointMode':'TemporaryOverride', 'TimeUntil':until}
						indigo.server.log("[%s]: Setting Heat Setpoint to: %s until: %s" % (dev.name, setting, until))
				else:
					postdata = {'HeatSetpointValue':setting, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
					indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, setting))
				response = requests.put(url, data=json.dumps(postdata), headers=headers)
				if response.status_code != 201:
					self.plugin.errorLog("[%s]: Cannnot set setpointHeat for: %s" % (time.asctime(), dev.name))
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, setting, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))
				return

		elif action == "actionZoneSetpointIncrease":
			setting = pluginAction.props.get("setting")
			newSetpoint = dev.states["setpointHeat"] + float(setting)
			if ((newSetpoint >= float(dev.states["minHeatSetpoint"])) and (newSetpoint <= float(dev.states["maxHeatSetpoint"]))):
				url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureZone/' + dev.address + '/heatSetpoint'
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 10 or Duration > 1440:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
						return
					else:
						t1 = (datetime.utcnow() + timedelta(minutes=Duration))
						r1 = int(t1.strftime("%M"))
						t2 = t1.replace(minute=r1-(r1%10))
						until = t2.strftime("%Y-%m-%dT%H:%M:00Z")
						postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'TemporaryOverride', 'TimeUntil':until}
						indigo.server.log("[%s]: Setting Heat Setpoint to: %s until: %s" % (dev.name, newSetpoint, until))
				else:
					postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
					indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, newSetpoint))
				response = requests.put(url, data=json.dumps(postdata), headers=headers)
				if response.status_code != 201:
					self.plugin.errorLog("[%s]: Cannnot set setpointHeat for: %s" % (time.asctime(), dev.name))
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))
				return

		elif action == "actionZoneSetpointDecrease":
			setting = pluginAction.props.get("setting")
			newSetpoint = dev.states["setpointHeat"] - float(setting)
			if ((newSetpoint >= float(dev.states["minHeatSetpoint"])) and (newSetpoint <= float(dev.states["maxHeatSetpoint"]))):
				url = self.TCCServer + 'WebAPI/emea/api/v1/temperatureZone/' + dev.address + '/heatSetpoint'
				if bool(pluginAction.props.get("Timing")) == False:
					Duration = int(pluginAction.props.get("Duration"))
					if Duration < 10 or Duration > 1440:
						self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
						return
					else:
						t1 = (datetime.utcnow() + timedelta(minutes=Duration))
						r1 = int(t1.strftime("%M"))
						t2 = t1.replace(minute=r1-(r1%10))
						until = t2.strftime("%Y-%m-%dT%H:%M:00Z")
						postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'TemporaryOverride', 'TimeUntil':until}
						indigo.server.log("[%s]: Setting Heat Setpoint to: %s until: %s" % (dev.name, newSetpoint, until))
				else:
					postdata = {'HeatSetpointValue':newSetpoint, 'SetpointMode':'PermanentOverride', 'TimeUntil':None}
					indigo.server.log("[%s]: Setting Heat Setpoint to: %s" % (dev.name, newSetpoint))
				response = requests.put(url, data=json.dumps(postdata), headers=headers)
				if response.status_code != 201:
					self.plugin.errorLog("[%s]: Cannnot set setpointHeat for: %s" % (time.asctime(), dev.name))
			else:
				self.plugin.errorLog ("[%s]: Cannot set heat setpoint [%s] outside limits [%s,%s]" % (dev.name, newSetpoint, dev.states["minHeatSetpoint"], dev.states["maxHeatSetpoint"]))
				return

		elif action == "actionDHWMode":
			setting = pluginAction.props.get("setting")
			url = self.TCCServer + 'WebAPI/emea/api/v1/domesticHotWater/' + dev.address + '/state'
			if setting == 'FollowSchedule':
				postdata = {'state':None, 'mode':'FollowSchedule', 'untilTime':None}
				indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s" % (dev.name, setting))
			elif setting == 'TemporaryOverride':
				Duration = int(pluginAction.props.get("Duration"))
				if Duration < 10 or Duration > 1440:
					self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
					return
				else:
					t1 = (datetime.utcnow() + timedelta(minutes=Duration))
					r1 = int(t1.strftime("%M"))
					t2 = t1.replace(minute=r1-(r1%10))
					until = t2.strftime("%Y-%m-%dT%H:%M:00Z")
					postdata = {'state':dev.states["zoneState"], 'mode':'TemporaryOverride', 'untilTime':until}
					indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s until: %s" % (dev.name, setting, until))
			elif setting == 'PermanentOverride':
				postdata = {'state':dev.states["zoneState"], 'mode':'PermanentOverride', 'untilTime':None}
				indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s" % (dev.name, setting))
			response = requests.put(url, data=json.dumps(postdata), headers=headers)
			if response.status_code != 201:
				self.plugin.errorLog("[%s]: Cannnot set zoneMode for: %s" % (time.asctime(), dev.name))

		elif action == "actionDHWState":
			setting = pluginAction.props.get("setting")
			url = self.TCCServer + 'WebAPI/emea/api/v1/domesticHotWater/' + dev.address + '/state'
			if bool(pluginAction.props.get("Timing")) == False:
				Duration = int(pluginAction.props.get("Duration"))
				if Duration < 10 or Duration > 1440:
					self.plugin.errorLog("[%s]: Duration [%s] is out of range (10-1440)" % (time.asctime(), Duration))
					return
				else:
					t1 = (datetime.utcnow() + timedelta(minutes=Duration))
					r1 = int(t1.strftime("%M"))
					t2 = t1.replace(minute=r1-(r1%10))
					until = t2.strftime("%Y-%m-%dT%H:%M:00Z")
					postdata = {'state':setting, 'mode':'TemporaryOverride', 'untilTime':until}
					indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s until: %s" % (dev.name, setting, until))
			else:
				postdata = {'state':setting, 'mode':'PermanentOverride', 'untilTime':None}
				indigo.server.log("[%s]: Setting Domestic Hot Water Mode to: %s" % (dev.name, setting))
			response = requests.put(url, data=json.dumps(postdata), headers=headers)
			if response.status_code != 201:
				self.plugin.errorLog("[%s]: Cannnot set setpointHeat for: %s" % (time.asctime(), dev.name))

		self.evohome_get_all ()
		return

	def dumpJSON(self, action, dev):
		url = self.TCCServer + 'WebAPI/api/devices/' + dev.address + '?allData=True'
		headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.myTCC.access_token}
		response = requests.get(url, headers=headers)
		if response.status_code == 200:
			content = json.loads (response.content)
			indigo.server.log("%s" % json.dumps(content,sort_keys=True,indent=4, separators=(',', ': ')))
		else:
			self.plugin.errorLog("Cannot read device data for: %s" % dev.name)

	def dumpTCC(self):
		headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.myTCC.access_token}
		url = self.TCCServer + 'WebAPI/api/accountInfo'
		response = requests.get(url, headers=headers)
		if response.status_code != 200:
			self.plugin.errorLog("[%s] Cannot read TCC data" % time.asctime())
			return
		content = json.loads (response.content)
		userID = content["userID"]
		url = self.TCCServer + 'WebAPI/api/locations?userId=' + str(userID) + '&allData=False&include=1'
		response = requests.get(url, headers=headers)
		if response.status_code != 200:
			self.plugin.errorLog("[%s] Cannot read TCC data" % time.asctime())
			return			
		content = json.loads (response.content)
		indigo.server.log("┌────────────────────────┬─────────────────┬──────────────────┬───────────────────┐")
		indigo.server.log("│        Location        │    Device ID    │       Name       │       Model       │")
		indigo.server.log("├-───────────────────────┼─────────────────┼──────────────────┼───────────────────┤")
		try: os.remote("thermostat_data.log")
		except: pass
		tout = open("thermostat_data.log", 'w')
		for location in content:
			for device in location["devices"]:
				indigo.server.log("│ %s │ %s │ %s │ %s │" % (location["name"].ljust(22), str(device["deviceID"]).ljust(15), device["name"].ljust(16), device["thermostatModelType"].ljust(17)))
				url = self.TCCServer + 'WebAPI/api/devices/' + str(device["deviceID"]) + '?allData=True'
				response = requests.get(url, headers=headers)
				if response.status_code == 200:
					content = json.loads (response.content)
					tout.write(str(json.dumps(content,sort_keys=True,indent=4, separators=(',', ': '))))
					tout.write('\n\n')
		tout.close()
		indigo.server.log("└────────────────────────┴─────────────────┴──────────────────┴───────────────────┘")

	def dumpEvohomeTCC(self):

		url = "https://mytotalconnectcomfort.com/WebApi/api/Session"
		payload = 'username='+self.plugin.pluginPrefs['evohome_UserID']+'&password='+self.plugin.pluginPrefs['evohome_Password']+'&ApplicationId=91db1612-73fd-4500-91b2-e63b069b185c'
		headers = {
			'Content-type': 'application/x-www-form-urlencoded'
		}
		response = requests.request("POST", url, headers=headers, data=payload)

		if response.status_code != 200:
			self.plugin.errorLog("[%s] Cannot read evohome TCC data" % time.asctime())
			return			
		content = json.loads(response.content)
		self.access_token=content["sessionId"]

		userID = str(content["userInfo"]['userID'])

		url = 'https://mytotalconnectcomfort.com/WebApi/api/locations?userId=' + userID + '&allData=True'
		headers = dict(sessionID=self.access_token)
		payload = {}
		response = requests.request("GET", url, headers=headers, data=payload)
		if response.status_code != 200:
			self.plugin.errorLog("[%s] Cannot read evohome TCC data" % time.asctime())
			return			
		all_locations = json.loads(response.content)
		indigo.server.log("┌────────────────────────┬─────────────────┬─────────────────┬──────────────────┬───────────────────┐")
		indigo.server.log("│        Location        │    System ID    │    Device ID    │       Name       │       Model       │")
		indigo.server.log("├────────────────────────┼─────────────────┼─────────────────┼──────────────────┼───────────────────┤")
		#indigo.server.log(all_locations['devices'])
		#indigo.server.log("all_locations: %s" % all_locations["name"])
		for device_instance in all_locations[0]["devices"]:
			if device_instance["thermostatModelType"] == "DOMESTIC_HOT_WATER":
				indigo.server.log("│ %s │ %s │ %s │ %s │ %s │" % (
				all_locations[0]["name"].ljust(22), str(all_locations[0]["locationID"]).ljust(15), "".ljust(15),
				"".ljust(16), "DomesticHotWater".ljust(17)))
			else:
				indigo.server.log("│ %s │ %s │ %s │ %s │ %s │" % (
				all_locations[0]["name"].ljust(22), str(all_locations[0]["locationID"]).ljust(15),
				str(device_instance["deviceID"]).ljust(15), device_instance["name"].ljust(16),
				device_instance["thermostatModelType"].ljust(17)))

			#indigo.server.log("\tgateway: %s" % all_locations["devices"]["deviceId"])
			#indigo.server.log("│ %s │ %s │ %s │ %s │ %s │" % (all_locations["locationInfo"]["name"].ljust(22), all_locations["systemId"].ljust(15), "".ljust(15), "".ljust(16), all_locations["thermostatModelType"].ljust(17)))
			#indigo.server.log("\t\tsystem: %s" % all_locations["locationId"])
			#if "dhw" in temperatureControlSystem:
			#	indigo.server.log("│ %s │ %s │ %s │ %s │ %s │" % (all_locations["locationInfo"]["name"].ljust(22), all_locations["systemId"].ljust(15), all_locations["devices"]["deviceID"].ljust(15), "".ljust(16), "DomesticHotWater".ljust(17)))
			#else:
			#	indigo.server.log("│ %s │ %s │ %s │ %s │ %s │" % (all_locations["locationInfo"]["name"].ljust(22), all_locations["systemId"].ljust(15), all_locations["devices"]["deviceID"].ljust(15), zone["name"].ljust(16), all_locations["thermostatModelType"].ljust(17)))
			#	indigo.server.log("\t\t\tzone: %s" % zone["zoneId"])
		indigo.server.log("└────────────────────────┴─────────────────┴─────────────────┴──────────────────┴───────────────────┘")

	def createEvohomeDevices(self):
		devPropsZone = {'NumHumidityInputs':0, 'SupportsCoolSetpoint':False, 'SupportsHvacFanMode':False, 'ShowCoolHeatEquipmentStateUI':True}
		devPropsDHW = {'NumHumidityInputs':0, 'SupportsHeatSetpoint':False, 'SupportsCoolSetpoint':False, 'SupportsHvacFanMode':False, 'ShowCoolHeatEquipmentStateUI':True}

		#headers = {'content-type':'application/json', 'Authorization':'Bearer ' + self.access_token}
		#url = self.TCCServer + 'WebAPI/emea/api/v1/userAccount'
		#response = requests.get(url, headers=headers)
		#content = json.loads (response.content)
		#if response.status_code != 200:
		#	self.plugin.errorLog("[%s] Cannot read evohome TCC data" % time.asctime())
		url = "https://mytotalconnectcomfort.com/WebApi/api/Session"
		payload = 'username='+self.plugin.pluginPrefs['evohome_UserID']+'&password='+self.plugin.pluginPrefs['evohome_Password']+'&ApplicationId=91db1612-73fd-4500-91b2-e63b069b185c'
		headers = {
			'Content-type': 'application/x-www-form-urlencoded'
		}
		response = requests.request("POST", url, headers=headers, data=payload)

		if response.status_code != 200:
			self.plugin.errorLog("[%s] Cannot read evohome TCC data" % time.asctime())
			return			
		userID = str(content["userInfo"]['userID'])

		url = self.TCCServer + 'WebAPI/emea/api/v1/location/installationInfo?userId=' + userID + '&includeTemperatureControlSystems=True'
		response = requests.get(url, headers=headers)
		if response.status_code != 200:
			self.plugin.errorLog("[%s] Cannot read evohome TCC data" % time.asctime())
			return			
		all_locations = json.loads (response.content)

		for location in all_locations:
			found = False
			for dev in indigo.devices.iter("self.evohomeLocation"):
				if dev.address == all_locations[0]["locationID"]:
					found = True
					break
			if found == False:
				dev = indigo.device.create(protocol=indigo.kProtocol.Plugin, address=location["locationInfo"]["locationId"], deviceTypeId='evohomeLocation', name='EV Loc: ' + location["locationInfo"]["name"])
				indigo.server.log("[%s] Created evohome Location: [%s] %s" % (time.asctime(), dev.address, dev.name))

			for gateway in location["gateways"]:
				for temperatureControlSystem in gateway["temperatureControlSystems"]:
					found = False
					for dev in indigo.devices.iter("self.evohomeController"):
						if dev.address == temperatureControlSystem["systemId"]:
							found = True
							break
					if found == False:
						dev = indigo.device.create(protocol=indigo.kProtocol.Plugin, address=temperatureControlSystem["systemId"], deviceTypeId='evohomeController', name='EV Con: ' + location["locationInfo"]["name"] + ' [' + temperatureControlSystem["systemId"] + ']')
						indigo.server.log("[%s] Created evohome Controller: [%s] %s" % (time.asctime(), dev.address, dev.name))

					if "dhw" in temperatureControlSystem:
						found = False
						for dev in indigo.devices.iter("self.evohomeDHW"):
							if dev.address == temperatureControlSystem["dhw"]["dhwId"]:
								found = True
								break
						if found == False:
							dev = indigo.device.create(protocol=indigo.kProtocol.Plugin, address=temperatureControlSystem["dhw"]["dhwId"], deviceTypeId='evohomeDHW', props=devPropsDHW, name='EV DHW: ' + temperatureControlSystem["systemId"])
							indigo.server.log("[%s] Created evohome DHW: [%s] %s" % (time.asctime(), dev.address, dev.name))

					for zone in temperatureControlSystem["zones"]:
						found = False
						for dev in indigo.devices.iter("self.evohomeZone"):
							if dev.address == zone["zoneId"]:
								found = True
								break
						if found == False:
							dev = indigo.device.create(protocol=indigo.kProtocol.Plugin, address=zone["zoneId"], deviceTypeId='evohomeZone', props=devPropsZone, name='EV Zone: ' + zone["name"])
							indigo.server.log("[%s] Created evohome Zone: [%s] %s" % (time.asctime(), dev.address, dev.name))

		self.evohome_initDevice ()


	def updateStateOnServer(self, dev, state, value):
		if dev.states[state] != value:
			self.plugin.debugLog("Updating Device: %s, State: %s, Value: %s" % (dev.name, state, value))
			dev.updateStateOnServer(state, value)

	######################################################################################
	# UI Validation
	def validatePrefsConfigUi(self, valuesDict):
		self.plugin.debugLog("Vaidating Plugin Configuration")
		errorsDict = indigo.Dict()
		if len(errorsDict) > 0:
			self.plugin.errorLog("\t Validation Errors")
			return (False, valuesDict, errorsDict)
		else:			
			self.plugin.debugLog("\t Validation Succesful")
			self.needToGetPluginPrefs = True
			return (True, valuesDict)


	######################################################################################

	def logSep(self, debug):
		if debug:
			self.plugin.debugLog("---------------------------------------------")
		else:
			indigo.server.log("---------------------------------------------")

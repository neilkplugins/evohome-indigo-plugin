#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2012, SSI. All rights reserved.

import os
import sys
import re
from Honeywell import Honeywell 

class Plugin(indigo.PluginBase):


	######################################################################################
	# class init & del
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.Honeywell = Honeywell(self)	
		self.debug = False
		self.StopThread = False

	def __del__(self):
		indigo.PluginBase.__del__(self)


	######################################################################################
	# plugin startup and shutdown
	def startup(self):
		self.debugLog("Method: startup")
		self.Honeywell.startup()
		
	def shutdown(self):
		self.debugLog("Method: shutdown")


	######################################################################################
	# ConcurrentThread: Start & Stop
	def runConcurrentThread(self):
		self.debugLog("Method: runConcurrentThread")
		self.Honeywell.runConcurrentThread()

	def stopConcurrentThread(self):
		self.debugLog("Method: stopConcurrentThread")
		self.StopThread = True

	def deviceStartComm(self, dev):
		self.Honeywell.deviceStartComm (dev)

	def deviceStopComm(self, dev):
		self.Honeywell.deviceStopComm (dev)

	def checkForUpdates(self):
		indigo.server.log("Manually checking for updates")
		self.updater.checkVersionNow()

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		self.Honeywell.closedPrefsConfigUi(valuesDict, userCancelled)

	
	######################################################################################
	# Actions

	def actionControlThermostat(self, action, dev):
		self.Honeywell.actionControlThermostat(action, dev)

	def actionSetpointStatus(self, pluginAction):
		self.Honeywell.actionCustomControl(pluginAction, "actionSetpointStatus")

	def actionZoneSetpoint(self, pluginAction):
		self.Honeywell.actionCustomControl(pluginAction, "actionZoneSetpoint")

	def dumpJSON(self, action, dev):
		self.Honeywell.dumpJSON(action, dev)

	def dumpTCC(self):
		self.Honeywell.dumpTCC()

	def dumpEvohomeTCC(self):
		self.Honeywell.dumpEvohomeTCC()

	def createEvohomeDevices(self):
		self.Honeywell.createEvohomeDevices()

	def initEvohomeDevices(self):
		self.Honeywell.evohome_initDevice()

	def evohome_actionSystemModeSet(self, pluginAction):
		self.Honeywell.evohome_actionCustomControl(pluginAction, "actionSystemModeSet")

	def evohome_actionZoneSetpointMode(self, pluginAction):
		self.Honeywell.evohome_actionCustomControl(pluginAction, "actionZoneSetpointMode")

	def evohome_actionZoneSetpoint(self, pluginAction):
		self.Honeywell.evohome_actionCustomControl(pluginAction, "actionZoneSetpoint")

	def evohome_actionZoneSetpointIncrease(self, pluginAction):
		self.Honeywell.evohome_actionCustomControl(pluginAction, "actionZoneSetpointIncrease")
		
	def evohome_actionZoneSetpointDecrease(self, pluginAction):
		self.Honeywell.evohome_actionCustomControl(pluginAction, "actionZoneSetpointDecrease")

	def evohome_actionDHWMode(self, pluginAction):
		self.Honeywell.evohome_actionCustomControl(pluginAction, "actionDHWMode")

	def evohome_actionDHWState(self, pluginAction):
		self.Honeywell.evohome_actionCustomControl(pluginAction, "actionDHWState")

	######################################################################################
	# Validations for UI

	def validatePrefsConfigUi(self, valuesDict):
		return self.Honeywell.validatePrefsConfigUi(valuesDict)

	######################################################################################
	# Menu Items




	######################################################################################
	# Lists for UI


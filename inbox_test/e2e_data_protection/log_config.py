#!/usr/bin/python
######################################################################################################################
#
# Copyright (c) 2022 Marvell International Ltd. 
# All Rights Reserved.
#
# This file contains information that is confidential and proprietary to Marvell International Ltd. Commercial use of 
# this code is subject to licensing terms and is permitted only on semiconductor devices manufactured by or on behalf 
# of Marvell International Ltd or its affiliates. Distribution subject to written consent from Marvell International Ltd.
#
######################################################################################################################

import logging
from logging.handlers import RotatingFileHandler
import sys

class MyLog(object):
	def __init__(self, logFile):
		self.logger = logging.getLogger()
		self.logger.setLevel(logging.NOTSET)  # log level controlled seperately for console and log file
		
		self.logger.handlers = []  # this should be initialized, otherwise, debug log will be printed to console

		self.handler = logging.StreamHandler(sys.stdout)
		self.handler.setLevel(logging.INFO)  # console level

		self.formatter = logging.Formatter('[%(asctime)s.%(msecs)03d] %(levelname)s %(filename)s(line:%(lineno)d): %(message)s')

		self.handler.setFormatter(self.formatter)

		self.logger.addHandler(self.handler) # if both stream handler and file handler added, duplicated log in console

		with open(logFile, 'w') as f: # create or clear log file
			pass

		self.logFile = logFile
		# self.logHand = logging.FileHandler(self.logFile, encoding='utf-8')
		# divide log file every 100 MB
		self.logHand = RotatingFileHandler(self.logFile, maxBytes=1024 * 1024 * 100, backupCount=50, encoding='utf-8')
		self.logHand.setFormatter(self.formatter)
		self.logHand.setLevel(logging.DEBUG)  # level in log file
		
		self.logger.addHandler(self.logHand)		

	def debug(self, msg):
		self.logger.debug(msg)
	
	def info(self, msg):
		self.logger.info(msg)
	
	def warn(self, msg):
		self.logger.warn(msg)
	
	def error(self, msg):
		self.logger.error(msg)
	
	def critical(self, msg):
		self.logger.critical(msg)
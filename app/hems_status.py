#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "lib"))

from sensor_data import fetch_data
from config import load_config
import logger

DEV_CONFIG = "../device.yml"


def hems_status_check(config, dev_list):
    for dev_info in dev_list:
        data_valid = fetch_data(
            config["influxdb"],
            config["data"]["tag"],
            config["data"]["label"],
            dev_info["name"],
            config["data"]["field"],
            "1h",
        )["valid"]
        if data_valid:
            logging.info("{name:0s}: OK".format(name=dev_info["name"]))
        else:
            logging.error("{name:0s}: NG".format(name=dev_info["name"]))


######################################################################
logger.init("hems.wattmeter.sharp")

logging.info("Load config...")
config = load_config()
dev_list = load_config(DEV_CONFIG)

logging.info("Start check")

hems_status_check(config, dev_list)

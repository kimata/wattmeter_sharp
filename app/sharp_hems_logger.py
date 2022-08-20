#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import serial
import logging
import pathlib
import fluent.sender

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "lib"))

import sniffer
from config import load_config
import logger

DEV_CONFIG = "../device.yml"


def get_label(dev_list, dev_id):
    for dev_info in dev_list:
        if dev_info["id"] == dev_id:
            return dev_info["label"]
    return None


def fluent_send(sender, data, dev_list):
    label = get_label(dev_list, data["dev_id"])

    if label is None:
        logging.warning("Unkown device: 0x{dev_id:04x}".format(dev_id=data["dev_id"]))
        return

    data = {
        "hostname": label,
        "power": int(data["watt"]),
    }

    if sender.emit("sharp", data):
        logging.info("Send: {data}".format(data=str(data)))
        pathlib.Path(config["liveness"]["file"]).touch()
    else:
        logging.error(sender.last_error)


######################################################################
logger.init("hems.wattmeter.sharp")

logging.info("Load config...")
config = load_config()
dev_list = load_config(DEV_CONFIG)

sender = fluent.sender.FluentSender("hems", host=config["fluent"]["host"])

logging.info("Open serial port")
ser = serial.Serial(config["serial"]["port"], 115200, timeout=10)

logging.info("Start sniffing")
sniffer.sniff(ser, lambda data: fluent_send(sender, data, dev_list))

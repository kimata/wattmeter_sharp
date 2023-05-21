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
from config import load_config, abs_path
import logger

DEV_CONFIG = "device.yaml"

dev_config_mtime = None
addr_list_cache = None


def get_name(addr_list, addr):
    for dev_info in addr_list:
        if dev_info["addr"].lower() == addr.lower():
            return dev_info["name"]
    return None


def reload_addr_list(dev_config):
    global addr_list_cache
    if (dev_config_mtime is not None) and (
        dev_config_mtime == abs_path(dev_config).stat().st_mtime
    ):
        return addr_list_cache

    logging.info("Load device list...")
    addr_list = load_config(dev_config)
    addr_list_cache = addr_list

    return addr_list


def fluent_send(sender, label, field, data):
    addr_list = reload_addr_list(DEV_CONFIG)
    name = get_name(addr_list, data["addr"])

    if name is None:
        logging.warning(
            "Unknown device: dev_id = {dev_id}".format(dev_id=data["dev_id_str"])
        )
        return

    data = {
        "hostname": name,
        field: int(data["watt"]),
    }

    if sender.emit(label, data):
        logging.info("Send: {data}".format(data=str(data)))
        pathlib.Path(config["liveness"]["file"]).touch()
    else:
        logging.error(sender.last_error)


######################################################################
logger.init("hems.wattmeter.sharp", level=logging.INFO)

logging.info("Load config...")
config = load_config()

sender = fluent.sender.FluentSender(
    config["data"]["tag"], host=config["fluent"]["host"]
)

logging.info("Open serial port")
ser = serial.Serial(config["serial"]["port"], 115200, timeout=10)

logging.info("Start sniffing")
sniffer.sniff(
    ser,
    lambda data: fluent_send(
        sender, config["data"]["label"], config["data"]["field"], data
    ),
)

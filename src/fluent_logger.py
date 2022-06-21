#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import serial
from fluent import sender
import logging

import sniffer
import logger

import config

fluent_logger = None


def send(data):
    logging.info(data)

    if data["dev_id"] not in config.DEV_MAP:
        return

    dev_name = config.DEV_MAP[data["dev_id"]]

    if not fluent_logger.emit(
        "sharp",
        {
            "hostname": dev_name,
            "power": int(data["watt"]),
        },
    ):
        logging.error(fluent_logger.last_error)


logger.init("sniffer")

fluent_logger = sender.FluentSender("hems", host=config.FLUENT_HOST)
ser = serial.Serial("/dev/ttyAMA0", 115200, timeout=10)

sniffer.sniff(ser, send)

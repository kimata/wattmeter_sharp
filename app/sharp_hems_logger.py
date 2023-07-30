#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
センサーから収集した消費電力データを Fluentd を使って送信します．

Usage:
  sharp_hmes_logger.py [-c CONFIG] [-s SERVER_HOST] [-p SERVER_PORT] [-T] [-d]

Options:
  -c CONFIG         : 設定ファイルを指定します． [default: config.yaml]
  -s SERVER_HOST    : サーバーのホスト名を指定します． [default: localhost]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します． [default: 4444]
  -T                : テストモードで動作します．
  -d                : デバッグモードで動作します．
"""

from docopt import docopt

import os
import sys
import logging
import pathlib
import fluent.sender
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "lib"))

import serial_pubsub
import sniffer
from config import load_config, abs_path
import notify_slack
import logger

DEV_CONFIG = "device.yaml"

addr_list_cache = None
dev_config_mtime = None


def notify_error(config):
    notify_slack.error(
        config["SLACK"]["BOT_TOKEN"],
        config["SLACK"]["ERROR"]["CHANNEL"],
        config["SLACK"]["FROM"],
        traceback.format_exc(),
        config["SLACK"]["ERROR"]["INTERVAL_MIN"],
    )


def get_name(addr_list, addr):
    for dev_info in addr_list:
        if dev_info["addr"].lower() == addr.lower():
            return dev_info["name"]
    return None


def reload_addr_list(dev_config):
    global addr_list_cache, dev_config_mtime
    if (dev_config_mtime is not None) and (
        dev_config_mtime == abs_path(dev_config).stat().st_mtime
    ):
        return addr_list_cache

    logging.info("Load device list...")
    addr_list = load_config(dev_config)
    addr_list_cache = addr_list
    dev_config_mtime = abs_path(dev_config).stat().st_mtime

    return addr_list


def fluent_send(sender, label, field, data):
    try:
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
            pathlib.Path(config["LIVENESS"]["FILE"]).touch()
        else:
            logging.error(sender.last_error)
    except:
        logging.error(traceback.format_exc())
        notify_error(config)


######################################################################
args = docopt(__doc__)

logger.init("hems.wattmeter.sharp", level=logging.INFO)

config = load_config(args["-c"])

server_host = os.environ.get("HEMS_SERVER_HOST", args["-s"])
server_port = os.environ.get("HEMS_SERVER_PORT", args["-p"])
liveness_file = pathlib.Path(config["LIVENESS"]["FILE"])
log_level = logging.DEBUG if args["-d"] else logging.INFO
test_mode = args["-T"]

logger.init("hems.wattmeter.sharp", level=log_level)

logging.info(
    "Start HEMS logger (server: {host}:{port})".format(
        host=server_host, port=server_port
    )
)

if test_mode:
    logging.info("TEST MODE")


logging.info(
    "Initialize Fluentd sender (host: {host}, tag: {tag})".format(
        host=config["FLUENT"]["HOST"],
        tag=config["FLUENT"]["DATA"]["TAG"],
    )
)
sender = fluent.sender.FluentSender(
    config["FLUENT"]["DATA"]["TAG"], host=config["FLUENT"]["HOST"]
)


def handle_packet(header, payload):
    global test_mode

    if test_mode:
        sniffer.handle_packet(
            header, payload, lambda data: (logging.info("OK"), os._exit(0))
        )
    else:
        sniffer.handle_packet(
            header,
            payload,
            lambda data: fluent_send(
                sender,
                config["FLUENT"]["DATA"]["LABEL"],
                config["FLUENT"]["DATA"]["FIELD"],
                data,
            ),
        )


try:
    serial_pubsub.start_client(server_host, server_port, handle_packet)
except:
    notify_error(config)
    raise

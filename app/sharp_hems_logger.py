#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
センサーから収集した消費電力データを Fluentd を使って送信します．

Usage:
  sharp_hmes_server.py [-f CONFIG] [-s SERVER_HOST] [-p SERVER_PORT] [-d]

Options:
  -f CONFIG         : 設定ファイルを指定します． [default: config.yaml]
  -s SERVER_HOST    : サーバーのホスト名を指定します． [default: localhost]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します． [default: 4444]
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
        config["slack"]["bot_token"],
        config["slack"]["error"]["channel"],
        config["slack"]["from"],
        traceback.format_exc(),
        config["slack"]["error"]["interval_min"],
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
            pathlib.Path(config["liveness"]["file"]).touch()
        else:
            logging.error(sender.last_error)
    except:
        logging.error(traceback.format_exc())
        notify_error(config)


######################################################################
args = docopt(__doc__)

logger.init("hems.wattmeter.sharp", level=logging.INFO)

config = load_config(args["-f"])

server_host = os.environ.get("HEMS_SERVER_HOST", args["-s"])
server_port = os.environ.get("HEMS_SERVER_PORT", args["-p"])
liveness_file = pathlib.Path(config["liveness"]["file"])
log_level = logging.DEBUG if args["-d"] else logging.INFO

logger.init("hems.wattmeter.sharp", level=log_level)

logging.info(
    "Start HEMS logger (server: {host}:{port})".format(
        host=server_host, port=server_port
    )
)

logging.info(
    "Initialize Fluentd sender (host: {host}, tag: {tag})".format(
        host=config["fluent"]["host"],
        tag=config["data"]["tag"],
    )
)
sender = fluent.sender.FluentSender(
    config["data"]["tag"], host=config["fluent"]["host"]
)

try:
    serial_pubsub.start_client(
        server_host,
        server_port,
        lambda header, payload: sniffer.handle_packet(
            header,
            payload,
            lambda data: fluent_send(
                sender, config["data"]["label"], config["data"]["field"], data
            ),
        ),
    )
except:
    notify_error(config)
    raise

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
センサーからのパケットを Pub-Sub パターンで配信します．

Usage:
  sharp_hmes_server.py [-f CONFIG] [-t SERIAL_PORT] [-p SERVER_PORT] [-d]

Options:
  -f CONFIG         : 設定ファイルを指定します． [default: config.yaml]
  -t SERIAL_PORT    : HEMS 中継器を接続するシリアルポートを指定します． [default: /dev/ttyUSB0]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します． [default: 4444]
  -d                : デバッグモードで動作します．
"""

from docopt import docopt

import os
import sys
import pathlib
import logging
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "lib"))

import serial_pubsub
from config import load_config
import notify_slack
import logger


def notify_error(config):
    notify_slack.error(
        config["SLACK"]["BOT_TOKEN"],
        config["SLACK"]["ERROR"]["CHANNEL"],
        config["SLACK"]["FROM"],
        traceback.format_exc(),
        config["SLACK"]["ERROR"]["INTERVAL_MIN"],
    )


######################################################################
args = docopt(__doc__)

config = load_config(args["-f"])

serial_port = os.environ.get("HEMS_SERIAL_PORT", args["-t"])
server_port = os.environ.get("HEMS_SERVER_PORT", args["-p"])
liveness_file = pathlib.Path(config["LIVENESS"]["FILE"])
log_level = logging.DEBUG if args["-d"] else logging.INFO

logger.init("hems.wattmeter.sharp", level=log_level)

logging.info(
    "Start server (serial: {serial}, port: {port})".format(
        serial=serial_port, port=server_port
    )
)

try:
    serial_pubsub.start_server(serial_port, server_port, liveness_file)
except:
    notify_error(config)
    raise

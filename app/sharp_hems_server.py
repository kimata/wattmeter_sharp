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

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "lib"))

import serial_pubsub
import logger


######################################################################
args = docopt(__doc__)

logger.init("hems.wattmeter.sharp", level=logging.INFO)

config = load_config(args["-f"])

serial_port = os.environ.get("HEMS_SERIAL_PORT", args["-t"])
server_port = os.environ.get("HEMS_SERVER_PORT", args["-s"])
liveness_file = pathlib.Path(config["liveness"]["file"])

logging.info(
    "Start server (serial: {serial}, port: {port}".format(
        serial=serial_port, port=server_port
    )
)

start_server(serial_port, server_port, liveness_file)

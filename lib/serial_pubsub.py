#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
センサーからのパケットを Pub-Sub パターンで配信します．

Usage:
  serial_pubsub.py -S [-t SERIAL_PORT] [-p SERVER_PORT] [-d]
  serial_pubsub.py [-s SERVER_HOST] [-p SERVER_PORT] [-d]

Options:
  -S                : サーバーモードで動作します．
  -s SERVER_HOST    : サーバーのホスト名を指定します． [default: localhost]
  -t SERIAL_PORT    : HEMS 中継器を接続するシリアルポートを指定します． [default: /dev/ttyUSB0]
  -p SERVER_PORT    : ZeroMQ の Pub サーバーを動作させるポートを指定します． [default: 4444]
  -d                : デバッグモードで動作します．
"""

import zmq
import serial
import logging

CH = "serial"
SER_BAUD = 115200
SER_TIMEOUT = 10


def start_server(serial_port, server_port, liveness_file=None):
    logging.info("Start serial server...")

    context = zmq.Context()

    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:{port}".format(port=server_port))

    ser = serial.Serial(serial_port, SER_BAUD, timeout=SER_TIMEOUT)

    logging.info("Server initialize done.")

    while True:
        header = ser.read(2)

        if len(header) == 0:
            continue
        elif len(header) == 1:
            logging.debug("Short packet")
            continue

        header_hex = header.hex()
        payload_hex = ser.read(header[1] + 5 - 2).hex()

        logging.debug(
            "send {header} {payload}".format(header=header_hex, payload=payload_hex)
        )
        socket.send_string(
            "{ch} {header} {payload}".format(
                ch=CH, header=header_hex, payload=payload_hex
            )
        )
        if liveness_file is not None:
            liveness_file.touch(exist_ok=True)


def start_client(server_host, server_port, func):
    logging.info("Start serial client...")

    socket = zmq.Context().socket(zmq.SUB)
    socket.connect("tcp://{host}:{port}".format(host=server_host, port=server_port))
    socket.setsockopt_string(zmq.SUBSCRIBE, CH)

    logging.info("Client initialize done.")

    while True:
        ch, header_hex, payload_hex = socket.recv_string().split(" ", 2)
        logging.debug(
            "recv {header} {payload}".format(header=header_hex, payload=payload_hex)
        )
        func(bytes.fromhex(header_hex), bytes.fromhex(payload_hex))


if __name__ == "__main__":
    from docopt import docopt

    import sniffer
    import logger

    args = docopt(__doc__)

    is_server_mode = args["-S"]
    server_host = args["-s"]
    server_port = int(args["-p"])
    serial_port = args["-t"]
    log_level = logging.DEBUG if args["-d"] else logging.INFO

    logger.init("test", level=log_level)

    def log_data(data):
        logging.info(data)

    def handle_packet(header, payload):
        sniffer.handle_packet(header, payload, log_data)

    if is_server_mode:
        print("Start server")
        start_server(serial_port, server_port)
    else:
        host = "localhost"
        print("Start client")
        start_client(server_host, server_port, handle_packet)

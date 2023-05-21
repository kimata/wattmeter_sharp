#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
シリアル入力を Pub-Sub パターンで配信します．

Usage:
  serial_pubsub.py [-s]

Options:
  -s           : サーバーモードで動作します．
"""

import zmq
import serial
import logging

PORT = 4444
CH = "serial"
SER_BAUD = 115200
SER_TIMEOUT = 10


def start_server(port="/dev/ttyUSB0"):
    context = zmq.Context()

    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:{port}".format(port=PORT))

    ser = serial.Serial(port, SER_BAUD, timeout=SER_TIMEOUT)

    while True:
        header = ser.read(2)

        if len(header) == 0:
            continue
        elif len(header) == 1:
            logging.debug("Short packet")
            continue

        payload = ser.read(header[1] + 5 - 2).hex()

        logging.debug("send {payload}".format(payload=payload))
        socket.send_string("{ch} {payload}".format(ch=CH, payload=payload))


def start_client(host, func):
    socket = zmq.Context().socket(zmq.SUB)
    socket.connect("tcp://{host}:{port}".format(host=host, port=PORT))
    socket.setsockopt_string(zmq.SUBSCRIBE, CH)

    while True:
        ch, payload = socket.recv_string().split(" ", 2)
        func(bytes.fromhex(payload))


if __name__ == "__main__":
    from docopt import docopt

    args = docopt(__doc__)

    def print_data(data):
        print("{data}".format(data=data))

    if args["-s"]:
        print("Start server")
        start_server()
    else:
        host = "localhost"
        print("Start client")
        start_client(host, print_data)

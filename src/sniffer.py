#!/usr/bin/env python3
import serial
import struct
import pprint
import datetime

cache = {}

def parse_packet(packet):
    dev_id = struct.unpack('<H', packet[5:7])[0]
    index = packet[14]
    cur_time = struct.unpack('<H', packet[19:21])[0]
    cur_power = struct.unpack('<I', packet[26:30])[0]
    pre_time = struct.unpack('<H', packet[35:37])[0]
    pre_power = struct.unpack('<I', packet[42:46])[0]

    # NOTE: 同じデータが2回送られることがあるので，新しいデータ毎にインクリメント
    # しているフィールドを使ってはじく
    if dev_id in cache and cache[dev_id] == index:
        return Nonea
    cache[dev_id] = index
    
    dif_time = cur_time - pre_time
    if dif_time < 0:
        dif_time += 0x10000
    dif_power = cur_power - pre_power
    if dif_power < 0:
        dif_power += 0x100000000

    return {
        "dev_id": dev_id,
        "cur_time": cur_time,
        "cur_power": cur_power,
        "pre_time": pre_time,
        "pre_power": pre_power,
        "watt": float(dif_power) / dif_time
    }


def sniff(ser, on_capture):
    while True:
        header = ser.read(2)

        if len(header) == 0:
            continue

        payload = ser.read(header[1] + 5 - 2)
        if header[1] == 44:
            data = parse_packet(header + payload)
            if data is not None:
                on_capture(data)

if __name__ == "__main__":
    import logging
    import logger
    logger.init("sniffer")
              
    ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=10)

    def log(data):
        logging.info(data)
    
    sniff(ser, log)


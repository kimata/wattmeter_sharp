#!/usr/bin/env python3
import serial
import struct
import logging

cache = {}


def dump_packet(data):
    return ",".join(
        map(lambda x: "{:02X}".format(x), struct.unpack("B" * len(data), data))
    )


def parse_packet(packet):
    dev_id = struct.unpack("<H", packet[5:7])[0]
    index = packet[14]
    cur_time = struct.unpack("<H", packet[19:21])[0]
    cur_power = struct.unpack("<I", packet[26:30])[0]
    pre_time = struct.unpack("<H", packet[35:37])[0]
    pre_power = struct.unpack("<I", packet[42:46])[0]

    # NOTE: 同じデータが2回送られることがあるので，新しいデータ毎にインクリメント
    # しているフィールドを使ってはじく
    if dev_id in cache and cache[dev_id] == index:
        logging.info("Packet duplication detected")
        return None
    cache[dev_id] = index

    dif_time = cur_time - pre_time
    if dif_time < 0:
        dif_time += 0x10000
    if dif_time == 0:
        logging.info("Packet duplication detected")
        return None

    dif_power = cur_power - pre_power
    if dif_power < 0:
        dif_power += 0x100000000

    data = {
        "dev_id": dev_id,
        "dev_id_str": "0x{:04x}".format(dev_id),
        "cur_time": cur_time,
        "cur_power": cur_power,
        "pre_time": pre_time,
        "pre_power": pre_power,
        "watt": round(float(dif_power) / dif_time, 2),
    }

    logging.info("Receive packet: {data}".format(data=str(data)))

    return data


def sniff(ser, on_capture):
    while True:
        header = ser.read(2)

        if len(header) == 0:
            continue
        elif len(header) == 1:
            logging.warning("Short packet")
            continue

        payload = ser.read(header[1] + 5 - 2)
        if header[1] == 0x2C:
            try:
                logging.warning("Data packet: {data}".format(data=dump_packet(payload)))
                data = parse_packet(header + payload)
                if data is not None:
                    on_capture(data)
            except:
                logging.warning(
                    "Invalid packet: {data}".format(data=dump_packet(header + payload))
                )
                pass
        else:
            logging.warning("Unknown packet: {data}".format(data=dump_packet(payload)))


if __name__ == "__main__":
    import sys
    import logger

    logger.init("test")

    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = "/dev/ttyUSB0"

    ser = serial.Serial(port, 115200, timeout=10)

    def log(data):
        logging.info("Handle packet: {data}".format(data=dump_packet(data)))

    sniff(ser, log)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pathlib
import pickle

import os
import struct
import logging
import json

counter_hist = {}
ieee_addr_list = []

# 電力に掛ける倍率
# NOTE:
# 電力会社のスマートメータの読み値と比較すると常に電力が小さいので，
# 一定の倍率を掛ける．
WATT_SCALE = 1.5

DEV_ID_CACHE = pathlib.Path(os.path.dirname(__file__)).parent / "data" / "dev_id.dat"


def dev_id_map_load():
    if DEV_ID_CACHE.exists():
        with open(DEV_ID_CACHE, "rb") as f:
            return pickle.load(f)
    else:
        return {}


def dev_id_map_store(dev_id_map):
    logging.info("Store dev_id_map")

    with open(DEV_ID_CACHE, "wb") as f:
        pickle.dump(dev_id_map, f)


def dump_packet(data):
    return ",".join(
        map(lambda x: "{:02X}".format(x), struct.unpack("B" * len(data), data))
    )


def parse_packet_ieee_addr(packet):
    addr_data = packet[4:12]

    return ":".join(
        map(
            lambda x: "{:02X}".format(x),
            reversed(struct.unpack("B" * len(addr_data), addr_data)),
        )
    )


def parse_packet_dev_id(packet):
    dev_id = struct.unpack("<H", packet[4:6])[0]
    index = packet[6]

    return {
        "dev_id": dev_id,
        "index": index,
    }


def parse_packet_measure(packet, dev_id_map):
    global counter_hist

    dev_id = struct.unpack("<H", packet[5:7])[0]
    counter = packet[14]
    cur_time = struct.unpack("<H", packet[19:21])[0]
    cur_power = struct.unpack("<I", packet[26:30])[0]
    pre_time = struct.unpack("<H", packet[35:37])[0]
    pre_power = struct.unpack("<I", packet[42:46])[0]

    if dev_id in dev_id_map:
        addr = dev_id_map[dev_id]
    else:
        addr = "UNKNOWN"
        logging.warning("dev_id = 0x{dev_id:04X} is unknown".format(dev_id=dev_id))
        logging.warning(
            "dev_ip_map = {dev_id_map}".format(
                dev_id_map=json.dumps(dev_id_map, indent=4)
            )
        )

    # NOTE: 同じデータが2回送られることがあるので，新しいデータ毎にインクリメント
    # しているフィールドを使ってはじく
    if dev_id in counter_hist and counter_hist[dev_id] == counter:
        logging.info("Packet duplication detected")
        return None
    counter_hist[dev_id] = counter

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
        "addr": addr,
        "dev_id": dev_id,
        "dev_id_str": "0x{:04X}".format(dev_id),
        "cur_time": cur_time,
        "cur_power": cur_power,
        "pre_time": pre_time,
        "pre_power": pre_power,
        "watt": round(float(dif_power) / dif_time * WATT_SCALE, 2),
    }

    logging.debug("Receive packet: {data}".format(data=str(data)))

    return data


def handle_packet(header, payload, on_capture):
    global ieee_addr_list
    dev_id_map = dev_id_map_load()

    if header[1] == 0x08:
        logging.debug("IEEE addr payload: {data}".format(data=dump_packet(payload)))
        ieee_addr_list.append(parse_packet_ieee_addr(header + payload))
    elif header[1] == 0x12:
        logging.debug("Dev ID payload: {data}".format(data=dump_packet(payload)))
        data = parse_packet_dev_id(header + payload)
        if data["index"] < len(ieee_addr_list):
            if data["dev_id"] not in dev_id_map:
                logging.info(
                    "Find IEEE addr for dev_id={dev_id}".format(
                        dev_id="0x{:04X}".format(data["dev_id"])
                    )
                )
                dev_id_map[data["dev_id"]] = ieee_addr_list[data["index"]]
                dev_id_map_store(dev_id_map)
            elif dev_id_map[data["dev_id"]] != ieee_addr_list[data["index"]]:
                logging.info(
                    "Update IEEE addr for dev_id={dev_id}".format(
                        dev_id="0x{:04X}".format(data["dev_id"])
                    )
                )
                dev_id_map[data["dev_id"]] = ieee_addr_list[data["index"]]
                dev_id_map_store(dev_id_map)
        else:
            logging.warning(
                "Unable to identify IEEE addr for dev_id={dev_id}".format(
                    dev_id="0x{:04X}".format(data["dev_id"])
                )
            )

        if data["index"] == (len(ieee_addr_list) - 1):
            # NOTE: 次の周期に備えてリストをクリアする
            logging.debug("Clear IEEE addr list")
            ieee_addr_list = []

    elif header[1] == 0x2C:
        try:
            logging.debug("Measure payload: {data}".format(data=dump_packet(payload)))
            data = parse_packet_measure(header + payload, dev_id_map)
            if data is not None:
                on_capture(data)
        except:
            logging.warning(
                "Invalid packet: {data}".format(data=dump_packet(header + payload))
            )
            pass
    else:
        logging.debug(
            "Unknown packet: {data}".format(data=dump_packet(header + payload))
        )

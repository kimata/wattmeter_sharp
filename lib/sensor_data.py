#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InfluxDB から電子機器の使用時間を取得します．

Usage:
  sensor_data.py [-f CONFIG]  [-e EVERY] [-w WINDOW]

Options:
  -f CONFIG    : CONFIG を設定ファイルとして読み込んで実行します．[default: config.yaml]
  -e EVERY     : 何分ごとのデータを取得するか [default: 1]
  -w WINDOWE   : 算出に使うウィンドウ [default: 5]
"""

from docopt import docopt

import influxdb_client
import datetime
import os
import logging
import traceback

FLUX_QUERY = """
from(bucket: "{bucket}")
|> range(start: -{period})
    |> filter(fn:(r) => r._measurement == "{sensor_type}")
    |> filter(fn: (r) => r.hostname == "{hostname}")
    |> filter(fn: (r) => r["_field"] == "{param}")
    |> aggregateWindow(every: {window}m, fn: mean, createEmpty: {create_empty})
    |> fill(usePrevious: true)
    |> timedMovingAverage(every: {every}m, period: {window}m)
"""

FLUX_SUM_QUERY = """
from(bucket: "{bucket}")
    |> range(start: -{period})
    |> filter(fn:(r) => r._measurement == "{sensor_type}")
    |> filter(fn: (r) => r.hostname == "{hostname}")
    |> filter(fn: (r) => r["_field"] == "{param}")
    |> reduce(
        fn: (r, accumulator) => ({{sum: r._value + accumulator.sum, count: accumulator.count + 1}}),
        identity: {{sum: 0.0, count: 0}},
    )
"""


def fetch_data_impl(
    config,
    template,
    sensor_type,
    hostname,
    param,
    period,
    every,
    window,
    create_empty,
):
    try:
        token = os.environ.get("INFLUXDB_TOKEN", config["TOKEN"])

        query = template.format(
            bucket=config["BUCKET"],
            sensor_type=sensor_type,
            hostname=hostname,
            param=param,
            period=period,
            every=every,
            window=window,
            create_empty=str(create_empty).lower(),
        )
        logging.debug("Flux query = {query}".format(query=query))
        client = influxdb_client.InfluxDBClient(
            url=config["URL"], token=token, org=config["ORG"]
        )
        query_api = client.query_api()

        return query_api.query(query=query)
    except Exception as e:
        logging.warning(e)
        logging.warning(traceback.format_exc())
        raise


def fetch_data(
    config,
    sensor_type,
    hostname,
    param,
    period="30h",
    every_min=1,
    window_min=5,
    create_empty=True,
):
    logging.info(
        (
            "Fetch data (type: {type}, host: {host}, param: {param}, "
            + "period: {period}, every: {every}min, window: {window}min, "
            + "create_empty: {create_empty})"
        ).format(
            type=sensor_type,
            host=hostname,
            param=param,
            period=period,
            every=every_min,
            window=window_min,
            create_empty=create_empty,
        )
    )

    try:
        table_list = fetch_data_impl(
            config,
            FLUX_QUERY,
            sensor_type,
            hostname,
            param,
            period,
            every_min,
            window_min,
            create_empty,
        )
        data = []
        time = []
        localtime_offset = datetime.timedelta(hours=9)

        if len(table_list) != 0:
            for record in table_list[0].records:
                # NOTE: aggregateWindow(createEmpty: true) と fill(usePrevious: true) の組み合わせ
                # だとタイミングによって，先頭に None が入る
                if record.get_value() is None:
                    continue
                data.append(record.get_value())
                time.append(record.get_time() + localtime_offset)

        if create_empty:
            # NOTE: aggregateWindow(createEmpty: true) と timedMovingAverage を使うと，
            # 末尾に余分なデータが入るので取り除く
            every_min = int(every_min)
            window_min = int(window_min)
            if window_min > every_min:
                data = data[: (every_min - window_min)]
                time = time[: (every_min - window_min)]

        logging.info("data count = {count}".format(count=len(time)))

        return {"value": data, "time": time, "valid": len(time) != 0}
    except:
        logging.warning(traceback.format_exc())

        return {"value": [], "time": [], "valid": False}


def get_equip_on_minutes(
    config,
    sensor_type,
    hostname,
    param,
    threshold,
    period="30h",
    every_min=1,
    window_min=5,
    create_empty=True,
):
    logging.info(
        (
            "Get on minutes (type: {type}, host: {host}, param: {param}, "
            + "threshold: {threshold}, period: {period}, every: {every}min, "
            + "window: {window}min, create_empty: {create_empty})"
        ).format(
            type=sensor_type,
            host=hostname,
            param=param,
            threshold=threshold,
            period=period,
            every=every_min,
            window=window_min,
            create_empty=create_empty,
        )
    )

    try:
        table_list = fetch_data_impl(
            config,
            FLUX_QUERY,
            sensor_type,
            hostname,
            param,
            period,
            every_min,
            window_min,
            create_empty,
        )

        if len(table_list) == 0:
            return 0

        count = 0

        every_min = int(every_min)
        window_min = int(window_min)
        record_num = len(table_list[0].records)

        for i, record in enumerate(table_list[0].records):
            if create_empty:
                # NOTE: timedMovingAverage を使うと，末尾に余分なデータが入るので取り除く
                if window_min > every_min:
                    if i > record_num - 1 - (window_min - every_min):
                        continue

            # NOTE: aggregateWindow(createEmpty: true) と fill(usePrevious: true) の組み合わせ
            # だとタイミングによって，先頭に None が入る
            if record.get_value() is None:
                continue
            if record.get_value() >= threshold:
                count += 1

        return count * int(every_min)
    except:
        logging.warning(traceback.format_exc())
        return 0


def get_equip_mode_period(
    config,
    sensor_type,
    hostname,
    param,
    threshold,
    period="30h",
    every_min=1,
    window_min=3,
    create_empty=True,
):
    logging.info(
        (
            "Get equipment mode period (type: {type}, host: {host}, param: {param}, "
            + "threshold: {threshold}, period: {period}, every: {every}min, "
            + "window: {window}min, create_empty: {create_empty})"
        ).format(
            type=sensor_type,
            host=hostname,
            param=param,
            threshold=threshold,
            period=period,
            every=every_min,
            window=window_min,
            create_empty=create_empty,
        )
    )

    try:
        table_list = fetch_data_impl(
            config,
            FLUX_QUERY,
            sensor_type,
            hostname,
            param,
            period,
            every_min,
            window_min,
            create_empty,
        )

        if len(table_list) == 0:
            return []

        # NOTE: 常時冷却と間欠冷却の期間を求める
        on_range = []
        state = "IDLE"
        start_time = None
        localtime_offset = datetime.timedelta(hours=9)

        for record in table_list[0].records:
            # NOTE: aggregateWindow(createEmpty: true) と fill(usePrevious: true) の組み合わせ
            # だとタイミングによって，先頭に None が入る
            if record.get_value() is None:
                continue

            if record.get_value() > threshold["FULL"]:
                if state != "FULL":
                    if state == "INTERM":
                        on_range.append(
                            [
                                start_time + localtime_offset,
                                record.get_time() + localtime_offset,
                                False,
                            ]
                        )
                    state = "FULL"
                    start_time = record.get_time()
            elif record.get_value() > threshold["INTERM"]:
                if state != "INTERM":
                    if state == "FULL":
                        on_range.append(
                            [
                                start_time + localtime_offset,
                                record.get_time() + localtime_offset,
                                True,
                            ]
                        )
                    state = "INTERM"
                    start_time = record.get_time()
            else:
                if state != "IDLE":
                    on_range.append(
                        [
                            start_time + localtime_offset,
                            record.get_time() + localtime_offset,
                            state == "FULL",
                        ]
                    )
                state = "IDLE"

        if state != "IDLE":
            on_range.append(
                [
                    start_time + localtime_offset,
                    table_list[0].records[-1].get_time() + localtime_offset,
                    state == "FULL",
                ]
            )

        return on_range
    except:
        logging.warning(traceback.format_exc())
        return []


def get_today_sum(config, sensor_type, hostname, param):
    try:
        now = datetime.datetime.now()

        period = "{hour}h{minute}m".format(hour=now.hour, minute=now.minute)

        table_list = fetch_data_impl(
            config, FLUX_SUM_QUERY, sensor_type, hostname, param, period
        )

        count, total = table_list.to_values(columns=["count", "sum"])[0]

        return total * (((now.hour * 60 + now.minute) * 60.0) / count) / 60
    except:
        logging.warning(traceback.format_exc())
        return 0


def dump_data(data):
    for i in range(len(data["time"])):
        logging.info(
            "{time}: {value}".format(time=data["time"][i], value=data["value"][i])
        )


if __name__ == "__main__":
    import logger
    import json

    from config import load_config

    args = docopt(__doc__)

    logger.init("test", logging.DEBUG)

    config = load_config(args["-f"])
    every = args["-e"]
    window = args["-w"]

    now = datetime.datetime.now()
    sensor_type = config["USAGE"]["TARGET"]["TYPE"]
    hostname = config["USAGE"]["TARGET"]["HOST"]
    param = config["USAGE"]["TARGET"]["PARAM"]
    threshold = config["USAGE"]["TARGET"]["THRESHOLD"]["WORK"]
    period = config["GRAPH"]["PARAM"]["PERIOD"]

    dump_data(
        fetch_data(
            config["INFLUXDB"], sensor_type, hostname, param, period, every, window
        )
    )

    period = "{hour}h{minute}m".format(hour=now.hour, minute=now.minute)

    logging.info(
        "Today ON minutes ({period}) = {minutes} min".format(
            period=period,
            minutes=get_equip_on_minutes(
                config["INFLUXDB"],
                sensor_type,
                hostname,
                param,
                threshold,
                period,
                every,
                window,
            ),
        )
    )

    sensor_type = config["GRAPH"]["VALVE"]["TYPE"]
    hostname = config["GRAPH"]["VALVE"]["HOST"]
    param = config["GRAPH"]["VALVE"]["PARAM"]
    threshold = config["GRAPH"]["VALVE"]["THRESHOLD"]
    period = config["GRAPH"]["PARAM"]["PERIOD"]

    logging.info(
        "Valve on period = {range_list}".format(
            range_list=json.dumps(
                get_equip_mode_period(
                    config["INFLUXDB"], sensor_type, hostname, param, threshold, period
                ),
                indent=2,
                default=str,
            )
        )
    )

    # logging.info(
    #     "Amount of cooling water used today = {water:0f} L".format(
    #         water=get_today_sum(config["INFLUXDB"], sensor_type, hostname, param)
    #     )
    # )

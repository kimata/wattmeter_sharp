#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import slack_sdk

import json
import logging
import os
import pathlib
import datetime
import tempfile

ERROR_NOTIFY_FOOTPRINT = (
    pathlib.Path(os.path.dirname(__file__)).parent / "data" / "error_notify"
)

SIMPLE_TMPL = """\
[
    {{
        "type": "header",
    "text": {{
            "type": "plain_text",
        "text": "{title}",
            "emoji": true
        }}
    }},
    {{
        "type": "section",
        "text": {{
            "type": "mrkdwn",
        "text": {message}
    }}
    }}
]
"""


def format_simple(title, message):
    return {
        "text": message,
        "json": json.loads(
            SIMPLE_TMPL.format(title=title, message=json.dumps(message))
        ),
    }


def send(token, ch_name, message):
    client = slack_sdk.WebClient(token=token)

    try:
        client.chat_postMessage(
            channel=ch_name,
            text=message["text"],
            blocks=message["json"],
        )
    except slack_sdk.errors.SlackApiError as e:
        logging.warning(e.response["error"])


def split_send(token, ch_name, title, message, formatter=format_simple):
    LINE_SPLIT = 20

    logging.info("Post slack channel: {ch_name}".format(ch_name=ch_name))

    message_lines = message.splitlines()
    for i in range(0, len(message_lines), LINE_SPLIT):
        send(
            token,
            ch_name,
            formatter(title, "\n".join(message_lines[i : i + LINE_SPLIT])),
        )


def info(token, ch_name, name, message, formatter=format_simple):
    title = "Info: " + name
    split_send(token, ch_name, title, message, formatter)


def check_interval(interval_min):
    if (
        ERROR_NOTIFY_FOOTPRINT.exists()
        and (
            datetime.datetime.now()
            - datetime.datetime.fromtimestamp(ERROR_NOTIFY_FOOTPRINT.stat().st_mtime)
        ).seconds
        < interval_min * 60
    ):
        logging.info("skip slack nofity")
        return False

    return True


def error_img(token, ch_id, title, img, text):
    client = slack_sdk.WebClient(token=token)

    with tempfile.TemporaryDirectory() as dname:
        img_path = os.path.join(dname, "error.png")
        img.save(img_path)

        try:
            client.files_upload_v2(
                channel=ch_id, file=img_path, title=title, initial_comment=text
            )
        except slack_sdk.errors.SlackApiError as e:
            logging.warning(e.response["error"])


def error(
    token,
    ch_name,
    name,
    message,
    interval_min=10,
    formatter=format_simple,
):
    title = "Error: " + name

    if not check_interval(interval_min):
        logging.warning("Interval is too short. Skipping.")
        return

    split_send(token, ch_name, title, message, formatter)

    ERROR_NOTIFY_FOOTPRINT.parent.mkdir(parents=True, exist_ok=True)
    ERROR_NOTIFY_FOOTPRINT.touch()


def error_with_image(
    token,
    ch_name,
    ch_id,
    name,
    message,
    attatch_img,
    interval_min=10,
    formatter=format_simple,
):
    title = "Error: " + name

    if not check_interval(interval_min):
        logging.warning("Interval is too short. Skipping.")
        return

    split_send(token, ch_name, title, message, formatter)

    if attatch_img is not None:
        if ch_id is None:
            logging.error("ch_id is not specified.")

        error_img(token, ch_id, title, attatch_img["data"], attatch_img["text"])

    ERROR_NOTIFY_FOOTPRINT.parent.mkdir(parents=True, exist_ok=True)
    ERROR_NOTIFY_FOOTPRINT.touch()


if __name__ == "__main__":
    import os
    import logger
    import sys
    import PIL.Image
    from config import load_config

    logger.init("test", level=logging.INFO)
    logging.info("Test")

    # NOTE: Slack の環境に合わせて書き換える
    test_ch_name = "#test"
    test_ch_id = "C058PTZG13L"

    config = load_config()
    if "SLACK" not in config:
        logging.warning("Slack の設定が記載されていません．")
        sys.exit(-1)

    client = slack_sdk.WebClient(token=config["SLACK"]["BOT_TOKEN"])

    img = PIL.Image.open(
        pathlib.Path(
            os.path.dirname(__file__), config["WEATHER"]["ICON"]["THERMO"]["PATH"]
        )
    )
    if "INFO" in config["SLACK"]:
        info(
            config["SLACK"]["BOT_TOKEN"],
            test_ch_name,
            os.path.basename(__file__),
            "メッセージ\nメッセージ",
        )

    if "ERROR" in config["SLACK"]:
        error(
            config["SLACK"]["BOT_TOKEN"],
            test_ch_name,
            os.path.basename(__file__),
            "エラーメッセージ",
            0,
        )

    if "ERROR" in config["SLACK"]:
        error_with_image(
            config["SLACK"]["BOT_TOKEN"],
            test_ch_name,
            test_ch_id,
            os.path.basename(__file__),
            "エラーメッセージ",
            {"data": img, "text": "エラー時のスクリーンショット"},
            0,
        )

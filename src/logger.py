#!/usr/bin/env python3
# - coding: utf-8 --
import coloredlogs
import logging
import logging.handlers
import pathlib
import bz2
import os

LOG_FORMAT = (
    "%(asctime)s %(levelname)s [%(filename)s:%(lineno)s %(funcName)s] %(message)s"
)


class GZipRotator:
    def namer(name):
        return name + ".bz2"

    def rotator(source, dest):
        with open(source, "rb") as fs:
            with bz2.open(dest, "wb") as fd:
                fd.writelines(fs)
        os.remove(source)


def init(name, dir_path="/dev/shm", is_stderr=True):
    if is_stderr:
        coloredlogs.install(fmt=LOG_FORMAT)
    else:
        logging.getLogger().setLevel(logging.INFO)

    log_path = pathlib.Path(dir_path)
    os.makedirs(str(log_path), exist_ok=True)

    logger = logging.getLogger()
    log_handler = logging.handlers.RotatingFileHandler(
        str(log_path / (name + ".log")),
        encoding="utf8",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
    )
    log_handler.formatter = logging.Formatter(
        fmt=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"
    )
    log_handler.namer = GZipRotator.namer
    log_handler.rotator = GZipRotator.rotator

    logger.addHandler(log_handler)


if __name__ == "__main__":
    init("test")
    logging.info("Test")

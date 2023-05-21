#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib
import yaml
import os

CONFIG_PATH = "config.yaml"


def abs_path(config_path=CONFIG_PATH):
    return pathlib.Path(os.getcwd(), config_path)


def load_config(config_path=CONFIG_PATH):
    path = str(abs_path(config_path))
    with open(path, "r") as file:
        return yaml.load(file, Loader=yaml.SafeLoader)

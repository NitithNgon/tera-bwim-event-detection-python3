import os
import errno
from os.path import isfile
from dotenv import dotenv_values
from config.config_parser import parse_config

def get_preamble_config(path_env: str) -> tuple:
    if not isfile(path_env):
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), f"{path_env} was not found in CWD")
    env_vars = dotenv_values(path_env)
    bridge_name_config = env_vars["BRIDGE_NAME"] if env_vars["bridge_name"] else "default"
    path_config =env_vars["PATH_CONFIG"]
    preamble_config = parse_config(
        config_file=path_config,
        version= bridge_name_config,
    )
    return env_vars, preamble_config

def get_lane_config(preamble_config, lane_number: str):
    event_number_to_config_version_map = preamble_config.get("event_number_to_config_version_map", None)
    config_version = event_number_to_config_version_map.get(
        lane_number) if event_number_to_config_version_map else None
    lane_config = preamble_config[config_version]
    return lane_config

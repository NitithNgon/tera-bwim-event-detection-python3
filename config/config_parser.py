from copy import deepcopy
from yaml import safe_load, YAMLError
import pandas as pd
import numpy as np


CONFIG_FILE = "./config/config.yaml"


def parse_config(version="default", config_file=CONFIG_FILE):
    try:
        with open(config_file, "r") as stream:
            config = safe_load(stream)
            default_config = config["default"]
            parsed_config = deepcopy(default_config)
            if version != "default":
                selected_config = config[version]
                parsed_config.update(selected_config)
                if parsed_config is None:
                    raise ValueError(f"{version} in .env not exists in config.yaml or check config.yaml file")
            return parsed_config
    except KeyError as exception:
        print("Specified version does not exist in config file.")
    except YAMLError as exception:
        print(exception)
    except Exception as exception:
        print(exception)


if __name__ == "__main__":
    loaded_config = parse_config(version="default", config_file=CONFIG_FILE)
    for item in loaded_config:
        print(item, ':', loaded_config[item])

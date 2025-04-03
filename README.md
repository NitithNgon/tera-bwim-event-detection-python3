# tera-bwim-event-detection
BWIM-system required 2 parts of code, `tera-bwim-event-detection` and `tera-bwim-control-analysis-system`. <br>
This repository is `tera-bwim-event-detection` running on python2.7


## Setting up BWIM-Event-Detection-System

1. Install python 2.7
https://www.python.org/downloads/release/python-2718/

2. Create venv from python2.7 and install all pip required in `requirements.txt`

3. Create project in Pycharm from these __script__ and __venv__

4. Create `.env` file with these pattern <br>
    - PIPENV_IGNORE_VIRTUALENVS = 1
    - CONFIG_VERSION = "default"
    - EVENT_DIR_VERSION = "DEVELOP"
    - CURRENT_WORKING_DIR = "ABS/PATH/TO/tera-bwim-control-analysis-system"
    - PATH_PYTHON = "ABS/PATH/TO/PYTHON311"
    - THINGSBOARD_URI = "http://our_thingsboard_uri/api/v1/integrations/http"
    - THINGSBOARD_ACCESS_TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxx"
    - NEOWAVE_PIC_URI = "https://cloud_for_pic"

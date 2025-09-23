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
    - NEOWAVE_PIC_URI = "https://cloud_for_pic"

5. Create `.env-event-detection` file with these pattern <br>
    - BRIDGE_NAME = "BANGPHLAT"
    - CONFIG_VERSION = "default"
    - PATH_CONFIG = "./config/config.yaml"
    - CAM_USER = 'admin'
    - CAM_PWD = 'Alphax123'
    - EVENT_UNCLASSIFIED_SYNOLOGY_DRIVE = "C:\SynologyDrive\BWIM_BMA_002\EVENT_UNCLASSIFIED" # folder which store unclassified event
    - EVENT_BWIM_SYNOLOGY_DRIVE = "C:\SynologyDrive\BWIM_BMA_002\EVENT_BWIM"
    - EVENT_VIDEO_SYNOLOGY_DRIVE = "C:\SynologyDrive\www\BMA002_EVENT"   # folder which store event video
    - EVENT_FTP_PATH = '/home/www/BMA002_EVENT'

5. Create `.env-heartbeat-server` file with these pattern <br>
    - LOCAL_HOST_IP = "10.241.0.1"
    - PORT = "5000"
    - INTERVAL_SECONDS = 10
    - TOKEN_LIST=[secrets.token_urlsafe(32), ]
    - OAUTH_TOKEN = 
    - CHANNEL = 

5. Create `.env-heartbeat-client` file with these pattern <br>
    - SERVER_ENDPOINT="http://10.241.0.1:5000"
    - DEVICE_ID = "BANGPHLAT"
    - HEARTBEAT_SEC = 10
    - RETRY_SEC = 5
    - TOKEN=secrets.token_urlsafe(32)
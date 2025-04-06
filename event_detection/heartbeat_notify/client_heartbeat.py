# -*- coding: utf-8 -*-
import requests
import time
import json

DEVICE_ID = "device_1"
SERVER_URL = "http://192.168.1.76:5000/" #node local
#run "ipconfig" to get sever ip-local IPv4 address
from main import Bwim_process_status

def is_server_ready(url, timeout=5):
    while True:
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                print("✅ Server is UP! Starting heartbeat...")
                return True
        except requests.ConnectionError:
            print("❌ Server is DOWN. Retrying in 5 seconds...")
        except requests.Timeout:
            print("⚠️ Server timed out. Retrying...")

        time.sleep(5)  # Wait before retrying

while True:
    # **Wait until the server is ready
    is_server_ready(SERVER_URL)
    try:
        playload={}
        playload["device_status"] =json.dumps(Bwim_process_status, default=lambda obj: obj.__dict__, indent=4)
        playload["device_id"]= DEVICE_ID
        response = requests.post("{}heartbeat".format(SERVER_URL), data=playload, headers={'Content-Type': 'application/json'})
        print("DEVICE_ID: {} Heartbeat sent.".format(DEVICE_ID))
    except Exception as e:
        print("Failed to send heartbeat: {}".format(e))

    time.sleep(10)  # Send heartbeat every 60 seconds
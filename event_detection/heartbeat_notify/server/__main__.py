import threading
import time
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

LOCAL_HOST_IP = "127.0.0.1"
PORT = "5000"
INTERVAL_SECONDS = 10


app = Flask(__name__)
device_status = {}  # Store last heartbeat timestamps


@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Server is running"}), 200


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    print(data)
    device_id = data.get('device_id')
    status_data = data.get('device_status', {})  # Default to empty dict if not provided

    if device_id:
        device_status[device_id] = {
            "last_time": datetime.now(),
            **status_data
        }
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"error": "No device_id provided"}), 400
    

def check_inactive_devices():
    now = datetime.now()
    timeout = timedelta(seconds=INTERVAL_SECONDS*1.2)  # Timeout threshold in a minutes

    inactive_devices = {}
    active_devices = {}

    for device_id, status in device_status.items():
        last_time = status['last_time']
        diff_time = (now - last_time)
        if diff_time > timeout:
            inactive_devices[device_id] = status    # Group: inactiveDevices
            print(status)
        else:
            active_devices[device_id] = status  # Group: activeDevice

    if active_devices:
        print("Active devices:")
        for device_id, status in active_devices.items():
            print(f"  {device_id}: {status}")

    if inactive_devices:
        print("!Inactive devices:")
        for device_id, status in inactive_devices.items():
            print(f"  {device_id}: {status}")


# Background thread to check inactive devices periodically
def monitor_inactive_devices():
    while True:
        time.sleep(INTERVAL_SECONDS)  # Check every INTERVAL_SECONDS
        check_inactive_devices()  # Check and handle inactive devices


# Start background thread
threading.Thread(target=monitor_inactive_devices, daemon=True).start()

if __name__ == "__main__":
    app.run(host=LOCAL_HOST_IP, port=PORT)

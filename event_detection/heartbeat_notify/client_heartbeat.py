import requests
import time
import json

LOCAL_HOST_IP = "127.0.0.1"
PORT = "5000"
DEVICE_ID = "device_1"
SERVER_URL = f"http://{LOCAL_HOST_IP}:{PORT}"


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

def heartbeat_sender(Bwim_process_status):
    while True:
        
        # Wait until the server is ready
        is_server_ready(SERVER_URL)

        try:
            playload={}
            playload["device_status"] = {}
            playload["device_status"] = json.dumps(Bwim_process_status, default=lambda obj: obj.__dict__, indent=4)
            playload["device_id"]= DEVICE_ID
            response = requests.post(f"{SERVER_URL}/heartbeat",
                headers={'Content-Type': 'application/json'}, json=playload,)
            
            print(f"DEVICE_ID: {DEVICE_ID} Heartbeat sent.      res: {response.json()}")
        except Exception as e:
            print(f"Failed to send heartbeat: {e}      res: {response.json()}")

        time.sleep(10)  # Send heartbeat every 10 seconds

if __name__ == "__main__":
    heartbeat_sender({})
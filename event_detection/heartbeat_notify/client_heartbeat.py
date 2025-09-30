from dotenv import dotenv_values
import requests
import time
import json


PATH_ENV_HB_CLIENT = ".env-heartbeat-client"
ENV_HB_CLIENT = dotenv_values(PATH_ENV_HB_CLIENT)
DEVICE_ID = ENV_HB_CLIENT.get("DEVICE_ID", "unknown")
AUTH_TOKEN = ENV_HB_CLIENT["TOKEN"]
SERVER_ENDPOINT = ENV_HB_CLIENT["SERVER_ENDPOINT"]
HEARTBEAT_SEC = int(ENV_HB_CLIENT.get("HEARTBEAT_SEC", 10))
RETRY_SEC = int(ENV_HB_CLIENT.get("RETRY_SEC", 5))



def is_server_ready(url_endpoint, timeout=5):
    while True:
        try:
            response = requests.get(url_endpoint, timeout=timeout, headers={
                'Authorization': f'Bearer {AUTH_TOKEN}'
            })
            if response.status_code == 200:
                print("✅ Server is UP! Starting heartbeat...")
                return True
            if response.status_code == 401:
                print(f"❌ Unauthorized. Please check your token. {response.json()}")
        except requests.ConnectionError:
            print("❌ Server is DOWN. Retrying in 5 seconds...")
        except requests.Timeout:
            print("⚠️ Server timed out. Retrying...")

        time.sleep(RETRY_SEC)  # Wait before retrying


def heartbeat_sender(Bwim_process_status):
    while True:
        post_request_heartbeat(Bwim_process_status)
        time.sleep(HEARTBEAT_SEC)  # Send heartbeat every 10 seconds


def post_request_heartbeat(Bwim_process_status, Trigger_bwim_process_status=None):
    # Wait until the server is ready
    is_server_ready(SERVER_ENDPOINT)

    try:
        playload={}
        playload["device_status"] = Bwim_process_status
        # playload["device_status"] = json.dumps(Bwim_process_status, default=lambda obj: obj.__dict__, indent=4)
        if Trigger_bwim_process_status:
            playload["trigger_status"] = Trigger_bwim_process_status
        playload["device_id"] = DEVICE_ID
        playload["max_next_pulse_sec"] = HEARTBEAT_SEC
        response = requests.post(f"{SERVER_ENDPOINT}/heartbeat", timeout=5,
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {AUTH_TOKEN}'}, json=playload,)
        
        print(f"DEVICE_ID: {DEVICE_ID} Heartbeat sent.      res: {response.json()}")
    except Exception as e:
        print(f"Failed to send heartbeat: {e}      res: {response.json()}")
    return None


def get_error_last(device_ids=None):
    url = f"{SERVER_ENDPOINT}/error_last"
    headers = {
        'Authorization': f'Bearer {AUTH_TOKEN}'
    }
    params = {}
    if device_ids is not None:
        params['device_ids'] = json.dumps(device_ids)
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            print("error_last response:", response.json())
            return response.json()
        else:
            print(f"Failed to get error_last: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Exception during get_error_last: {e}")
    return None

# def error_reporting(error_detected_log):
#     # Wait until the server is ready
#     is_server_ready(SERVER_ENDPOINT)

#     try:
#         playload={}
#         playload["device_status"] = {}
#         playload["device_status"] = json.dumps(Bwim_process_status, default=lambda obj: obj.__dict__, indent=4)
#         playload["device_id"]= DEVICE_ID
#         response = requests.post(f"{SERVER_ENDPOINT}/heartbeat",
#             headers={'Content-Type': 'application/json'}, json=playload,)
        
#         print(f"DEVICE_ID: {DEVICE_ID} Heartbeat sent.      res: {response.json()}")
#     except Exception as e:
#         print(f"Failed to send heartbeat: {e}      res: {response.json()}")


if __name__ == "__main__":
    pass
    # heartbeat_sender({})

    post_request_heartbeat({},{"algorithm_status": "OK"})
    time.sleep(10)
    post_request_heartbeat({},{})
    time.sleep(10)
    post_request_heartbeat({},{"algorithm_status": "OK"})
    time.sleep(60*8)
    post_request_heartbeat({},{"algorithm_status": "OK"})
    time.sleep(10)
    post_request_heartbeat({},{"algorithm_status": "OK"})
    time.sleep(10)
    post_request_heartbeat({},{"algorithm_status": "NOT_OK"})
    time.sleep(10)
    post_request_heartbeat({},{"algorithm_status": "NOT_OK"})
    time.sleep(10)
    post_request_heartbeat({},{"algorithm_status": "NOT_OK"})
    time.sleep(10)
    post_request_heartbeat({},{"algorithm_status": "OK"})
    time.sleep(10)
    post_request_heartbeat({},{"algorithm_status": "NOT_OK"})
    time.sleep(10)
    post_request_heartbeat({},{"algorithm_status": "OK"})
    time.sleep(10)
    post_request_heartbeat({},{"algorithm_status": "NOT_OK"})



    # get_error_last()
    # get_error_last("loadtest-pc")
    # get_error_last(["loadtest-pc","device_1"])
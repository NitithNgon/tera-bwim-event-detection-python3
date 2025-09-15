import os
from datetime import datetime
from dotenv import dotenv_values
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


PATH_ENV_HB_SERVER = ".env-heartbeat-server"
ENV_HB_SERVER = dotenv_values(PATH_ENV_HB_SERVER)
OAUTH_TOKEN = ENV_HB_SERVER.get("OAUTH_TOKEN")
CHANNEL = ENV_HB_SERVER.get("CHANNEL")
DATETIME_FORMAT_NOTIFY = "%Y-%m-%d %H:%M:%S"

# slack_token = os.environ["SLACK_BOT_TOKEN"]
slack_token = OAUTH_TOKEN
client = WebClient(token=slack_token)


def strftime_format(datetime_db: datetime):
    return datetime_db.strftime(DATETIME_FORMAT_NOTIFY)


def device_property(log_type: int) -> str:
    match(log_type):
        case 0:
            device_property = ""
        case 1:
            device_property = "'s (strain sampling rate)"
        case _:
            device_property = "unknow"
    return device_property


def send_slack_message(device, log_type, status):
    main_text = f"{strftime_format(device.last_time)} | ({device.device_id}){device_property(log_type)} is ({status})"
    last_device_logs = device.last_device_logs
    if last_device_logs != []:
        main_text += "\n"
        main_text += "Last Logs"
        for device_log in last_device_logs:
            main_text += "\n"
            start_time = strftime_format(device_log.start_time)
            end_time = strftime_format(device_log.end_time)
            main_text += f"{start_time} to {end_time} | duration: {device_log.duration} | ({device.device_id}){device_property(device_log.log_type)} is ({device_log.status})"

    print(main_text)
    try:
        response = client.chat_postMessage(
            channel=CHANNEL,
            text=main_text
        )
        return response
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["error"]    # str like 'invalid_auth', 'channel_not_found'

# Example usage:
# send_slack_message("C09CHAG79M1", "test1234")
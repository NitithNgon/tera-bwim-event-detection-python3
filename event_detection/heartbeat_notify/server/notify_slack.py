import os
from datetime import datetime, timedelta
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

DEVICE_PROPERTY_MESSAGE_DICT = {
    0: "",
    1: "'s (strain sampling rate)",
    2: "'s (most algorithm return code status)",
}


def format_duration(td: timedelta):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def format_sec(td: timedelta):
    return int(td.total_seconds())


def strftime_format(datetime_db: datetime):
    return datetime_db.strftime(DATETIME_FORMAT_NOTIFY)


def device_property(log_type: int) -> str:
    device_property_message = DEVICE_PROPERTY_MESSAGE_DICT.get(log_type, "")
    return device_property_message


def additional_text(log_type, device) -> str:
    additional_text_message=""
    match(log_type):
        case 1:
            device_status = device.device_status
            if device_status.actual_buffering_data_time and device_status.expected_buffering_data_time:
                actual_buffering_data_time = format_sec(device_status.actual_buffering_data_time)
                expected_buffering_data_time = format_sec(device_status.expected_buffering_data_time)
                time_ratio = actual_buffering_data_time/expected_buffering_data_time
                time_ratio = 1/time_ratio if time_ratio<0 else time_ratio
                additional_text_message = f" {time_ratio:02f}X"
                additional_text_message += f"\n\ttime using for buffering_data {format_sec(device_status.actual_buffering_data_time)} sec, expacted {format_sec(device_status.expected_buffering_data_time)} sec"
        case 2:
            staging_device_status = device.device_status.staging
            additional_text_message = f"\n\tcontinuously {staging_device_status.amount_algorithm_status} times in {format_duration(staging_device_status.time_range_algorithm_status)}"
        case _:
            pass
    return additional_text_message


def additional_text_last_log(log_type, log) -> str:
    additional_text_message=""
    match(log_type):
        case 1:
            if log.actual_buffering_data_time and log.expected_buffering_data_time:
                actual_buffering_data_time = format_sec(log.actual_buffering_data_time)
                expected_buffering_data_time = format_sec(log.expected_buffering_data_time)
                time_ratio = actual_buffering_data_time/expected_buffering_data_time
                time_ratio = 1/time_ratio if time_ratio<0 else time_ratio
                additional_text_message = f" {time_ratio:02f}X"
            additional_text_message = f"\n\ttime using for buffering_data {format_sec(log.actual_buffering_data_time)} sec, expacted {format_sec(log.expected_buffering_data_time)} sec"

        case 2:
            additional_text_message = f"\n\tcontinuously {log.cum_amount_most_algorithm_status} times in {format_duration(log.cum_time_range_most_algorithm_status)}"
        case _:
            pass
    return additional_text_message


def send_slack_message(device, log_type, status):
    main_text = f"{strftime_format(device.last_time)} | ({device.device_id}){device_property(log_type)} is ({status}){additional_text(log_type, device)}"
    last_device_logs = device.last_device_logs
    if last_device_logs != []:
        main_text += "\n"
        main_text += "After"
        for device_log in last_device_logs:
            main_text += "\n"
            start_time = strftime_format(device_log.start_time)
            end_time = strftime_format(device_log.end_time)
            main_text += f"{start_time} to {end_time} | duration: {format_duration(device_log.duration)} | ({device.device_id}){device_property(device_log.log_type)} is ({device_log.status}){additional_text_last_log(device_log.log_type, device_log)}"

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
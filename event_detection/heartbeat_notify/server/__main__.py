from math import e
import threading
import time
import os
import json
from functools import wraps
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import inspect
from flask_sqlalchemy import SQLAlchemy
from dotenv import dotenv_values
from event_detection.heartbeat_notify.server.db import db, DATETIME_FORMAT
from event_detection.heartbeat_notify.server.models import *
from event_detection.heartbeat_notify.server.notify_slack import send_slack_message
from event_detection.heartbeat_notify.server.models.db_schedule import initialize_scheduler, get_scheduler, stop_scheduler, DatabaseScheduler


PATH_ENV_HB_SERVER = ".env-heartbeat-server"
ENV_HB_SERVER = dotenv_values(PATH_ENV_HB_SERVER)
TOKEN_LIST = json.loads(ENV_HB_SERVER["TOKEN_LIST"])
LOCAL_HOST_IP = ENV_HB_SERVER.get("LOCAL_HOST_IP")
PORT = ENV_HB_SERVER.get("PORT")
INTERVAL_SECONDS = int(ENV_HB_SERVER.get("INTERVAL_SECONDS", 10))



#### Bearer Token Authentication 

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        # Accept "Bearer <token>" or just "<token>"
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = auth_header
        if not token or token not in TOKEN_LIST:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def patch_routes_with_auth(app):
    for rule in app.url_map.iter_rules():
        endpoint = app.view_functions[rule.endpoint]
        if rule.endpoint != 'static' and not getattr(endpoint, '_auth_wrapped', False):
            wrapped = require_auth(endpoint)
            wrapped._auth_wrapped = True
            app.view_functions[rule.endpoint] = wrapped



#### Setup Flask Server, SQLAlchemy DB

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.sqlite'  # default db
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(BASE_DIR, 'db')
os.makedirs(db_dir, exist_ok=True)
app.config['SQLALCHEMY_BINDS'] = {
    'heartbeat_db': f"sqlite:///{os.path.join(db_dir, 'heartbeat_db.sqlite')}",
    'error_report_db': f"sqlite:///{os.path.join(db_dir, 'error_report_db.sqlite')}",
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable SQLAlchemy's event system monitors changes of Obj to emit event signal 
db.init_app(app)
with app.app_context():
    db.create_all(bind_key='heartbeat_db')
    db.create_all(bind_key='error_report_db')
    heartbeat_engine = db.engines['heartbeat_db']
    error_report_engine = db.engines['error_report_db']
    print("heartbeat_db tables:", inspect(heartbeat_engine).get_table_names())
    print("error_report_db tables:", inspect(error_report_engine).get_table_names())
    patch_routes_with_auth(app)
    
    archive_path = os.path.join(BASE_DIR, 'archive')
    scheduler = initialize_scheduler(
        app,
        archive_path=archive_path,
        schedule_days=7,
        schedule_hour=2
    )


#### REST API

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Server is running"}), 200


# curl -X POST -H "Authorization: Bearer your_token" http://localhost:5000/archive/cleanup
@app.route('/archive/cleanup', methods=['POST'])
def force_cleanup():
    scheduler: DatabaseScheduler = get_scheduler()
    if scheduler:
        scheduler.force_cleanup()
        return jsonify({"message": "Cleanup completed"}), 200
    return jsonify({"error": "Scheduler not running"}), 500


@app.route('/error_last', methods=['GET'])
def error_last():
    # Get device_ids from query parameters, e.g. /error_last?device_ids=device1,device2
    device_ids = request.args.get('device_ids', None)
    device_ids = json.loads(device_ids) if device_ids else None
    if not isinstance(device_ids, list) and device_ids:
        device_ids = [device_ids]
    print(device_ids, type(device_ids))
    if device_ids:
        print(f"Filtering for device_ids: {device_ids}")
        # query only device_ids
        subquery = (
            db.session.query(
                ErrorReport.device_id,
                db.func.max(ErrorReport.date_time).label("max_time")
            )
            .filter(ErrorReport.device_id.in_(device_ids))
            .group_by(ErrorReport.device_id)
            .subquery()
        )
    else:
        # Consider all devices
        subquery = (
            db.session.query(
                ErrorReport.device_id,
                db.func.max(ErrorReport.date_time).label("max_time")
            )
            .group_by(ErrorReport.device_id)
            .subquery()
        )

    # Main query: filter by device_ids if provided
    query = db.session.query(ErrorReport).join(
        subquery,
        (ErrorReport.device_id == subquery.c.device_id) &
        (ErrorReport.date_time == subquery.c.max_time)
    )
    latest_errors = query.all()
    if latest_errors:
        print(type(latest_errors[0]), latest_errors[0])
    else:
        print("No error reports found.")
    result = [err.to_dict() for err in latest_errors]
    return jsonify(result), 200


@app.route('/error', methods=['POST'])
def error_report():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400
    print(data)
    error_code = data.get('error_code')
    device_id = data.get('device_id')
    date_time_str = data.get('date_time')
    error_report = data.get('error_report', {})
    date_time = datetime.strptime(date_time_str, DATETIME_FORMAT)
    date_time_code = date_time.strftime("%Y%m%d_%H%M%S")
    error_id = f"{device_id}_{date_time_code}_{error_code}"
    error_report_dict = {
        "error_id": error_id,
        "device_id": device_id,
        "error_code": error_code,
        "date_time": date_time,
        "error_report": error_report
    }

    if device_id:
        error_report = ErrorReport(**error_report_dict)
        db.session.add(error_report)
        db.session.commit()
        print(f"Error report saved: {error_report}")
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"error": "No device_id provided"}), 400


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400 
    print(data)
    device_id = data.get('device_id')
    max_next_pulse_sec = data.get('max_next_pulse_sec', 10)
    status_data = data.get('device_status', {})
    bwim_flag = status_data.pop("Flag_data", {})
    trigger_status = data.get('trigger_status', {})
    all_status = {**status_data, **bwim_flag, **trigger_status}

    if device_id:
        device = Heartbeat.query.filter_by(device_id=device_id).first()
        if device:
            device.last_time = datetime.now()
            device.max_next_pulse_sec = int(max_next_pulse_sec)
        else:
            device = Heartbeat(device_id=device_id, last_time=datetime.now(), max_next_pulse_sec=int(max_next_pulse_sec))
            db.session.add(device)
        db.session.flush()

        device_status = device.device_status
        if device_status:
            for column in DeviceStatus.__table__.columns:
                if column.name != 'device_id':  # Skip primary key
                    if column.name in all_status:
                        value = all_status[column.name]
                    else:
                        value = column.default.arg if column.default else column.default
                    setattr(device_status, column.name, value)
        else:
            device_status = DeviceStatus(device_id=device_id, **all_status)
            db.session.add(device_status)
        db.session.commit()
        save_device_status_to_new_log(device, device_status)
        db.session.commit()
        
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"error": "No device_id provided"}), 400



#### Background functions

def check_inactive_devices():
    with app.app_context():
        now = datetime.now()
        # timeout = timedelta(seconds=INTERVAL_SECONDS * 1.2)
        all_devices = Heartbeat.query.all()
        for device in all_devices:
            device: Heartbeat = device
            diff_time = now - device.last_time
            timeout = timedelta(seconds=device.max_next_pulse_sec * 1.2)
            
            device.active_status = diff_time <= timeout
            active_status_log = "online" if device.active_status else "offline"
            move_device_log_next_stage(device, log_type=0, status=active_status_log)

        db.session.commit()
        # inactive_devices = Heartbeat.query.filter_by(active_status=False).all()
        # result = [device.to_dict() for device in inactive_devices]
        # print("Inactive devices:")
        # print(result)


def save_device_status_to_new_log(device: Heartbeat, device_status: DeviceStatus):
    log_type_log_status_dict = {}

    # log_type 1
    match(device_status.strain_sampling_rate_status):
        case "SLOW":
            log_type_log_status_dict[1] = "slow_strain_sampling_rate"
        case "OK":
            # log_type_log_status_dict[1] = "ok"
            log_type_log_status_dict[1] = "fast_strain_sampling_rate"
        case _:
            pass

    # log_type 2
    algorithm_status = device_status.algorithm_status
    if algorithm_status in ("OK", "NOT_OK"):
        amount_algorithm_status, time_range_algorithm_status = algorithm_status_count(device_status, device)
        print(amount_algorithm_status, time_range_algorithm_status)
        if majority_algorithm_statuses_meet_criteria(
            amount_algorithm_status,
            time_range_algorithm_status,
            reduction_factor=2 if algorithm_status == "OK" else 1,
            time_range_factor=1.5 if algorithm_status == "OK" else 1,
        ):
            
            log_type_log_status_dict[2] = "return_normal_codes" if algorithm_status == "OK" else "return_multiple_0_codes"
        else:
            current_link: HeartbeatLogLink = device.current_links.filter_by(log_type=2).first()
            staging_device_status: StagingDeviceStatus = device_status.staging
            if current_link and staging_device_status:
                if staging_device_status.last_staging_algorithm_status == current_link.device_log.most_algorithm_status:
                    reset_algorithm_status_count(device_status, device)
                    set_last_cum_algorithm_status_count(current_link.device_log)
                    db.session.flush()

    # log_type 3

    for log_type, log_status in log_type_log_status_dict.items():
        move_device_log_next_stage(device, log_type, log_status)


def move_device_log_next_stage(device: Heartbeat, log_type: int, status: str):
    current_link: HeartbeatLogLink = device.current_links.filter_by(log_type=log_type).first()
    if current_link:
        current_device_log: DeviceLog = current_link.device_log
        if status == current_device_log.status:
            is_update = updata_current_device_log(current_device_log, device.device_status)
            if is_update:
                db.session.flush()
            return
        close_current_device_log(current_device_log, device)
        db.session.flush()
    if status != "ok":
        response = send_slack_message(device, log_type, status)
        device.notification_sent = response.get("ok", False)
        new_log = initialize_device_log(device, device.device_status, log_type, status)
        device.current_device_logs.append(new_log)
        db.session.flush()  # make sure updated rows visible to queries
    return


# def server_self_check():
#     with app.app_context():
#         now = datetime.now()
#         timeout = timedelta(seconds=INTERVAL_SECONDS * 1.2)
#         server_device = Heartbeat.query.filter_by(device_id="server_self_check").first()
#         if server_device:
#             diff_time = now - server_device.last_time
#             if diff_time > timeout:
#                 print("Server self-check failed. Sending notification.")
#                 send_slack_message("Server self-check failed. No heartbeat received.")
#         else:
#             # Create the server self-check entry if it doesn't exist
#             server_device = Heartbeat(device_id="server_self_check", last_time=now, active_status=True)
#             db.session.add(server_device)
#             db.session.commit()


# Background thread to check inactive devices periodically
def monitor_inactive_devices():
    while True:
        time.sleep(INTERVAL_SECONDS)  # Check every INTERVAL_SECONDS
        # server_self_check()
        check_inactive_devices()  # Check and handle inactive devices


def shutdown_handler():
    print("Shutting down database scheduler...")
    stop_scheduler()
    print("Database scheduler stopped")


import atexit
atexit.register(shutdown_handler)

threading.Thread(target=monitor_inactive_devices, daemon=True).start()


if __name__ == "__main__":
    try:
        app.run(host=LOCAL_HOST_IP, port=PORT)
    except KeyboardInterrupt:
        print("Server shutting down...")
        shutdown_handler()

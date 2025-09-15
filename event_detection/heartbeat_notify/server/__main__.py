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


PATH_ENV_HB_SERVER = ".env-heartbeat-server"
ENV_HB_SERVER = dotenv_values(PATH_ENV_HB_SERVER)
TOKEN_LIST = json.loads(ENV_HB_SERVER["TOKEN_LIST"])
LOCAL_HOST_IP = ENV_HB_SERVER.get("LOCAL_HOST_IP")
PORT = ENV_HB_SERVER.get("PORT")
INTERVAL_SECONDS = int(ENV_HB_SERVER.get("INTERVAL_SECONDS", 10))


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


app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.sqlite'  # default db
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(BASE_DIR, 'db')
os.makedirs(db_dir, exist_ok=True)
app.config['SQLALCHEMY_BINDS'] = {
    'heartbeat_db': f"sqlite:///{os.path.join(db_dir, 'heartbeat_db.sqlite')}",
    'error_report_db': f"sqlite:///{os.path.join(db_dir, 'error_report_db.sqlite')}",
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable SQLAlchemy’s event system monitors changes of Obj to emit event signal 
db.init_app(app)
with app.app_context():
    db.create_all(bind_key='heartbeat_db')
    db.create_all(bind_key='error_report_db')

    heartbeat_engine = db.engines['heartbeat_db']
    error_report_engine = db.engines['error_report_db']
    print("heartbeat_db", inspect(heartbeat_engine).get_table_names())
    print("error_report_db", inspect(error_report_engine).get_table_names())

    patch_routes_with_auth(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Server is running"}), 200


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
    status_data = data.get('device_status', {})
    bwim_flag = status_data.pop("Flag_data", {})
    all_status = {**status_data, **bwim_flag}
    
    if device_id:
        heartbeat = Heartbeat.query.filter_by(device_id=device_id).first()
        if heartbeat:
            heartbeat.last_time = datetime.now()
        else:
            heartbeat = Heartbeat(device_id=device_id, last_time=datetime.now())
            db.session.add(heartbeat)
        db.session.commit()

        device_status = DeviceStatus.query.filter_by(device_id=device_id).first()
        if device_status:
            for key, value in all_status.items():
                if hasattr(device_status, key):
                    setattr(device_status, key, value)
        else:
            device_status = DeviceStatus(device_id=device_id, **all_status)
            db.session.add(device_status)
        db.session.commit()

        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"error": "No device_id provided"}), 400


def check_inactive_devices():
    with app.app_context():
        now = datetime.now()
        timeout = timedelta(seconds=INTERVAL_SECONDS * 1.2)
        all_devices = Heartbeat.query.all()
        for device in all_devices:
            device: Heartbeat = device
            diff_time = now - device.last_time
            
            device.active_status = diff_time <= timeout
            active_status_log = "online" if device.active_status else "offline"
            move_device_log_next_stage(device, log_type=0, status=active_status_log)
            save_device_status_to_new_log(device, device.device_status)

            db.session.add(device)

        db.session.commit()

        inactive_devices = Heartbeat.query.filter_by(active_status=False).all()
        result = [device.to_dict() for device in inactive_devices]
        print("Inactive devices:")
        print(result)


def save_device_status_to_new_log(device: Heartbeat, device_status: DeviceStatus):
    
    log_type_log_status_dict = {}
    
    # log_type 1
    match(device_status.strain_sampling_rate_status):
        case "SLOW":
            log_type_log_status_dict[1] = "slow_strain_sampling_rate"
        case "OK":
            # log_type_log_status_dict[1] = "ok"
            log_type_log_status_dict[1] = "normal"

    # log_type 2

    for log_type, log_status in log_type_log_status_dict.items():
        move_device_log_next_stage(device, log_type, log_status)



def move_device_log_next_stage(device: Heartbeat, log_type: int, status: str):
    current_link = device.current_links.filter_by(log_type=log_type).first()
    if current_link:
        current_device_log = current_link.device_log
        if status == current_device_log.status:
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

def server_self_check():
    with app.app_context():
        now = datetime.now()
        timeout = timedelta(seconds=INTERVAL_SECONDS * 3)
        server_device = Heartbeat.query.filter_by(device_id="server_self_check").first()
        if server_device:
            diff_time = now - server_device.last_time
            if diff_time > timeout:
                print("Server self-check failed. Sending notification.")
                send_slack_message("Server self-check failed. No heartbeat received.")
        else:
            # Create the server self-check entry if it doesn't exist
            server_device = Heartbeat(device_id="server_self_check", last_time=now, active_status=True)
            db.session.add(server_device)
            db.session.commit()


# Background thread to check inactive devices periodically
def monitor_inactive_devices():
    while True:
        time.sleep(INTERVAL_SECONDS)  # Check every INTERVAL_SECONDS
        check_inactive_devices()  # Check and handle inactive devices
        # server_self_check()



threading.Thread(target=monitor_inactive_devices, daemon=True).start()

if __name__ == "__main__":
    app.run(host=LOCAL_HOST_IP, port=PORT)

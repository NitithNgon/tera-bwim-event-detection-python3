import time
from event_detection.heartbeat_notify.server.db import db, BaseModel
from datetime import datetime, timedelta
from dotenv import dotenv_values


PATH_ENV_HB_SERVER = ".env-heartbeat-server"
ENV_HB_SERVER = dotenv_values(PATH_ENV_HB_SERVER)
MIN_LIMIT_ALGORITHM_STATUS_COUNT = int(ENV_HB_SERVER.get("MIN_LIMIT_ALGORITHM_STATUS_COUNT",3))
MAX_LIMIT_ALGORITHM_STATUS_TIME_RANGE_MINUTE = int(ENV_HB_SERVER.get("MAX_LIMIT_ALGORITHM_STATUS_TIME_RANGE_MINUTE",5))

class DeviceStatus(BaseModel):
    __bind_key__ = 'heartbeat_db'
    __tablename__ = 'device_status'
    device_id = db.Column(db.String(100), db.ForeignKey('heartbeat.device_id'), primary_key=True)

    # Fields from Currently_bwim_process_status
    expected_buffering_data_time = db.Column(db.Interval, default=None)  # timedelta
    actual_buffering_data_time = db.Column(db.Interval, default=None)
    strain_sampling_rate_status = db.Column(db.String(50), default=None)
    last_record_time = db.Column(db.DateTime, default=None)
    last_event_time = db.Column(db.DateTime, default=None)

    # Flattened fields from Bwim_flag
    system_shutdown = db.Column(db.Integer, default=0)
    event_1_triggered = db.Column(db.Integer, default=0)
    event_2_triggered = db.Column(db.Integer, default=0)
    event_3_triggered = db.Column(db.Integer, default=0)
    event_4_triggered = db.Column(db.Integer, default=0)
    lpr_summary = db.Column(db.Integer, default=0)
    event_backup = db.Column(db.Integer, default=0)

    # Fields from Trigger_bwim_process_status
    algorithm_status = db.Column(db.String(50), default=None)
    

    def __repr__(self):
        return f"<device: {self.device_id} actual_buffering_data_time: {self.actual_buffering_data_time} strain_sampling_rate_status: {self.strain_sampling_rate_status} system_shutdown: {self.system_shutdown}>"


# Staging data that need to check some condition frist
# before move to device_log
class StagingDeviceStatus(BaseModel):
    __bind_key__ = 'heartbeat_db'
    __tablename__ = 'staging_device_status'

    device_id = db.Column(db.String(100), db.ForeignKey('device_status.device_id'), primary_key=True)
    last_staging_algorithm_status = db.Column(db.String(50), nullable=False)
    amount_algorithm_status = db.Column(db.Integer, default=1, nullable=False)
    start_time_algorithm_status = db.Column(db.DateTime, nullable=False)
    time_range_algorithm_status = db.Column(db.Interval, default=None)
    

    # 1-to-0/1 relationship
    device_status = db.relationship('DeviceStatus', backref=db.backref('staging', uselist=False))

def algorithm_status_count(device_status: DeviceStatus, device):
    staging_device_status: StagingDeviceStatus = device_status.staging
    if staging_device_status:
        if staging_device_status.last_staging_algorithm_status == device_status.algorithm_status:
            staging_device_status.amount_algorithm_status += 1
            staging_device_status.time_range_algorithm_status = datetime.now() - staging_device_status.start_time_algorithm_status
        else:
            # reset count
            new_algorithm_status_count(device_status, device, staging_device_status)
    else:
        # init count
        staging_device_status = StagingDeviceStatus(
            device_id=device_status.device_id,
            last_staging_algorithm_status=device_status.algorithm_status,
            amount_algorithm_status=1,
            start_time_algorithm_status=device.last_time,
        )
        db.session.add(staging_device_status)
    db.session.flush()
    return staging_device_status.amount_algorithm_status, staging_device_status.time_range_algorithm_status


def new_algorithm_status_count(device_status: DeviceStatus, device, staging_device_status: StagingDeviceStatus):
    staging_device_status.last_staging_algorithm_status = device_status.algorithm_status
    staging_device_status.amount_algorithm_status = 1
    staging_device_status.start_time_algorithm_status = device.last_time
    staging_device_status.time_range_algorithm_status = None


def reset_algorithm_status_count(device_status: DeviceStatus, device):
    staging_device_status: StagingDeviceStatus = device_status.staging
    if staging_device_status:
        new_algorithm_status_count(device_status, device, staging_device_status)


def majority_algorithm_statuses_meet_criteria(amount_algorithm_status, time_range_algorithm_status, reduction_factor=1, time_range_factor=1) -> bool:
    if time_range_algorithm_status:
        amount_criteria = amount_algorithm_status >= MIN_LIMIT_ALGORITHM_STATUS_COUNT/reduction_factor
        time_range_criteria = time_range_algorithm_status < timedelta(minutes=MAX_LIMIT_ALGORITHM_STATUS_TIME_RANGE_MINUTE * time_range_factor)
        return amount_criteria and time_range_criteria
    else:
        return False 
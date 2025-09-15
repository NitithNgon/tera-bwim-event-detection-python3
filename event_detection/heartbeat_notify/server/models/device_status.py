from event_detection.heartbeat_notify.server.db import db, BaseModel

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

    def __repr__(self):
        return f"<device: {self.device_id} actual_buffering_data_time: {self.actual_buffering_data_time} strain_sampling_rate_status: {self.strain_sampling_rate_status} system_shutdown: {self.system_shutdown}>"

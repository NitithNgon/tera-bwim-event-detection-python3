from event_detection.heartbeat_notify.server.db import db, BaseModel
from sqlalchemy.ext.associationproxy import association_proxy
from datetime import datetime, timedelta
from event_detection.heartbeat_notify.server.models.device_status import DeviceStatus


class Heartbeat(BaseModel):
    __bind_key__ = 'heartbeat_db'
    __tablename__ = 'heartbeat'

    device_id = db.Column(db.String, primary_key=True)
    last_time = db.Column(db.DateTime, nullable=False)
    max_next_pulse_sec = db.Column(db.Integer, nullable=False)
    active_status = db.Column(db.Boolean, default=True)
    notification_sent = db.Column(db.Boolean, default=False)

    # Relationship to DeviceStatus (one-to-one)
    device_status = db.relationship("DeviceStatus", backref="heartbeat", uselist=False)


    # Association-object relationships
    log_links = db.relationship(
        "HeartbeatLogLink",
        back_populates="heartbeat",
        cascade="all, delete-orphan",
        lazy='dynamic',
        overlaps="current_links,last_links",
    )

    # link rows filtered by kind
    current_links = db.relationship(
        "HeartbeatLogLink",
        primaryjoin="and_(Heartbeat.device_id==HeartbeatLogLink.heartbeat_id, HeartbeatLogLink.link_kind=='current')",
        cascade="all, delete-orphan",
        lazy='dynamic',
        overlaps="log_links,last_links",
    )
    last_links = db.relationship(
        "HeartbeatLogLink",
        primaryjoin="and_(Heartbeat.device_id==HeartbeatLogLink.heartbeat_id, HeartbeatLogLink.link_kind=='last')",
        cascade="all, delete-orphan",
        lazy='dynamic',
        overlaps="log_links,current_links",
    )

    # proxy real logs; creator builds the link row for you
    current_device_logs = association_proxy(
        'current_links', 'device_log',
        creator=lambda log: HeartbeatLogLink(device_log=log, log_type=log.log_type, link_kind='current')
    )
    last_device_logs = association_proxy(
        'last_links', 'device_log',
        creator=lambda log: HeartbeatLogLink(device_log=log, log_type=log.log_type, link_kind='last')
    )

    def __repr__(self):
        return f"<Heartbeat(device_id={self.device_id}, last_time={self.last_time}, active_status={self.active_status}, notification_sent={self.notification_sent})>"


# Association object
class HeartbeatLogLink(BaseModel):
    __bind_key__ = 'heartbeat_db'
    __tablename__ = 'heartbeat_log_link'

    log_id = db.Column(db.Integer, db.ForeignKey('device_log.log_id', ondelete='CASCADE'), primary_key=True, nullable=False, index=True)
    heartbeat_id = db.Column(db.String, db.ForeignKey('heartbeat.device_id', ondelete='CASCADE'), nullable=False, index=True)
    log_type = db.Column(db.Integer, nullable=False, index=True)
    link_kind = db.Column(db.String, nullable=False)

    # Relationships
    heartbeat = db.relationship('Heartbeat', back_populates='log_links', overlaps="current_links,last_links")
    device_log = db.relationship('DeviceLog', foreign_keys=[log_id], primaryjoin="DeviceLog.log_id==HeartbeatLogLink.log_id")


class DeviceLog(BaseModel):
    __bind_key__ = 'heartbeat_db'
    __tablename__ = 'device_log'

    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    log_type = db.Column(db.Integer, default=0)
    status = db.Column(db.String(255), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Interval, nullable=True)

    # Fields from Heartbeat
    device_id = db.Column(db.String, db.ForeignKey('heartbeat.device_id'), nullable=False)
    last_time = db.Column(db.DateTime, nullable=False)
    max_next_pulse_sec = db.Column(db.Integer, nullable=False)
    active_status = db.Column(db.Boolean, default=True)
    notification_sent = db.Column(db.Boolean, default=False)

    # Fields from DeviceStatus
    expected_buffering_data_time = db.Column(db.Interval, default=None)
    actual_buffering_data_time = db.Column(db.Interval, default=None)
    strain_sampling_rate_status = db.Column(db.String(50), default=None)
    last_record_time = db.Column(db.DateTime, default=None)
    last_event_time = db.Column(db.DateTime, default=None)
    system_shutdown = db.Column(db.Integer, default=0)
    event_1_triggered = db.Column(db.Integer, default=0)
    event_2_triggered = db.Column(db.Integer, default=0)
    event_3_triggered = db.Column(db.Integer, default=0)
    event_4_triggered = db.Column(db.Integer, default=0)
    lpr_summary = db.Column(db.Integer, default=0)
    event_backup = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<DeviceLog(id={self.id}, device_id={self.device_id}, active_status={self.active_status}, status={self.status}, start_time={self.start_time}, end_time={self.end_time}, duration={self.duration})>"


def initialize_device_log(heartbeat: Heartbeat, device_status: DeviceStatus, log_type: int=0, status: str|None=None):
    new_log = DeviceLog(
        log_type=log_type,
        device_id=heartbeat.device_id,
        active_status=heartbeat.active_status,
        notification_sent = heartbeat.notification_sent,
        status=status,
        start_time=datetime.now(),
        last_time=heartbeat.last_time,
        max_next_pulse_sec=heartbeat.max_next_pulse_sec,
        expected_buffering_data_time=device_status.expected_buffering_data_time,
        actual_buffering_data_time=device_status.actual_buffering_data_time,
        strain_sampling_rate_status=device_status.strain_sampling_rate_status,
        last_record_time=device_status.last_record_time,
        last_event_time=device_status.last_event_time,
        system_shutdown=device_status.system_shutdown,
        event_1_triggered=device_status.event_1_triggered,
        event_2_triggered=device_status.event_2_triggered,
        event_3_triggered=device_status.event_3_triggered,
        event_4_triggered=device_status.event_4_triggered,
        lpr_summary=device_status.lpr_summary,
        event_backup=device_status.event_backup,
    )
    db.session.add(new_log)
    return new_log


def close_current_device_log(log: DeviceLog, heartbeat: Heartbeat):
    if log.end_time is None:
        log.end_time = datetime.now()
        log.duration = log.end_time - log.start_time
        if hasattr(heartbeat, 'current_device_logs') and hasattr(heartbeat, 'last_device_logs'):
            # heartbeat.current_device_logs.remove(log)
            # heartbeat.last_device_logs.append(log)
            old_last_link = heartbeat.log_links.filter_by(link_kind='last', log_type=log.log_type).first()
            if old_last_link:
                db.session.delete(old_last_link)
            link = heartbeat.log_links.filter_by(log_id=log.log_id).first()
            link.link_kind = 'last'

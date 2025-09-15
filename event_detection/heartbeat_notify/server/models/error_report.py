from event_detection.heartbeat_notify.server.db import db, BaseModel

class ErrorReport(BaseModel):
    __bind_key__ = 'error_report_db'
    __tablename__ = 'error_report'

    error_id = db.Column(db.String, primary_key=True)
    error_code = db.Column(db.Integer, nullable=False)
    device_id = db.Column(db.String, nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    error_report = db.Column(db.JSON, nullable=True)     # store error_report dict as JSON

    # def __repr__(self):
    #     return f"<error_id: {self.error_id} error_code: {self.error_code} device: {self.device_id} time: {self.date_time} error_report: {self.error_report}>"

    # def to_dict(self):
    #     result = {}
    #     for column in self.__table__.columns:
    #         value = getattr(self, column.name)
    #         # Format datetime fields as string
    #         if isinstance(value, db.DateTime().python_type):
    #             value = value.strftime("%Y-%m-%d %H:%M:%S")
    #         result[column.name] = value
    #     return result
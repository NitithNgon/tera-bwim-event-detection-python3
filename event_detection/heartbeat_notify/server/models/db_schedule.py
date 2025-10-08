import os
import sqlite3
import schedule
import threading
import time
from datetime import datetime, timedelta
from sqlalchemy import text
from event_detection.heartbeat_notify.server.db import db
from event_detection.heartbeat_notify.server.models.heartbeat import DeviceLog, HeartbeatLogLink

SCHEDULE_DAYS = 7
SCHEDULE_HOUR = 2
ARCHIVE_PATH = "./archive"


class DatabaseScheduler:
    def __init__(self, app, archive_path=ARCHIVE_PATH, schedule_hour=SCHEDULE_HOUR, schedule_days=SCHEDULE_DAYS):
        self.app = app
        self.archive_path = archive_path
        self.schedule_hour = schedule_hour
        self.schedule_days = schedule_days
        self.running = False
        self.thread = None
        
        os.makedirs(self.archive_path, exist_ok=True)
        schedule.every(schedule_days).days.at(f"{schedule_hour:02d}:00").do(self.cleanup_and_archive)
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._schedule_loop, daemon=True)
            self.thread.start()
            print(f"Database scheduler started - cleanup runs every {self.schedule_days} days at {self.schedule_hour}:00")
    
    def stop(self):
        self.running = False
        schedule.clear()
        if self.thread:
            self.thread.join()
        print("Database scheduler stopped")
    
    def _schedule_loop(self):
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                print(f"Error in database scheduler: {e}")
                time.sleep(60)
    
    def cleanup_and_archive(self):
        try:
            with self.app.app_context():
                print("Starting database cleanup and archiving...")
                logs_to_archive = self._get_logs_to_archive()
                if logs_to_archive:
                    archived_count = self._archive_logs_to_sqlite(logs_to_archive)
                    deleted_count = self._delete_archived_logs()
                    print(f"Database cleanup completed: {archived_count} logs archived, {deleted_count} logs deleted")
                else:
                    print("No logs found for archiving")
        except Exception as e:
            print(f"Error during database cleanup: {e}")

    def _get_logs_to_archive(self):
        try:
            query = text("""
                SELECT dl.* FROM device_log dl
                LEFT JOIN heartbeat_log_link hll ON dl.log_id = hll.log_id
                WHERE hll.log_id IS NULL
                ORDER BY dl.start_time
            """)
            
            result = db.session.execute(query, bind_arguments={'bind': db.get_engine(bind_key='heartbeat_db')})
            columns = result.keys()
            logs = []
            for row in result:
                log_dict = dict(zip(columns, row))
                for key, value in log_dict.items():
                    if isinstance(value, datetime):
                        log_dict[key] = value.isoformat()
                    elif isinstance(value, timedelta):
                        log_dict[key] = value.total_seconds()
                logs.append(log_dict)
            
            return logs
        except Exception as e:
            print(f"Error getting logs to archive: {e}")
            return []
    
    def _archive_logs_to_sqlite(self, logs):
        archived_count = 0
        try:
            logs_by_month = {}
            for log in logs:
                start_time = datetime.fromisoformat(log['start_time'])
                month_key = start_time.strftime("%Y-%m")
                if month_key not in logs_by_month:
                    logs_by_month[month_key] = []
                logs_by_month[month_key].append(log)
            for month, logs_data in logs_by_month.items():
                archived_count += self._create_monthly_archive(month, logs_data)
            return archived_count
        except Exception as e:
            print(f"Error archiving logs to SQLite: {e}")
            return 0
    
    def _create_monthly_archive(self, month, logs_data):
        archive_conn = None
        archived_count = 0
        try:
            archive_filename = f"device_log_archive_{month}.db"
            archive_filepath = os.path.join(self.archive_path, archive_filename)
            archive_conn = sqlite3.connect(archive_filepath)
            archive_cursor = archive_conn.cursor()
            self._ensure_archive_table(archive_cursor, logs_data)
            for log in logs_data:
                columns = list(log.keys())
                placeholders = ', '.join(['?' for _ in columns])
                column_names = ', '.join(columns)
                archive_cursor.execute(f"""
                    INSERT OR REPLACE INTO archived_device_logs 
                    ({column_names})
                    VALUES ({placeholders})
                """, list(log.values()))
                archived_count += 1
            archive_conn.commit()
            print(f"Archived {archived_count} logs to {archive_filepath}")
            return archived_count
        except Exception as e:
            print(f"Error creating monthly archive for {month}: {e}")
            if archive_conn:
                archive_conn.rollback()
            return 0
        finally:
            if archive_conn:
                archive_conn.close()
                print(f"Closed archive database connection for {month}")
    
    def _ensure_archive_table(self, cursor, logs_data):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archived_device_logs (
                log_id INTEGER PRIMARY KEY,
                device_id TEXT NOT NULL
            )
        """)
        cursor.execute("PRAGMA table_info(archived_device_logs)")
        existing_columns = {row[1]: row[2] for row in cursor.fetchall()}
        if logs_data:
            sample_log = logs_data[0]
            for column_name, value in sample_log.items():
                if column_name not in existing_columns:
                    if isinstance(value, bool):
                        column_type = "BOOLEAN"
                    elif isinstance(value, int):
                        column_type = "INTEGER"
                    elif isinstance(value, float):
                        column_type = "REAL"
                    else:
                        column_type = "TEXT"
                    cursor.execute(f"""
                        ALTER TABLE archived_device_logs 
                        ADD COLUMN {column_name} {column_type}
                    """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_id ON archived_device_logs(device_id)
        """)
        if 'start_time' in existing_columns or (logs_data and 'start_time' in logs_data[0]):
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_start_time ON archived_device_logs(start_time)
            """)
    
    def _delete_archived_logs(self):
        try:
            query = text("""
                DELETE FROM device_log 
                WHERE log_id IN (
                    SELECT dl.log_id FROM device_log dl
                    LEFT JOIN heartbeat_log_link hll ON dl.log_id = hll.log_id
                    WHERE hll.log_id IS NULL
                )
            """)
            
            result = db.session.execute(query, bind_arguments={'bind': db.get_engine(bind_key='heartbeat_db')})
            deleted_count = result.rowcount
            db.session.commit()
            return deleted_count
        except Exception as e:
            print(f"Error deleting archived logs: {e}")
            db.session.rollback()
            return 0
        
    def force_cleanup(self):
        print("Forcing immediate database cleanup...")
        self.cleanup_and_archive()
    
    
db_scheduler = None
def initialize_scheduler(app, **kwargs):
    global db_scheduler
    if db_scheduler is None:
        db_scheduler = DatabaseScheduler(app, **kwargs)
        db_scheduler.start()
    return db_scheduler

def get_scheduler():
    return db_scheduler

def stop_scheduler():
    global db_scheduler
    if db_scheduler:
        db_scheduler.stop()
        db_scheduler = None

if __name__ == "__main__":
    pass
    # from flask import Flask
    # from event_detection.heartbeat_notify.server.db import db
    # app = Flask(__name__)
    # app.config['SQLALCHEMY_BINDS'] = {
    #     'heartbeat_db': 'sqlite:///heartbeat_db.sqlite'
    # }
    # db.init_app(app)
    # scheduler = initialize_scheduler(
    #     app,
    # )
    # try:
    #     while True:
    #         time.sleep(60)
    # except KeyboardInterrupt:
    #     print("Shutting down...")
    #     stop_scheduler()
from flask_sqlalchemy import SQLAlchemy

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

db = SQLAlchemy()

class BaseModel(db.Model):
    __abstract__ = True  # SQLAlchemy will not create a table for this class

    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, db.DateTime().python_type):
                value = value.strftime(DATETIME_FORMAT)
            result[column.name] = value
        return result
    
    def __repr__(self):
        columns = []
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            columns.append(f"{column.name}={value!r}")
        return f"<{self.__class__.__name__}({', '.join(columns)})>"
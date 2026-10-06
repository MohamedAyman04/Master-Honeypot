"""
Workstation Database Models
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """Workstation users with login credentials"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # In production: hash this!
    role = db.Column(db.String(20), default='operator')  # operator, engineer, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role
        }


class SensorReading(db.Model):
    """SCADA Historian Sensor Telemetry (Vulnerable to SQLi enumeration)"""
    __tablename__ = 'sensor_readings'

    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.String(50), nullable=False)
    sensor_name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), default='NORMAL')
    location = db.Column(db.String(80), default='CDU-01 Refinery')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'tag_id': self.tag_id,
            'sensor_name': self.sensor_name,
            'value': self.value,
            'unit': self.unit,
            'status': self.status,
            'location': self.location,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }


class SystemSecret(db.Model):
    """Honeytoken credentials planted for SQL injection discoveries"""
    __tablename__ = 'system_secrets'

    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(80), nullable=False)
    credential = db.Column(db.String(200), nullable=False)
    canary_token = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.String(200), default='RESTRICTED OT ACCESS')

    def to_dict(self):
        return {
            'id': self.id,
            'service': self.service,
            'credential': self.credential,
            'canary_token': self.canary_token,
            'notes': self.notes
        }


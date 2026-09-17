from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()


class MaintenanceWindow(db.Model):
    __tablename__ = 'maintenance_windows'

    id = db.Column(db.Integer, primary_key=True)
    component_name = db.Column(db.String(100), nullable=False)
    window_start = db.Column(db.DateTime, nullable=False)
    window_end = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), default='Scheduled')
    notes = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'component_name': self.component_name,
            'window_start': self.window_start.strftime('%Y-%m-%d %H:%M:%S'),
            'window_end': self.window_end.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'notes': self.notes,
        }

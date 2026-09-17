from flask import Flask
from pathlib import Path
from .models import db, MaintenanceWindow


def create_app():
    app = Flask(__name__, template_folder='../templates')

    repo_root = Path(__file__).resolve().parents[4]
    db_path = repo_root / 'database-files' / 'historians' / 'maintenance_times_historian.db'
    db_path.parent.mkdir(parents=True, exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'historian-2-secret-key'

    db.init_app(app)

    with app.app_context():
        db.create_all()
        if MaintenanceWindow.query.count() == 0:
            seed_maintenance_data()

    from .routes import maintenance_bp
    app.register_blueprint(maintenance_bp)

    return app


def seed_maintenance_data():
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    rows = [
        MaintenanceWindow(component_name='Pump_1', window_start=now + timedelta(days=1), window_end=now + timedelta(days=1, hours=2), status='Scheduled', notes='Seal check'),
        MaintenanceWindow(component_name='Valve_A', window_start=now + timedelta(days=2), window_end=now + timedelta(days=2, hours=1), status='Scheduled', notes='Actuator calibration'),
        MaintenanceWindow(component_name='Compressor_3', window_start=now + timedelta(days=4), window_end=now + timedelta(days=4, hours=3), status='Planned', notes='Vibration inspection'),
    ]

    db.session.add_all(rows)
    db.session.commit()

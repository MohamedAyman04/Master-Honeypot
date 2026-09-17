from flask import Flask
from pathlib import Path
from prometheus_flask_exporter import PrometheusMetrics
from .models import db, SensorReading, User


def create_app():
    app = Flask(__name__, template_folder='../templates')
    PrometheusMetrics(app, path='/metrics')

    repo_root = Path(__file__).resolve().parents[4]
    db_path = repo_root / 'database-files' / 'historians' / 'sensor_readings_historian.db'
    db_path.parent.mkdir(parents=True, exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'historian-3-secret-key'

    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_default_users()
        if SensorReading.query.count() == 0:
            seed_sensor_data()

    from .routes import sensor_bp
    app.register_blueprint(sensor_bp)

    return app


def seed_sensor_data():
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    rows = [
        SensorReading(sensor_name='Temperature_Reactor_A', value=146.2, unit='C', status='Normal', timestamp=now),
        SensorReading(sensor_name='Pressure_Tank_B', value=23.4, unit='Bar', status='Normal', timestamp=now - timedelta(minutes=1)),
        SensorReading(sensor_name='Flow_Rate_Main', value=127.1, unit='L/min', status='Normal', timestamp=now - timedelta(minutes=2)),
    ]

    db.session.add_all(rows)
    db.session.commit()


def ensure_default_users():
    defaults = [
        ('admin', 'admin', 'admin'),
        ('operator', 'operator123', 'operator'),
        ('engineer', 'engineer456', 'engineer'),
    ]

    for username, password, role in defaults:
        existing = User.query.filter_by(username=username).first()
        if not existing:
            db.session.add(User(username=username, password=password, role=role))

    db.session.commit()

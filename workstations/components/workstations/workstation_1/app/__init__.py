from flask import Flask
from prometheus_flask_exporter import PrometheusMetrics
from .models import db
import os
import uuid
from pathlib import Path
from flask import request
from .unified_logger import UnifiedLogger
from components.common.story_client import StoryClient


def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.config['SECRET_KEY'] = 'dev-secret-key'
    PrometheusMetrics(app, path='/metrics')
    
    # Initialize the UnifiedLogger to write to the shared L3 volume
    # /app/logs is mounted to honeypot_logs_data in L3 docker-compose
    unified_logger = UnifiedLogger(service="workstation_api", layer="Level 3", log_dir="/app/logs")
    story_client = StoryClient(component="workstation_api", level="Level 3")
    
    @app.before_request
    def log_l3_access():
        if not request.path.startswith('/static') and not request.path.startswith('/metrics'):
            session_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
            
            # Detect simulated SQLi
            event_type = "API_ACCESS"
            if request.args and any("UNION" in str(v).upper() or "SELECT" in str(v).upper() for v in request.args.values()):
                event_type = "SQL_INJECTION"
                
            unified_logger.log(
                event_type=event_type,
                correlation_id=session_id,
                source={
                    "ip": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent", "")
                },
                target={
                    "host": "ws-eng-01",
                    "endpoint": request.path,
                    "service": "workstation_api"
                },
                payload={
                    "method": request.method,
                    "raw_url": request.url
                }
            )

            story_client.log(
                event_type=event_type.lower(),
                message=f"{event_type} {request.method} {request.path}",
                severity="high" if event_type == "SQL_INJECTION" else "info",
                details={
                    "ip": request.remote_addr,
                    "method": request.method,
                    "path": request.path,
                    "user_agent": request.headers.get("User-Agent", ""),
                },
            )

    component_name = (os.getenv('WORKSTATION_COMPONENT', 'workstation_1') or 'workstation_1').strip()
    raw_db_name = (os.getenv('WORKSTATION_DB_NAME', f'{component_name}.db') or f'{component_name}.db').strip()
    db_file_name = Path(raw_db_name).name
    if not db_file_name.endswith('.db'):
        db_file_name = f'{db_file_name}.db'

    app.config['WORKSTATION_COMPONENT'] = component_name
    app.config['WORKSTATION_DEVICE_PROFILE'] = {
        'ip': os.getenv('WORKSTATION_DEVICE_IP', ''),
        'mac': os.getenv('WORKSTATION_DEVICE_MAC', ''),
        'serial': os.getenv('WORKSTATION_SERIAL', ''),
        'model': os.getenv('WORKSTATION_MODEL', ''),
        'vendor': os.getenv('WORKSTATION_VENDOR', ''),
    }

    repo_root = Path(__file__).resolve().parents[4]
    db_path = repo_root / 'database-files' / 'workstations' / db_file_name
    db_path.parent.mkdir(parents=True, exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        # Create default users if missing (intentional weak credentials for honeypot research)
        from .models import User, SensorReading, SystemSecret
        default_users = [
            ('admin', 'admin', 'admin'),
            ('operator', 'operator123', 'operator'),
            ('engineer', 'engineer456', 'engineer'),
        ]

        for username, password, role in default_users:
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                db.session.add(User(username=username, password=password, role=role))

        if SensorReading.query.count() == 0:
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            default_sensors = [
                SensorReading(tag_id='TT-101', sensor_name='CDU-01 Furnace Temp', value=342.6, unit='°C', status='NORMAL', location='Furnace CDU-01', timestamp=now),
                SensorReading(tag_id='PT-102', sensor_name='Crude Feed Pressure', value=18.4, unit='Bar', status='NORMAL', location='Inlet Manifold', timestamp=now - timedelta(minutes=1)),
                SensorReading(tag_id='LT-103', sensor_name='Distillation Column Level', value=68.2, unit='%', status='NORMAL', location='Distillation Column', timestamp=now - timedelta(minutes=2)),
                SensorReading(tag_id='FT-104', sensor_name='Reflux Flow Rate', value=142.8, unit='m³/h', status='NORMAL', location='Reflux Overhead', timestamp=now - timedelta(minutes=3)),
                SensorReading(tag_id='PT-105', sensor_name='Overhead Condenser Pressure', value=4.2, unit='Bar', status='NORMAL', location='Condenser Header', timestamp=now - timedelta(minutes=4)),
                SensorReading(tag_id='FT-106', sensor_name='Reboiler Steam Flow', value=89.1, unit='kg/h', status='NORMAL', location='Reboiler Loop', timestamp=now - timedelta(minutes=5)),
                SensorReading(tag_id='XV-107', sensor_name='Safety Relief Valve Position', value=0.0, unit='%', status='CLOSED', location='ESD Block Valve', timestamp=now - timedelta(minutes=6)),
                SensorReading(tag_id='SI-901', sensor_name='ESD Emergency Shutdown Interlock', value=1.0, unit='ARMED', status='NORMAL', location='Safety SIS Rack', timestamp=now - timedelta(minutes=7)),
                SensorReading(tag_id='VT-201', sensor_name='Pump 101-A Bearing Vibration', value=1.8, unit='mm/s', status='NORMAL', location='Pump House A', timestamp=now - timedelta(minutes=8)),
                SensorReading(tag_id='TT-202', sensor_name='Naphtha Draw Temp', value=124.5, unit='°C', status='NORMAL', location='Draw Tray 14', timestamp=now - timedelta(minutes=9)),
                SensorReading(tag_id='TT-203', sensor_name='Kerosene Draw Temp', value=188.2, unit='°C', status='NORMAL', location='Draw Tray 28', timestamp=now - timedelta(minutes=10)),
                SensorReading(tag_id='TT-204', sensor_name='Diesel Draw Temp', value=262.7, unit='°C', status='NORMAL', location='Draw Tray 42', timestamp=now - timedelta(minutes=11)),
                SensorReading(tag_id='LT-205', sensor_name='Heavy Fuel Oil Level', value=81.3, unit='%', status='NORMAL', location='Bottoms Tankage', timestamp=now - timedelta(minutes=12)),
            ]
            db.session.add_all(default_sensors)

        if SystemSecret.query.count() == 0:
            default_secrets = [
                SystemSecret(service='OPCUA_SERVER_ROOT', credential='opc.tcp://192.168.99.10:4840/freeopcua/server/', canary_token='CANARY-OPCUA-ADM-9942', notes='Primary Level 1/2 Process Server'),
                SystemSecret(service='SAFETY_PLC_S7_KEY', credential='S7_Safety_Override#2026!', canary_token='CANARY-S7-PLC-KEY-8812', notes='Emergency Shutdown Logic CPU 414'),
                SystemSecret(service='MODBUS_RTU_GATEWAY', credential='admin:ModbusCracking2026$$', canary_token='CANARY-MODBUS-GW-7731', notes='Serial Gateway 192.168.99.12'),
                SystemSecret(service='HISTORIAN_INGESTION_TOKEN', credential='Bearer ht_tok_scada_historian_master_key_2026', canary_token='CANARY-HISTORIAN-AUTH-4419', notes='L2/L3 Bridge Ingestion Key'),
            ]
            db.session.add_all(default_secrets)

        db.session.commit()
        print("[*] Default users & historian telemetry ensured")
        print(f"[*] Workstation profile loaded: component={component_name}, db={db_file_name}")
    
    from .routes import auth_bp
    app.register_blueprint(auth_bp)
    
    return app


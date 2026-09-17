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
        from .models import User
        default_users = [
            ('admin', 'admin', 'admin'),
            ('operator', 'operator123', 'operator'),
            ('engineer', 'engineer456', 'engineer'),
        ]

        for username, password, role in default_users:
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                db.session.add(User(username=username, password=password, role=role))

        db.session.commit()
        print("[*] Default users ensured: admin/admin, operator/operator123, engineer/engineer456")
        print(f"[*] Workstation profile loaded: component={component_name}, db={db_file_name}")
    
    from .routes import auth_bp
    app.register_blueprint(auth_bp)
    
    return app


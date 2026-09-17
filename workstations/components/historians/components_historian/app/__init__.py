from flask import Flask
from pathlib import Path
from .models import db, FactoryComponent


def create_app():
    app = Flask(__name__, template_folder='../templates')

    repo_root = Path(__file__).resolve().parents[4]
    db_path = repo_root / 'database-files' / 'historians' / 'components_historian.db'
    db_path.parent.mkdir(parents=True, exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'historian-4-secret-key'

    db.init_app(app)

    with app.app_context():
        db.create_all()
        if FactoryComponent.query.count() == 0:
            seed_component_data()

    from .routes import components_bp
    app.register_blueprint(components_bp)

    return app


def seed_component_data():
    rows = [
        FactoryComponent(component_name='Plant_Network_Switch_A', component_type='Network', level=2, status='Active', location='Control Room'),
        FactoryComponent(component_name='Engineering_Workstation_1', component_type='Workstation', level=3, status='Active', location='Operations Office'),
        FactoryComponent(component_name='Historian_Server_1', component_type='Historian', level=3, status='Active', location='Data Center'),
        FactoryComponent(component_name='Gateway_Node_1', component_type='Gateway', level=2, status='Active', location='Cell/Area Boundary'),
    ]

    # Keep only components up to level 2 (level 3 not included)
    filtered_rows = [row for row in rows if row.level < 3]
    db.session.add_all(filtered_rows)
    db.session.commit()

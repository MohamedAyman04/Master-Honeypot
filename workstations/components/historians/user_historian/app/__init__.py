from flask import Flask
from .models import db
from pathlib import Path

def create_app():
    """Create and configure the Flask app"""
    app = Flask(__name__, template_folder='../templates')

    repo_root = Path(__file__).resolve().parents[4]
    db_path = repo_root / 'database-files' / 'historians' / 'user_historian.db'
    db_path.parent.mkdir(parents=True, exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'historian-secret-key-change-in-production'
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        from .models import User

        # Ensure default users exist in user historian
        ensure_default_users(User)
    
    # Register blueprint
    from .routes import historian_bp
    app.register_blueprint(historian_bp)
    
    return app


def ensure_default_users(User):
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
    print("[*] Historian 1 user records ensured")

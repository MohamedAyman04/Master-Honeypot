from flask import Blueprint, redirect, url_for, render_template, jsonify
from .models import User


historian_bp = Blueprint('historian', __name__)


@historian_bp.route('/')
def index():
    return redirect(url_for('historian.dashboard'))


@historian_bp.route('/dashboard')
def dashboard():
    return render_template(
        'historian_dashboard.html',
        users_count=User.query.count()
    )


@historian_bp.route('/api/users')
def api_users():
    users = User.query.order_by(User.id.asc()).all()
    return jsonify([user.to_dict() for user in users])

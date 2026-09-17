from flask import Blueprint, jsonify, redirect, render_template, url_for
from .models import MaintenanceWindow


maintenance_bp = Blueprint('maintenance', __name__)


@maintenance_bp.route('/')
def index():
    return redirect(url_for('maintenance.dashboard'))


@maintenance_bp.route('/dashboard')
def dashboard():
    count = MaintenanceWindow.query.count()
    return render_template('historian_dashboard.html', records_count=count)


@maintenance_bp.route('/api/maintenance')
def api_maintenance():
    rows = MaintenanceWindow.query.order_by(MaintenanceWindow.window_start.asc()).all()
    return jsonify([row.to_dict() for row in rows])

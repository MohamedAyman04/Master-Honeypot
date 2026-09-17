from flask import Blueprint, jsonify, redirect, render_template, url_for
from .models import FactoryComponent


components_bp = Blueprint('components_hist', __name__)


@components_bp.route('/')
def index():
    return redirect(url_for('components_hist.dashboard'))


@components_bp.route('/dashboard')
def dashboard():
    count = FactoryComponent.query.count()
    return render_template('historian_dashboard.html', records_count=count)


@components_bp.route('/api/components')
def api_components():
    rows = FactoryComponent.query.order_by(FactoryComponent.level.asc(), FactoryComponent.component_name.asc()).all()
    return jsonify([row.to_dict() for row in rows])

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_file
from flask_paginate import Pagination, get_page_args
from datetime import datetime
import io
import matplotlib.pyplot as plt

from services import DataService, NotificationService, AnalyticsService
from database import get_db_session
from cache import CacheManager
from utils import (
    handle_exceptions, validate_phone_number, validate_sensor_data,
    sanitize_input, monitor_performance, log_request_info, log_response_info,
    validate_pagination_params, ValidationError, DataProcessingError
)

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)
admin_bp = Blueprint('admin', __name__)

# Main routes
@main_bp.route('/')
@handle_exceptions
@monitor_performance('dashboard')
def index():
    """Main dashboard page"""
    with get_db_session() as session:
        data_service = DataService(session)
        
        # Get water posts for map
        water_posts = data_service.get_water_posts_with_coordinates()
        
        # Get river data
        river_data = data_service.get_river_data()
        
        # Get latest sensor data for display
        sensor_a_data = data_service.get_latest_sensor_data('sensor_a')
        sensor_b_data = data_service.get_latest_sensor_data('sensor_b')
        
        return render_template('index.html',
                             water_posts=water_posts,
                             river_data=river_data,
                             sensor_a_data=sensor_a_data,
                             sensor_b_data=sensor_b_data)

@main_bp.route('/water-data')
@handle_exceptions
@monitor_performance('water_data_page')
def water_data():
    """Water data page with pagination"""
    page, per_page, offset = get_page_args(
        page_parameter='page',
        per_page_parameter='per_page'
    )
    
    page, per_page = validate_pagination_params(page, per_page)
    
    with get_db_session() as session:
        data_service = DataService(session)
        
        # Get paginated water data
        water_data, total = data_service.get_paginated_data(
            model_class='WaterData',
            page=page,
            per_page=per_page
        )
        
        # Get latest data for display
        latest_water_data = data_service.get_latest_water_data()
        latest_forecasting = data_service.get_latest_forecasting()
        
        pagination = Pagination(
            page=page,
            per_page=per_page,
            total=total,
            css_framework='bootstrap4'
        )
        
        current_time = datetime.now()
        
        return render_template('water_data.html',
                             water_data=water_data,
                             pagination=pagination,
                             latest_water_data=latest_water_data,
                             latest_forecasting=latest_forecasting,
                             date=current_time.strftime('%A, %Y-%m-%d'),
                             time=current_time.strftime('%H:%M'))

@main_bp.route('/sensor-a-data')
@handle_exceptions
@monitor_performance('sensor_a_data_page')
def sensor_a_data():
    """Sensor A data page"""
    page, per_page, offset = get_page_args(
        page_parameter='page',
        per_page_parameter='per_page'
    )
    
    page, per_page = validate_pagination_params(page, per_page)
    
    with get_db_session() as session:
        data_service = DataService(session)
        
        sensor_data, total = data_service.get_paginated_data(
            model_class='SensorA',
            page=page,
            per_page=per_page
        )
        
        latest_sensor_data = data_service.get_latest_sensor_data('sensor_a')
        latest_forecasting = data_service.get_latest_forecasting()
        
        pagination = Pagination(
            page=page,
            per_page=per_page,
            total=total,
            css_framework='bootstrap4'
        )
        
        current_time = datetime.now()
        
        return render_template('sensor_a_data.html',
                             sensor_data=sensor_data,
                             pagination=pagination,
                             latest_sensor_data=latest_sensor_data,
                             latest_forecasting=latest_forecasting,
                             date=current_time.strftime('%A, %Y-%m-%d'),
                             time=current_time.strftime('%H:%M'))

@main_bp.route('/sensor-b-data')
@handle_exceptions
@monitor_performance('sensor_b_data_page')
def sensor_b_data():
    """Sensor B data page"""
    page, per_page, offset = get_page_args(
        page_parameter='page',
        per_page_parameter='per_page'
    )
    
    page, per_page = validate_pagination_params(page, per_page)
    
    with get_db_session() as session:
        data_service = DataService(session)
        
        sensor_data, total = data_service.get_paginated_data(
            model_class='SensorB',
            page=page,
            per_page=per_page
        )
        
        latest_sensor_data = data_service.get_latest_sensor_data('sensor_b')
        latest_forecasting = data_service.get_latest_forecasting()
        
        pagination = Pagination(
            page=page,
            per_page=per_page,
            total=total,
            css_framework='bootstrap4'
        )
        
        current_time = datetime.now()
        
        return render_template('sensor_b_data.html',
                             sensor_data=sensor_data,
                             pagination=pagination,
                             latest_sensor_data=latest_sensor_data,
                             latest_forecasting=latest_forecasting,
                             date=current_time.strftime('%A, %Y-%m-%d'),
                             time=current_time.strftime('%H:%M'))

@main_bp.route('/analytics')
@handle_exceptions
@monitor_performance('analytics_page')
def analytics():
    """Analytics page"""
    with get_db_session() as session:
        analytics_service = AnalyticsService(session)
        
        water_trend = analytics_service.get_water_level_trend(days=7)
        sensor_a_stats = analytics_service.get_sensor_statistics('sensor_a', hours=24)
        sensor_b_stats = analytics_service.get_sensor_statistics('sensor_b', hours=24)
        
        # Get risk assessment for all posts
        risk_assessments = []
        data_service = DataService(session)
        water_posts = data_service.get_water_posts_with_coordinates()
        
        for post in water_posts:
            risk = analytics_service.get_flood_risk_assessment(post['post_code'])
            risk['post_name'] = post['post_name']
            risk_assessments.append(risk)
        
        return render_template('analytics.html',
                             water_trend=water_trend,
                             sensor_a_stats=sensor_a_stats,
                             sensor_b_stats=sensor_b_stats,
                             risk_assessments=risk_assessments)

# API routes
@api_bp.route('/real-time')
@handle_exceptions
@monitor_performance('real_time_data')
def real_time_data():
    """Real-time data API endpoint"""
    with get_db_session() as session:
        data_service = DataService(session)
        
        sensor_a_data = data_service.get_latest_sensor_data('sensor_a')
        sensor_b_data = data_service.get_latest_sensor_data('sensor_b')
        water_data = data_service.get_latest_water_data()
        forecasting_data = data_service.get_latest_forecasting()
        
        current_time = datetime.now()
        
        response_data = {
            'timestamp': current_time.isoformat(),
            'time': current_time.strftime('%H:%M'),
            'date': current_time.strftime('%A, %Y-%m-%d'),
            'sensor_a': sensor_a_data or {},
            'sensor_b': sensor_b_data or {},
            'water_data': water_data or {},
            'forecasting': forecasting_data or {}
        }
        
        log_response_info(response_data)
        return jsonify(response_data)

@api_bp.route('/water-data')
@handle_exceptions
@monitor_performance('water_data_api')
def api_water_data():
    """Water data API endpoint"""
    with get_db_session() as session:
        data_service = DataService(session)
        
        water_data, _ = data_service.get_paginated_data(
            model_class='WaterData',
            page=1,
            per_page=100
        )
        
        forecasting_data, _ = data_service.get_paginated_data(
            model_class='Forecasting',
            page=1,
            per_page=100
        )
        
        river_data = data_service.get_river_data()
        
        # Process data for chart
        labels = [item.created_at.isoformat() for item in water_data]
        values = [item.water_elevation for item in water_data]
        
        labels_prediction = [item.created_at.isoformat() for item in forecasting_data]
        values_prediction = [item.prediction_water_elevation for item in forecasting_data]
        
        # Create limiters data
        limiters = []
        for river in river_data:
            limiters.extend([
                {
                    'name': f'Safe ({river["river_safe_height"]})',
                    'value': river['river_safe_height'],
                    'color': 'rgba(0, 128, 0, 0.6)'
                },
                {
                    'name': f'Warning ({river["river_warning_height"]})',
                    'value': river['river_warning_height'],
                    'color': 'rgba(255, 165, 0, 0.6)'
                },
                {
                    'name': f'Danger ({river["river_danger_height"]})',
                    'value': river['river_danger_height'],
                    'color': 'rgba(255, 0, 0, 0.6)'
                }
            ])
        
        return jsonify({
            'labels': labels,
            'values': values,
            'labels_prediction': labels_prediction,
            'values_prediction': values_prediction,
            'limiters': limiters
        })

@api_bp.route('/analytics/water-trend')
@handle_exceptions
@monitor_performance('water_trend_api')
def api_water_trend():
    """Water trend analytics API"""
    days = request.args.get('days', 7, type=int)
    post_code = request.args.get('post_code', None)
    
    with get_db_session() as session:
        analytics_service = AnalyticsService(session)
        trend_data = analytics_service.get_water_level_trend(days=days, post_code=post_code)
        
        return jsonify(trend_data)

@api_bp.route('/analytics/sensor-stats')
@handle_exceptions
@monitor_performance('sensor_stats_api')
def api_sensor_stats():
    """Sensor statistics API"""
    sensor_type = request.args.get('sensor_type', 'sensor_a')
    hours = request.args.get('hours', 24, type=int)
    
    with get_db_session() as session:
        analytics_service = AnalyticsService(session)
        stats = analytics_service.get_sensor_statistics(sensor_type, hours=hours)
        
        return jsonify(stats)

@api_bp.route('/analytics/risk-assessment')
@handle_exceptions
@monitor_performance('risk_assessment_api')
def api_risk_assessment():
    """Risk assessment API"""
    post_code = request.args.get('post_code', None)
    
    if not post_code:
        raise ValidationError("Post code is required")
    
    with get_db_session() as session:
        analytics_service = AnalyticsService(session)
        risk = analytics_service.get_flood_risk_assessment(post_code)
        
        return jsonify(risk)

# Admin routes
@admin_bp.route('/edit-data')
@handle_exceptions
@monitor_performance('edit_data_page')
def edit_data():
    """Edit data page"""
    with get_db_session() as session:
        from models import WaterPostData, RiverData
        
        water_posts = session.query(WaterPostData).all()
        river_data = session.query(RiverData).all()
        
        return render_template('edit_data.html',
                             water_posts=water_posts,
                             river_data=river_data)

@admin_bp.route('/update_water_post/<int:id>', methods=['POST'])
@handle_exceptions
@monitor_performance('update_water_post')
def update_water_post(id):
    """Update water post data"""
    with get_db_session() as session:
        from models import WaterPostData
        
        water_post = session.query(WaterPostData).get_or_404(id)
        data = request.form
        
        # Sanitize and validate data
        water_post.post_code = sanitize_input(data.get('post_code'))
        water_post.post_name = sanitize_input(data.get('post_name'))
        water_post.post_longitude = sanitize_input(data.get('post_longitude'))
        water_post.post_latitude = sanitize_input(data.get('post_latitude'))
        water_post.post_river_code = sanitize_input(data.get('post_river_code'))
        
        try:
            water_post.post_sensor_placement = float(data.get('post_sensor_placement', 0))
        except (ValueError, TypeError):
            raise ValidationError("Sensor placement must be a valid number")
        
        water_post.post_inactive = sanitize_input(data.get('post_inactive', 'active'))
        
        session.commit()
        
        # Invalidate related cache
        CacheManager.invalidate_water_cache(water_post.post_code)
        
        return redirect(url_for('admin.edit_data'))

@admin_bp.route('/update_river_data/<int:id>', methods=['POST'])
@handle_exceptions
@monitor_performance('update_river_data')
def update_river_data(id):
    """Update river data"""
    with get_db_session() as session:
        from models import RiverData
        
        river = session.query(RiverData).get_or_404(id)
        data = request.form
        
        # Sanitize and validate data
        river.river_code = sanitize_input(data.get('river_code'))
        river.river_name = sanitize_input(data.get('river_name'))
        
        # Validate numeric fields
        numeric_fields = [
            'river_point_distance', 'river_flow_velocity', 'river_roughness',
            'river_width', 'river_depth', 'river_slope', 'river_safe_height',
            'river_warning_height', 'river_danger_height'
        ]
        
        for field in numeric_fields:
            try:
                value = float(data.get(field, 0))
                setattr(river, field, value)
            except (ValueError, TypeError):
                raise ValidationError(f"{field} must be a valid number")
        
        session.commit()
        
        # Invalidate related cache
        CacheManager.invalidate_water_cache()
        CacheManager.invalidate_forecasting_cache()
        
        return redirect(url_for('admin.edit_data'))

# Subscription routes
@main_bp.route('/subscribe', methods=['POST'])
@handle_exceptions
@monitor_performance('subscribe_sms')
def subscribe():
    """Subscribe to SMS notifications"""
    log_request_info()
    
    phone_number = request.form.get('phone_number', '').strip()
    
    if not validate_phone_number(phone_number):
        raise ValidationError("Invalid phone number format")
    
    phone_number = sanitize_input(phone_number)
    
    with get_db_session() as session:
        notification_service = NotificationService(session)
        
        success = notification_service.add_sms_subscriber(phone_number)
        
        if success:
            return redirect(url_for('main.index'))
        else:
            raise DataProcessingError("Failed to add subscriber")

@main_bp.route('/whatsapp-subscribe', methods=['POST'])
@handle_exceptions
@monitor_performance('subscribe_whatsapp')
def whatsapp_subscribe():
    """Subscribe to WhatsApp notifications"""
    log_request_info()
    
    phone_number = request.form.get('phone_number', '').strip()
    whatsapp_api = request.form.get('whatsapp_api', '').strip()
    
    if not validate_phone_number(phone_number):
        raise ValidationError("Invalid phone number format")
    
    if not whatsapp_api:
        raise ValidationError("WhatsApp API is required")
    
    phone_number = sanitize_input(phone_number)
    whatsapp_api = sanitize_input(whatsapp_api)
    
    with get_db_session() as session:
        notification_service = NotificationService(session)
        
        success = notification_service.add_whatsapp_subscriber(phone_number, whatsapp_api)
        
        if success:
            return redirect(url_for('main.index'))
        else:
            raise DataProcessingError("Failed to add WhatsApp subscriber")

# Plot routes
@main_bp.route('/water-elevation-plot.png')
@handle_exceptions
@monitor_performance('water_elevation_plot')
def plot_png():
    """Generate water elevation plot"""
    with get_db_session() as session:
        data_service = DataService(session)
        
        water_data, _ = data_service.get_paginated_data(
            model_class='WaterData',
            page=1,
            per_page=100
        )
        
        forecasting_data, _ = data_service.get_paginated_data(
            model_class='Forecasting',
            page=1,
            per_page=100
        )
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if water_data:
            actual_dates = [item.created_at for item in water_data]
            actual_values = [item.water_elevation for item in water_data]
            ax.plot(actual_dates, actual_values, label='Actual Water Level', linewidth=2)
        
        if forecasting_data:
            pred_dates = [item.created_at for item in forecasting_data]
            pred_values = [item.prediction_water_elevation for item in forecasting_data]
            ax.plot(pred_dates, pred_values, label='Predicted Water Level', 
                   linestyle='--', linewidth=2)
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Water Elevation (m)')
        ax.set_title('Water Level Monitoring and Prediction')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return send_file(buf, mimetype='image/png') 
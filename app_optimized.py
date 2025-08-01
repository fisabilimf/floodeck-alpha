import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_paginate import Pagination, get_page_args
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Import our optimized modules
from config import config
from models import Base
from services import DataService, NotificationService, AnalyticsService
from database import init_database, get_db_session, get_health_check
from cache import cache, CacheManager
from utils import (
    handle_exceptions, validate_phone_number, validate_sensor_data,
    sanitize_input, monitor_performance, log_request_info, log_response_info,
    ValidationError, DataProcessingError
)

def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app

def init_extensions(app):
    """Initialize Flask extensions"""
    # Initialize cache
    cache.init_app(app)
    
    # Initialize database
    init_database(app.config)
    
    # Enable CORS
    CORS(app)

def register_blueprints(app):
    """Register Flask blueprints"""
    from routes import main_bp, api_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')

def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Not Found', 'message': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred'}), 500
    
    @app.errorhandler(ValidationError)
    def validation_error(error):
        return jsonify({'error': 'Validation Error', 'message': str(error)}), 400
    
    @app.errorhandler(DataProcessingError)
    def data_processing_error(error):
        return jsonify({'error': 'Data Processing Error', 'message': str(error)}), 500

# Create the application instance
app = create_app()

# Global service instances
data_service = None
notification_service = None
analytics_service = None

@app.before_first_request
def initialize_services():
    """Initialize service instances"""
    global data_service, notification_service, analytics_service
    
    with get_db_session() as session:
        data_service = DataService(session)
        notification_service = NotificationService(session)
        analytics_service = AnalyticsService(session)

@app.route('/health')
@handle_exceptions
@monitor_performance('health_check')
def health_check():
    """Health check endpoint"""
    db_health = get_health_check()
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'database': db_health,
            'cache': CacheManager.get_cache_info()
        }
    }
    
    # Check if any service is unhealthy
    if db_health.get('status') != 'healthy':
        health_status['status'] = 'unhealthy'
    
    return jsonify(health_status)

@app.route('/')
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
        
        # Convert to JSON for template
        water_posts_json = json.dumps(water_posts)
        
        return render_template('index.html',
                             water_posts=water_posts_json,
                             river_data=river_data,
                             sensor_a_data=sensor_a_data,
                             sensor_b_data=sensor_b_data)

@app.route('/api/real-time')
@handle_exceptions
@monitor_performance('real_time_data')
def real_time_data():
    """Real-time data API endpoint"""
    with get_db_session() as session:
        data_service = DataService(session)
        
        # Get latest data from all sources
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

@app.route('/subscribe', methods=['POST'])
@handle_exceptions
@monitor_performance('subscribe_sms')
def subscribe():
    """Subscribe to SMS notifications"""
    log_request_info()
    
    phone_number = request.form.get('phone_number', '').strip()
    
    # Validate phone number
    if not validate_phone_number(phone_number):
        raise ValidationError("Invalid phone number format")
    
    # Sanitize input
    phone_number = sanitize_input(phone_number)
    
    with get_db_session() as session:
        notification_service = NotificationService(session)
        
        success = notification_service.add_sms_subscriber(phone_number)
        
        if success:
            return redirect(url_for('index'))
        else:
            raise DataProcessingError("Failed to add subscriber")

@app.route('/whatsapp-subscribe', methods=['POST'])
@handle_exceptions
@monitor_performance('subscribe_whatsapp')
def whatsapp_subscribe():
    """Subscribe to WhatsApp notifications"""
    log_request_info()
    
    phone_number = request.form.get('phone_number', '').strip()
    whatsapp_api = request.form.get('whatsapp_api', '').strip()
    
    # Validate inputs
    if not validate_phone_number(phone_number):
        raise ValidationError("Invalid phone number format")
    
    if not whatsapp_api:
        raise ValidationError("WhatsApp API is required")
    
    # Sanitize inputs
    phone_number = sanitize_input(phone_number)
    whatsapp_api = sanitize_input(whatsapp_api)
    
    with get_db_session() as session:
        notification_service = NotificationService(session)
        
        success = notification_service.add_whatsapp_subscriber(phone_number, whatsapp_api)
        
        if success:
            return redirect(url_for('index'))
        else:
            raise DataProcessingError("Failed to add WhatsApp subscriber")

@app.route('/water-data')
@handle_exceptions
@monitor_performance('water_data_page')
def water_data():
    """Water data page with pagination"""
    page, per_page, offset = get_page_args(
        page_parameter='page',
        per_page_parameter='per_page'
    )
    
    # Validate pagination parameters
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
        
        # Create pagination object
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

@app.route('/api/water-data')
@handle_exceptions
@monitor_performance('water_data_api')
def api_water_data():
    """Water data API endpoint"""
    with get_db_session() as session:
        data_service = DataService(session)
        
        # Get water data for chart
        water_data, _ = data_service.get_paginated_data(
            model_class='WaterData',
            page=1,
            per_page=100
        )
        
        # Get forecasting data
        forecasting_data, _ = data_service.get_paginated_data(
            model_class='Forecasting',
            page=1,
            per_page=100
        )
        
        # Get river data for limiters
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

@app.route('/water-elevation-plot.png')
@handle_exceptions
@monitor_performance('water_elevation_plot')
def plot_png():
    """Generate water elevation plot"""
    with get_db_session() as session:
        data_service = DataService(session)
        
        # Get data for plotting
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
        
        # Plot actual data
        if water_data:
            actual_dates = [item.created_at for item in water_data]
            actual_values = [item.water_elevation for item in water_data]
            ax.plot(actual_dates, actual_values, label='Actual Water Level', linewidth=2)
        
        # Plot prediction data
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
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return send_file(buf, mimetype='image/png')

@app.route('/sensor-a-data')
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
        
        # Get paginated sensor A data
        sensor_data, total = data_service.get_paginated_data(
            model_class='SensorA',
            page=page,
            per_page=per_page
        )
        
        # Get latest data
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

@app.route('/sensor-b-data')
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
        
        # Get paginated sensor B data
        sensor_data, total = data_service.get_paginated_data(
            model_class='SensorB',
            page=page,
            per_page=per_page
        )
        
        # Get latest data
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

@app.route('/analytics')
@handle_exceptions
@monitor_performance('analytics_page')
def analytics():
    """Analytics page"""
    with get_db_session() as session:
        analytics_service = AnalyticsService(session)
        
        # Get analytics data
        water_trend = analytics_service.get_water_level_trend(days=7)
        sensor_a_stats = analytics_service.get_sensor_statistics('sensor_a', hours=24)
        sensor_b_stats = analytics_service.get_sensor_statistics('sensor_b', hours=24)
        
        # Get risk assessment for all posts
        risk_assessments = []
        with get_db_session() as session:
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

@app.route('/api/analytics/water-trend')
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

@app.route('/api/analytics/sensor-stats')
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

@app.route('/api/analytics/risk-assessment')
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 
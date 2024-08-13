#import section
import json
import matplotlib.pyplot as plt
import pandas as pd
import pymysql
import io
import base64
import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_mysqldb import MySQL
from datetime import datetime
from flask_paginate import Pagination, get_page_args
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'floodeck_alpha'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/floodeck_alpha'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

mysql = MySQL(app)

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='floodeck_alpha'
        )
        if conn.is_connected():
            print("Connected to MySQL database")
        return conn
    except Error as e:
        print(f"Error: {e}")
        return None

def convert_datetime(item):
    if isinstance(item, datetime):
        return item.isoformat()
    return item

def get_data(table, offset=0, per_page=10):
    cursor = mysql.connection.cursor()
    cursor.execute(f'''SELECT * FROM {table} ORDER BY id DESC LIMIT %s OFFSET %s''', (per_page, offset))
    data = cursor.fetchall()
    cursor.execute(f'''SELECT COUNT(*) FROM {table}''')
    total = cursor.fetchone()[0]
    return data, total

def db_connection():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM subscribers') 
    data = cursor.fetchall()
    cursor.close()
    return data

def get_data(table, offset=0, per_page=10):
    cursor = mysql.connection.cursor()
    cursor.execute(f'''SELECT * FROM {table} ORDER BY id DESC LIMIT %s OFFSET %s''', (per_page, offset))
    data = cursor.fetchall()
    cursor.execute(f'''SELECT COUNT(*) FROM {table}''')
    total = cursor.fetchone()[0]
    return data, total

def get_temperature():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT sensor_a_temperature FROM sensor_a ORDER BY created_at DESC LIMIT 1')
    temperature = cursor.fetchone()

    return temperature[0] if temperature else 'N/A'

def get_humidity():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT sensor_a_humidity FROM sensor_a ORDER BY created_at DESC LIMIT 1')
    humidity = cursor.fetchone()

    return humidity[0] if humidity else 'N/A'

def get_raindrop():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT sensor_a_raindrop FROM sensor_a ORDER BY created_at DESC LIMIT 1')
    raindrop = cursor.fetchone()

    return raindrop[0] if raindrop else 'N/A'

def get_status():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT water_status FROM water_data ORDER BY created_at DESC LIMIT 1')
    status = cursor.fetchone()
    return status[0] if status else 'N/A'

def get_predicted_status():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT water_status FROM forecasting ORDER BY created_at DESC LIMIT 1')
    status = cursor.fetchone()
    return status[0] if status else 'N/A'

def get_latest_water_level():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT water_elevation FROM water_data ORDER BY created_at DESC LIMIT 1')
    water_level = cursor.fetchone()
    return water_level[0] if water_level else 'N/A'

def get_latest_predicted_water_level():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT prediction_water_elevation FROM forecasting ORDER BY created_at DESC LIMIT 1')
    water_level = cursor.fetchone()
    return water_level[0] if water_level else 'N/A'

def get_sensor_a_status():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT sensor_a_status FROM sensor_a ORDER BY created_at DESC LIMIT 1')
    status = cursor.fetchone()
    return status[0] if status else 'N/A'

def get_predicted_sensor_a_status():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT water_sensor_a_status FROM forecasting ORDER BY created_at DESC LIMIT 1')
    status = cursor.fetchone()
    return status[0] if status else 'N/A'

def get_latest_water_level_sensor_a():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT sensor_a_scan_water_height FROM sensor_a ORDER BY created_at DESC LIMIT 1')
    water_level = cursor.fetchone()
    return water_level[0] if water_level else 'N/A'

def get_latest_predicted_water_level_sensor_a():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT prediction_sensor_a_scan_water_height FROM forecasting ORDER BY created_at DESC LIMIT 1')
    water_level = cursor.fetchone()
    return water_level[0] if water_level else 'N/A'

def get_sensor_b_status():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT sensor_b_status FROM sensor_b ORDER BY created_at DESC LIMIT 1')
    status = cursor.fetchone()
    return status[0] if status else 'N/A'

def get_predicted_sensor_b_status():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT water_sensor_b_status FROM forecasting ORDER BY created_at DESC LIMIT 1')
    status = cursor.fetchone()
    return status[0] if status else 'N/A'

def get_latest_water_level_sensor_b():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT sensor_b_scan_water_height FROM sensor_b ORDER BY created_at DESC LIMIT 1')
    water_level = cursor.fetchone()
    return water_level[0] if water_level else 'N/A'

def get_latest_predicted_water_level_sensor_b():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT prediction_sensor_b_scan_water_height FROM forecasting ORDER BY created_at DESC LIMIT 1')
    water_level = cursor.fetchone()
    return water_level[0] if water_level else 'N/A'

# Define the models (assuming you already have these in models.py)
class WaterPostData(db.Model):
    __tablename__ = 'water_post_data'
    id = db.Column(db.BigInteger, primary_key=True)
    post_code = db.Column(db.String(255))
    post_name = db.Column(db.String(255))
    post_longitude = db.Column(db.String(255))
    post_latitude = db.Column(db.String(255))
    post_river_code = db.Column(db.String(255))
    post_sensor_placement = db.Column(db.Float)
    post_inactive = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class RiverData(db.Model):
    __tablename__ = 'river_data'
    id = db.Column(db.Integer, primary_key=True)
    river_code = db.Column(db.String(255), nullable=False)
    river_point_distance = db.Column(db.Float, nullable=False)
    river_flow_velocity = db.Column(db.Float, nullable=False)
    river_roughness = db.Column(db.Float, nullable=False)
    river_width = db.Column(db.Float, nullable=False)
    river_depth = db.Column(db.Float, nullable=False)
    river_slope = db.Column(db.Float, nullable=False)
    river_safe_height = db.Column(db.Float, nullable=False)
    river_warning_height = db.Column(db.Float, nullable=False)
    river_danger_height = db.Column(db.Float, nullable=False)
    river_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class Subscriber(db.Model):
    __tablename__ = 'sms_subscribers'
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class WhatsappSubscriber(db.Model):
    __tablename__ = 'whatsapp_subscribers'
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    whatsapp_api = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

@app.route('/api/real-time')
def real_time_data():
    latest_water_level = get_latest_water_level()  # Implement this function to get the latest water level
    latest_water_level_sensor_a = get_latest_water_level_sensor_a()  # Implement this function to get the latest water level
    latest_water_level_sensor_b = get_latest_water_level_sensor_b()  # Implement this function to get the latest water level
    status = get_status()  # Implement this function to get the current status
    status_sensor_a = get_sensor_a_status()  # Implement this function to get the current status
    status_sensor_b = get_sensor_b_status()  # Implement this function to get the current status
    latest_predicted_water_level = get_latest_predicted_water_level()  # Implement this function to get the latest predicted water level
    latest_predicted_water_level_sensor_a = get_latest_predicted_water_level_sensor_a()  # Implement this function to get the latest predicted water level
    latest_predicted_water_level_sensor_b = get_latest_predicted_water_level_sensor_b()  # Implement this function to get the latest predicted water level
    predicted_status = get_predicted_status()  # Implement this function to get the predicted status
    predicted_status_sensor_a = get_predicted_sensor_a_status()  # Implement this function to get the predicted status
    predicted_status_sensor_b = get_predicted_sensor_a_status()  # Implement this function to get the predicted status
    
    temperature = get_temperature()
    humidity = get_humidity()
    raindrop = get_raindrop()
    
    current_time = datetime.now().strftime('%H:%M')
    current_date = datetime.now().strftime('%A, %Y-%m-%d')
    
    return jsonify({
        'latest_water_level': latest_water_level,
        'latest_water_level_sensor_a': latest_water_level_sensor_a,
        'latest_water_level_sensor_b': latest_water_level_sensor_b,
        'status': status,
        'status_sensor_a': status_sensor_a,
        'status_sensor_b': status_sensor_b,
        'latest_predicted_water_level': latest_predicted_water_level,
        'latest_predicted_water_level_sensor_a': latest_predicted_water_level_sensor_a,
        'latest_predicted_water_level_sensor_b': latest_predicted_water_level_sensor_b,
        'predicted_status': predicted_status,
        'predicted_status_sensor_a': predicted_status_sensor_a,
        'predicted_status_sensor_b': predicted_status_sensor_b,
        'temperature': temperature,
        'humidity': humidity,
        'raindrop': raindrop,
        'time': current_time,
        'date': current_date
    })

@app.route('/subscribe', methods=['POST'])
def subscribe():
    phone_number = request.form['phone_number']
    new_subscriber = Subscriber(phone_number=phone_number)
    db.session.add(new_subscriber)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/whatsapp-subscribe', methods=['POST'])
def whatsapp_subscribe():
    phone_number = request.form['phone_number']
    whatsapp_api =request.form['whatsapp_api']
    new_subscriber = WhatsappSubscriber(phone_number=phone_number, whatsapp_api=whatsapp_api)
    db.session.add(new_subscriber)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/')
def index():
    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT sensor_a_scan_water_height FROM sensor_a''')  # Example table name
    water_data_a = cursor.fetchall()
    cursor.execute('''SELECT sensor_b_scan_water_height FROM sensor_b''')  # Example table name
    water_data_b = cursor.fetchall()
    cursor.execute('''SELECT * FROM river_data''')  # Example table name
    river_data = cursor.fetchall()
    cursor.execute('''SELECT * FROM water_post_data''')  # Example table name
    water_post_data_no_json = cursor.fetchall()
    cursor.execute('''SELECT * FROM water_post_data''')  # Example table name
    water_post_data = cursor.fetchall()
    water_post_data = [
        [convert_datetime(item) for item in row]
        for row in water_post_data
    ]
    water_post_data_json = json.dumps(water_post_data)
    return render_template('index.html', river_data=river_data, water_post_data=water_post_data_json, water_post_data_no_json=water_post_data_no_json, water_data_a=water_data_a, water_data_b=water_data_b)

# Route to display data and form to edit
@app.route('/edit-data')
def edit_data():
    water_posts = WaterPostData.query.all()
    river_data = RiverData.query.all()
    return render_template('edit_data.html', water_posts=water_posts, river_data=river_data)

# Route to update water post data
@app.route('/update_water_post/<int:id>', methods=['POST'])
def update_water_post(id):
    water_post = WaterPostData.query.get_or_404(id)
    data = request.form
    water_post.post_code = data.get('post_code')
    water_post.post_name = data.get('post_name')
    water_post.post_longitude = data.get('post_longitude')
    water_post.post_latitude = data.get('post_latitude')
    water_post.post_river_code = data.get('post_river_code')
    water_post.post_sensor_placement = data.get('post_sensor_placement')
    water_post.post_inactive = data.get('post_inactive')
    db.session.commit()
    # return jsonify({'message': 'Water post data updated successfully!'})
    return redirect(url_for('edit_data'))

# Route to update river data
@app.route('/update_river_data/<int:id>', methods=['POST'])
def update_river_data(id):
    river = RiverData.query.get_or_404(id)
    data = request.form
    river.river_code = data.get('river_code')
    river.river_point_distance = data.get('river_point_distance')
    river.river_flow_velocity = data.get('river_flow_velocity')
    river.river_roughness = data.get('river_roughness')
    river.river_width = data.get('river_width')
    river.river_depth = data.get('river_depth')
    river.river_slope = data.get('river_slope')
    river.river_safe_height = data.get('river_safe_height')
    river.river_warning_height = data.get('river_warning_height')
    river.river_danger_height = data.get('river_danger_height')
    river.river_name = data.get('river_name')
    db.session.commit()
    # return jsonify({'message': 'River data updated successfully!'})
    return redirect(url_for('edit_data'))

@app.route('/water-data')
def water_data():
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    per_page = 10
    offset = (page - 1) * per_page
    water_data, total = get_data('water_data', offset=offset, per_page=per_page)

    latest_water_level = water_data[0][3] if water_data else 'N/A'
    current_time = datetime.now().strftime('%H:%M')
    current_date = datetime.now().strftime('%A, %Y-%m-%d')
    
    labels = [convert_datetime(row[5]) for row in water_data]  # Use row 5 as datetime label
    values = [row[3] for row in water_data]  # Use row 4 as value

    water_data_prediction, total = get_data('forecasting', offset=offset, per_page=per_page)

    latest_predicted_water_level = water_data_prediction[0][4] if water_data_prediction else 'N/A'

    labels_prediction = [convert_datetime(row[8]) for row in water_data_prediction]  # Use row 5 as datetime label
    values_prediction = [row[4] for row in water_data_prediction]  # Use row 4 as value

    status = get_status()
    predicted_status = get_predicted_status()

    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')
    return render_template('water_data.html', 
        water_data=water_data, 
        page=page, 
        per_page=per_page, 
        pagination=pagination, 
        labels=labels, 
        values=values, 
        labels_prediction=labels_prediction, 
        values_prediction=values_prediction,         
        date=current_date,
        time=current_time,
        latest_water_level=latest_water_level,
        latest_predicted_water_level=latest_predicted_water_level,
        status=status,
        predicted_status=predicted_status
)

@app.route('/api/water-data')
def api_water_data():
    water_data, total = get_data('water_data', offset=0, per_page=100)  # Adjust as necessary
    labels = [convert_datetime(row[5]) for row in water_data]  # Use row 5 as datetime label
    values = [row[3] for row in water_data]  # Use row 4 as value

    water_data_prediction, total = get_data('forecasting', offset=0, per_page=100)  # Adjust as necessary
    labels_prediction = [convert_datetime(row[8]) for row in water_data_prediction]  # Use row 5 as datetime label
    values_prediction = [row[4] for row in water_data_prediction]  # Use row 4 as value

    limiters_data, total = get_data('river_data', offset=0, per_page=100)  # Fetch limiters data
    safe_limiters = [{'name': f'({row[8] * row[6]})', 'value': row[8] * row[6], 'color': 'rgba(0, 128, 0, 0.6)'} for row in limiters_data]  # Green
    warning_limiters = [{'name': f'({row[9] * row[6]})', 'value': row[9] * row[6], 'color': 'rgba(255, 165, 0, 0.6)'} for row in limiters_data]  # Orange
    danger_limiters = [{'name': f'({row[10] * row[6]})', 'value': row[10] * row[6], 'color': 'rgba(255, 0, 0, 0.6)'} for row in limiters_data]  # Red
    limiters = safe_limiters + warning_limiters + danger_limiters

    return jsonify(labels=labels, values=values, labels_prediction=labels_prediction, values_prediction=values_prediction, limiters=limiters)

@app.route('/water-elevation-plot.png')
def plot_png():
    # Get actual water data
    water_data, total = get_data('water_data', offset=0, per_page=100)  # Adjust as necessary
    actual_labels = [pd.to_datetime(row[5]) for row in water_data]  # Convert to datetime
    actual_values = [row[3] for row in water_data]

    # Get prediction data
    prediction_water_data, total = get_data('forecasting', offset=0, per_page=100)  # Adjust as necessary
    prediction_labels = [pd.to_datetime(row[8]) for row in prediction_water_data]  # Convert to datetime
    prediction_values = [row[4] for row in prediction_water_data]

    fig, ax = plt.subplots()
    ax.plot(actual_labels, actual_values, label='Water Data')
    ax.plot(prediction_labels, prediction_values, label='Prediction Data', linestyle='--')

    ax.set_xlabel('Date')
    ax.set_ylabel('Value')
    ax.set_title('Water Data and Prediction Over Time')
    ax.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/sensor-a-data')
def water_data_sensor_a():
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    per_page = 10
    offset = (page - 1) * per_page
    water_data, total = get_data('sensor_a', offset=offset, per_page=per_page)

    latest_water_level = water_data[0][3] if water_data else 'N/A'
    current_time = datetime.now().strftime('%H:%M')
    current_date = datetime.now().strftime('%A, %Y-%m-%d')
    
    labels = [convert_datetime(row[7]) for row in water_data]  # Use row 5 as datetime label
    values = [row[4] for row in water_data]  # Use row 4 as value

    water_data_prediction, total = get_data('forecasting', offset=offset, per_page=per_page)

    latest_predicted_water_level = water_data_prediction[0][4] if water_data_prediction else 'N/A'

    labels_prediction = [convert_datetime(row[8]) for row in water_data_prediction]  # Use row 5 as datetime label
    values_prediction = [row[2] for row in water_data_prediction]  # Use row 4 as value

    status = get_sensor_a_status()
    predicted_status = get_predicted_sensor_a_status()

    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')
    return render_template('sensor_a_data.html', 
        water_data=water_data, 
        page=page, 
        per_page=per_page, 
        pagination=pagination, 
        labels=labels, 
        values=values, 
        labels_prediction=labels_prediction, 
        values_prediction=values_prediction,         
        date=current_date,
        time=current_time,
        latest_water_level=latest_water_level,
        latest_predicted_water_level=latest_predicted_water_level,
        status=status,
        predicted_status=predicted_status
)

@app.route('/api/sensor-a-data')
def api_water_data_sensor_a():
    water_data, total = get_data('sensor_a', offset=0, per_page=100)  # Adjust as necessary
    labels = [convert_datetime(row[7]) for row in water_data]  # Use row 5 as datetime label
    values = [row[4] for row in water_data]  # Use row 4 as value

    water_data_prediction, total = get_data('forecasting', offset=0, per_page=100)  # Adjust as necessary
    labels_prediction = [convert_datetime(row[8]) for row in water_data_prediction]  # Use row 5 as datetime label
    values_prediction = [row[2] for row in water_data_prediction]  # Use row 4 as value

    limiters_data, total = get_data('river_data', offset=0, per_page=100)  # Fetch limiters data
    safe_limiters = [{'name': f'({row[8] * row[6]})', 'value': row[8] * row[6], 'color': 'rgba(0, 128, 0, 0.6)'} for row in limiters_data]  # Green
    warning_limiters = [{'name': f'({row[9] * row[6]})', 'value': row[9] * row[6], 'color': 'rgba(255, 165, 0, 0.6)'} for row in limiters_data]  # Orange
    danger_limiters = [{'name': f'({row[10] * row[6]})', 'value': row[10] * row[6], 'color': 'rgba(255, 0, 0, 0.6)'} for row in limiters_data]  # Red
    limiters = safe_limiters + warning_limiters + danger_limiters

    return jsonify(labels=labels, values=values, labels_prediction=labels_prediction, values_prediction=values_prediction, limiters=limiters)

@app.route('/sensor-a-data-plot.png')
def plot_sensor_a_png():
    # Get actual water data
    water_data, total = get_data('sensor_a', offset=0, per_page=100)  # Adjust as necessary
    actual_labels = [pd.to_datetime(row[7]) for row in water_data]  # Convert to datetime
    actual_values = [row[4] for row in water_data]

    # Get prediction data
    prediction_water_data, total = get_data('forecasting', offset=0, per_page=100)  # Adjust as necessary
    prediction_labels = [pd.to_datetime(row[8]) for row in prediction_water_data]  # Convert to datetime
    prediction_values = [row[2] for row in prediction_water_data]

    fig, ax = plt.subplots()
    ax.plot(actual_labels, actual_values, label='Water Data')
    ax.plot(prediction_labels, prediction_values, label='Prediction Data', linestyle='--')

    ax.set_xlabel('Date')
    ax.set_ylabel('Value')
    ax.set_title('Water Data and Prediction Over Time')
    ax.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/sensor-b-data')
def water_data_sensor_b():
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    per_page = 10
    offset = (page - 1) * per_page
    water_data, total = get_data('sensor_b', offset=offset, per_page=per_page)

    latest_water_level = water_data[0][3] if water_data else 'N/A'
    current_time = datetime.now().strftime('%H:%M')
    current_date = datetime.now().strftime('%A, %Y-%m-%d')
    
    labels = [convert_datetime(row[7]) for row in water_data]  # Use row 5 as datetime label
    values = [row[4] for row in water_data]  # Use row 4 as value

    water_data_prediction, total = get_data('forecasting', offset=offset, per_page=per_page)

    latest_predicted_water_level = water_data_prediction[0][4] if water_data_prediction else 'N/A'

    labels_prediction = [convert_datetime(row[8]) for row in water_data_prediction]  # Use row 5 as datetime label
    values_prediction = [row[3] for row in water_data_prediction]  # Use row 4 as value

    status = get_sensor_b_status()
    predicted_status = get_predicted_sensor_b_status()

    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')
    return render_template('sensor_b_data.html', 
        water_data=water_data, 
        page=page, 
        per_page=per_page, 
        pagination=pagination, 
        labels=labels, 
        values=values, 
        labels_prediction=labels_prediction, 
        values_prediction=values_prediction,         
        date=current_date,
        time=current_time,
        latest_water_level=latest_water_level,
        latest_predicted_water_level=latest_predicted_water_level,
        status=status,
        predicted_status=predicted_status
)

@app.route('/api/sensor-b-data')
def api_water_data_sensor_b():
    water_data, total = get_data('sensor_b', offset=0, per_page=100)  # Adjust as necessary
    labels = [convert_datetime(row[7]) for row in water_data]  # Use row 5 as datetime label
    values = [row[4] for row in water_data]  # Use row 4 as value

    water_data_prediction, total = get_data('forecasting', offset=0, per_page=100)  # Adjust as necessary
    labels_prediction = [convert_datetime(row[8]) for row in water_data_prediction]  # Use row 5 as datetime label
    values_prediction = [row[3] for row in water_data_prediction]  # Use row 4 as value

    limiters_data, total = get_data('river_data', offset=0, per_page=100)  # Fetch limiters data
    safe_limiters = [{'name': f'({row[8] * row[6]})', 'value': row[8] * row[6], 'color': 'rgba(0, 128, 0, 0.6)'} for row in limiters_data]  # Green
    warning_limiters = [{'name': f'({row[9] * row[6]})', 'value': row[9] * row[6], 'color': 'rgba(255, 165, 0, 0.6)'} for row in limiters_data]  # Orange
    danger_limiters = [{'name': f'({row[10] * row[6]})', 'value': row[10] * row[6], 'color': 'rgba(255, 0, 0, 0.6)'} for row in limiters_data]  # Red
    limiters = safe_limiters + warning_limiters + danger_limiters

    return jsonify(labels=labels, values=values, labels_prediction=labels_prediction, values_prediction=values_prediction, limiters=limiters)

@app.route('/sensor-b-data-plot.png')
def plot_sensor_b_png():
    # Get actual water data
    water_data, total = get_data('sensor_b', offset=0, per_page=100)  # Adjust as necessary
    actual_labels = [pd.to_datetime(row[7]) for row in water_data]  # Convert to datetime
    actual_values = [row[4] for row in water_data]

    # Get prediction data
    prediction_water_data, total = get_data('forecasting', offset=0, per_page=100)  # Adjust as necessary
    prediction_labels = [pd.to_datetime(row[8]) for row in prediction_water_data]  # Convert to datetime
    prediction_values = [row[3] for row in prediction_water_data]

    fig, ax = plt.subplots()
    ax.plot(actual_labels, actual_values, label='Water Data')
    ax.plot(prediction_labels, prediction_values, label='Prediction Data', linestyle='--')

    ax.set_xlabel('Date')
    ax.set_ylabel('Value')
    ax.set_title('Water Data and Prediction Over Time')
    ax.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

# if __name__ == '__main__':
#     app.run(debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

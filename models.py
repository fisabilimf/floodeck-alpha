from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint
import re

Base = declarative_base()

class WaterPostData(Base):
    """Model for water post data"""
    __tablename__ = 'water_post_data'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    post_code = Column(String(255), nullable=False, unique=True, index=True)
    post_name = Column(String(255), nullable=False)
    post_longitude = Column(String(255), nullable=False)
    post_latitude = Column(String(255), nullable=False)
    post_river_code = Column(String(255), nullable=False, index=True)
    post_sensor_placement = Column(Float, nullable=False)
    post_inactive = Column(String(255), default='active')
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    sensor_a_data = relationship("SensorA", back_populates="water_post")
    sensor_b_data = relationship("SensorB", back_populates="water_post")
    water_data = relationship("WaterData", back_populates="water_post")
    forecasting_data = relationship("Forecasting", back_populates="water_post")
    
    def __repr__(self):
        return f"<WaterPostData(post_code='{self.post_code}', post_name='{self.post_name}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'post_code': self.post_code,
            'post_name': self.post_name,
            'post_longitude': self.post_longitude,
            'post_latitude': self.post_latitude,
            'post_river_code': self.post_river_code,
            'post_sensor_placement': self.post_sensor_placement,
            'post_inactive': self.post_inactive,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RiverData(Base):
    """Model for river data"""
    __tablename__ = 'river_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    river_code = Column(String(255), nullable=False, unique=True, index=True)
    river_point_distance = Column(Float, nullable=False)
    river_flow_velocity = Column(Float, nullable=False)
    river_roughness = Column(Float, nullable=False)
    river_width = Column(Float, nullable=False)
    river_depth = Column(Float, nullable=False)
    river_slope = Column(Float, nullable=False)
    river_safe_height = Column(Float, nullable=False)
    river_warning_height = Column(Float, nullable=False)
    river_danger_height = Column(Float, nullable=False)
    river_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    water_posts = relationship("WaterPostData", backref="river")
    
    def __repr__(self):
        return f"<RiverData(river_code='{self.river_code}', river_name='{self.river_name}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'river_code': self.river_code,
            'river_point_distance': self.river_point_distance,
            'river_flow_velocity': self.river_flow_velocity,
            'river_roughness': self.river_roughness,
            'river_width': self.river_width,
            'river_depth': self.river_depth,
            'river_slope': self.river_slope,
            'river_safe_height': self.river_safe_height,
            'river_warning_height': self.river_warning_height,
            'river_danger_height': self.river_danger_height,
            'river_name': self.river_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SensorA(Base):
    """Model for Sensor A data"""
    __tablename__ = 'sensor_a'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    water_post_code = Column(String(255), nullable=False, index=True)
    sensor_a_temperature = Column(Float, nullable=False)
    sensor_a_humidity = Column(Float, nullable=False)
    sensor_a_scan_water_height = Column(Float, nullable=False)
    sensor_a_raindrop = Column(Float, nullable=False)
    sensor_a_status = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Foreign key relationship
    water_post_id = Column(BigInteger, nullable=False)
    water_post = relationship("WaterPostData", back_populates="sensor_a_data")
    
    def __repr__(self):
        return f"<SensorA(water_post_code='{self.water_post_code}', status='{self.sensor_a_status}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'water_post_code': self.water_post_code,
            'sensor_a_temperature': self.sensor_a_temperature,
            'sensor_a_humidity': self.sensor_a_humidity,
            'sensor_a_scan_water_height': self.sensor_a_scan_water_height,
            'sensor_a_raindrop': self.sensor_a_raindrop,
            'sensor_a_status': self.sensor_a_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SensorB(Base):
    """Model for Sensor B data"""
    __tablename__ = 'sensor_b'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    water_post_code = Column(String(255), nullable=False, index=True)
    sensor_b_scan_water_height = Column(Float, nullable=False)
    sensor_b_status = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Foreign key relationship
    water_post_id = Column(BigInteger, nullable=False)
    water_post = relationship("WaterPostData", back_populates="sensor_b_data")
    
    def __repr__(self):
        return f"<SensorB(water_post_code='{self.water_post_code}', status='{self.sensor_b_status}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'water_post_code': self.water_post_code,
            'sensor_b_scan_water_height': self.sensor_b_scan_water_height,
            'sensor_b_status': self.sensor_b_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class WaterData(Base):
    """Model for water data"""
    __tablename__ = 'water_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    water_post_code = Column(String(255), nullable=False, index=True)
    water_elevation = Column(Float, nullable=False)
    water_status = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Foreign key relationship
    water_post_id = Column(BigInteger, nullable=False)
    water_post = relationship("WaterPostData", back_populates="water_data")
    
    def __repr__(self):
        return f"<WaterData(water_post_code='{self.water_post_code}', status='{self.water_status}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'water_post_code': self.water_post_code,
            'water_elevation': self.water_elevation,
            'water_status': self.water_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Forecasting(Base):
    """Model for forecasting data"""
    __tablename__ = 'forecasting'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    river_code = Column(String(255), nullable=False, index=True)
    prediction_sensor_a_scan_water_height = Column(Float, nullable=False)
    prediction_sensor_b_scan_water_height = Column(Float, nullable=False)
    prediction_water_elevation = Column(Float, nullable=False)
    water_sensor_a_status = Column(String(255), nullable=False)
    water_sensor_b_status = Column(String(255), nullable=False)
    water_status = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Foreign key relationship
    water_post_id = Column(BigInteger, nullable=False)
    water_post = relationship("WaterPostData", back_populates="forecasting_data")
    
    def __repr__(self):
        return f"<Forecasting(river_code='{self.river_code}', status='{self.water_status}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'river_code': self.river_code,
            'prediction_sensor_a_scan_water_height': self.prediction_sensor_a_scan_water_height,
            'prediction_sensor_b_scan_water_height': self.prediction_sensor_b_scan_water_height,
            'prediction_water_elevation': self.prediction_water_elevation,
            'water_sensor_a_status': self.water_sensor_a_status,
            'water_sensor_b_status': self.water_sensor_b_status,
            'water_status': self.water_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Subscriber(Base):
    """Model for SMS subscribers"""
    __tablename__ = 'sms_subscribers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(20), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<Subscriber(phone_number='{self.phone_number}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def validate_phone_number(phone_number):
        """Validate phone number format"""
        pattern = r'^\+?1?\d{9,15}$'
        return bool(re.match(pattern, phone_number))

class WhatsappSubscriber(Base):
    """Model for WhatsApp subscribers"""
    __tablename__ = 'whatsapp_subscribers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(20), nullable=False, unique=True, index=True)
    whatsapp_api = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<WhatsappSubscriber(phone_number='{self.phone_number}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'whatsapp_api': self.whatsapp_api,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

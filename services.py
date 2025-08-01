import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from models import (
    WaterPostData, RiverData, SensorA, SensorB, 
    WaterData, Forecasting, Subscriber, WhatsappSubscriber
)
from cache import cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataService:
    """Service class for data operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    @cache.memoize(timeout=60)  # Cache for 1 minute
    def get_latest_sensor_data(self, sensor_type: str, post_code: str = None) -> Optional[Dict]:
        """Get latest sensor data with caching"""
        try:
            if sensor_type == 'sensor_a':
                query = self.db.query(SensorA)
                if post_code:
                    query = query.filter(SensorA.water_post_code == post_code)
                latest = query.order_by(desc(SensorA.created_at)).first()
                
                if latest:
                    return {
                        'temperature': latest.sensor_a_temperature,
                        'humidity': latest.sensor_a_humidity,
                        'water_height': latest.sensor_a_scan_water_height,
                        'raindrop': latest.sensor_a_raindrop,
                        'status': latest.sensor_a_status,
                        'created_at': latest.created_at
                    }
            
            elif sensor_type == 'sensor_b':
                query = self.db.query(SensorB)
                if post_code:
                    query = query.filter(SensorB.water_post_code == post_code)
                latest = query.order_by(desc(SensorB.created_at)).first()
                
                if latest:
                    return {
                        'water_height': latest.sensor_b_scan_water_height,
                        'status': latest.sensor_b_status,
                        'created_at': latest.created_at
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest {sensor_type} data: {e}")
            return None
    
    @cache.memoize(timeout=60)
    def get_latest_water_data(self, post_code: str = None) -> Optional[Dict]:
        """Get latest water data with caching"""
        try:
            query = self.db.query(WaterData)
            if post_code:
                query = query.filter(WaterData.water_post_code == post_code)
            latest = query.order_by(desc(WaterData.created_at)).first()
            
            if latest:
                return {
                    'water_elevation': latest.water_elevation,
                    'status': latest.water_status,
                    'created_at': latest.created_at
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest water data: {e}")
            return None
    
    @cache.memoize(timeout=60)
    def get_latest_forecasting(self, post_code: str = None) -> Optional[Dict]:
        """Get latest forecasting data with caching"""
        try:
            query = self.db.query(Forecasting)
            if post_code:
                query = query.filter(Forecasting.river_code == post_code)
            latest = query.order_by(desc(Forecasting.created_at)).first()
            
            if latest:
                return {
                    'prediction_sensor_a_height': latest.prediction_sensor_a_scan_water_height,
                    'prediction_sensor_b_height': latest.prediction_sensor_b_scan_water_height,
                    'prediction_water_elevation': latest.prediction_water_elevation,
                    'sensor_a_status': latest.water_sensor_a_status,
                    'sensor_b_status': latest.water_sensor_b_status,
                    'water_status': latest.water_status,
                    'created_at': latest.created_at
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest forecasting data: {e}")
            return None
    
    def get_paginated_data(self, model_class, page: int = 1, per_page: int = 10, 
                          filters: Dict = None) -> Tuple[List, int]:
        """Get paginated data with optional filters"""
        try:
            query = self.db.query(model_class)
            
            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    if hasattr(model_class, key) and value is not None:
                        query = query.filter(getattr(model_class, key) == value)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            data = query.order_by(desc(model_class.created_at)).offset(offset).limit(per_page).all()
            
            return data, total
            
        except Exception as e:
            logger.error(f"Error getting paginated data: {e}")
            return [], 0
    
    def get_water_posts_with_coordinates(self) -> List[Dict]:
        """Get all water posts with coordinates for map display"""
        try:
            posts = self.db.query(WaterPostData).filter(
                WaterPostData.post_inactive == 'active'
            ).all()
            
            return [post.to_dict() for post in posts]
            
        except Exception as e:
            logger.error(f"Error getting water posts: {e}")
            return []
    
    def get_river_data(self) -> List[Dict]:
        """Get all river data"""
        try:
            rivers = self.db.query(RiverData).all()
            return [river.to_dict() for river in rivers]
            
        except Exception as e:
            logger.error(f"Error getting river data: {e}")
            return []

class NotificationService:
    """Service class for notification operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def add_sms_subscriber(self, phone_number: str) -> bool:
        """Add new SMS subscriber with validation"""
        try:
            if not Subscriber.validate_phone_number(phone_number):
                logger.warning(f"Invalid phone number format: {phone_number}")
                return False
            
            # Check if already exists
            existing = self.db.query(Subscriber).filter(
                Subscriber.phone_number == phone_number
            ).first()
            
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    existing.updated_at = datetime.now()
                    self.db.commit()
                    logger.info(f"Reactivated SMS subscriber: {phone_number}")
                return True
            
            # Create new subscriber
            new_subscriber = Subscriber(phone_number=phone_number)
            self.db.add(new_subscriber)
            self.db.commit()
            
            logger.info(f"Added new SMS subscriber: {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding SMS subscriber: {e}")
            self.db.rollback()
            return False
    
    def add_whatsapp_subscriber(self, phone_number: str, whatsapp_api: str) -> bool:
        """Add new WhatsApp subscriber with validation"""
        try:
            if not Subscriber.validate_phone_number(phone_number):
                logger.warning(f"Invalid phone number format: {phone_number}")
                return False
            
            # Check if already exists
            existing = self.db.query(WhatsappSubscriber).filter(
                WhatsappSubscriber.phone_number == phone_number
            ).first()
            
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    existing.updated_at = datetime.now()
                    self.db.commit()
                    logger.info(f"Reactivated WhatsApp subscriber: {phone_number}")
                return True
            
            # Create new subscriber
            new_subscriber = WhatsappSubscriber(
                phone_number=phone_number,
                whatsapp_api=whatsapp_api
            )
            self.db.add(new_subscriber)
            self.db.commit()
            
            logger.info(f"Added new WhatsApp subscriber: {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding WhatsApp subscriber: {e}")
            self.db.rollback()
            return False
    
    def get_active_subscribers(self, notification_type: str = 'sms') -> List[Dict]:
        """Get all active subscribers"""
        try:
            if notification_type == 'sms':
                subscribers = self.db.query(Subscriber).filter(
                    Subscriber.is_active == True
                ).all()
            else:
                subscribers = self.db.query(WhatsappSubscriber).filter(
                    WhatsappSubscriber.is_active == True
                ).all()
            
            return [sub.to_dict() for sub in subscribers]
            
        except Exception as e:
            logger.error(f"Error getting active subscribers: {e}")
            return []

class AnalyticsService:
    """Service class for analytics and reporting"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_water_level_trend(self, days: int = 7, post_code: str = None) -> List[Dict]:
        """Get water level trend for the last N days"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            query = self.db.query(
                WaterData.water_elevation,
                WaterData.created_at,
                WaterData.water_status
            ).filter(WaterData.created_at >= start_date)
            
            if post_code:
                query = query.filter(WaterData.water_post_code == post_code)
            
            data = query.order_by(WaterData.created_at).all()
            
            return [
                {
                    'water_elevation': row.water_elevation,
                    'created_at': row.created_at.isoformat(),
                    'status': row.water_status
                }
                for row in data
            ]
            
        except Exception as e:
            logger.error(f"Error getting water level trend: {e}")
            return []
    
    def get_sensor_statistics(self, sensor_type: str, hours: int = 24) -> Dict:
        """Get sensor statistics for the last N hours"""
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            if sensor_type == 'sensor_a':
                query = self.db.query(
                    func.avg(SensorA.sensor_a_temperature).label('avg_temperature'),
                    func.avg(SensorA.sensor_a_humidity).label('avg_humidity'),
                    func.avg(SensorA.sensor_a_scan_water_height).label('avg_water_height'),
                    func.avg(SensorA.sensor_a_raindrop).label('avg_raindrop'),
                    func.count(SensorA.id).label('total_readings')
                ).filter(SensorA.created_at >= start_time)
                
                result = query.first()
                
                return {
                    'avg_temperature': float(result.avg_temperature) if result.avg_temperature else 0,
                    'avg_humidity': float(result.avg_humidity) if result.avg_humidity else 0,
                    'avg_water_height': float(result.avg_water_height) if result.avg_water_height else 0,
                    'avg_raindrop': float(result.avg_raindrop) if result.avg_raindrop else 0,
                    'total_readings': result.total_readings
                }
            
            elif sensor_type == 'sensor_b':
                query = self.db.query(
                    func.avg(SensorB.sensor_b_scan_water_height).label('avg_water_height'),
                    func.count(SensorB.id).label('total_readings')
                ).filter(SensorB.created_at >= start_time)
                
                result = query.first()
                
                return {
                    'avg_water_height': float(result.avg_water_height) if result.avg_water_height else 0,
                    'total_readings': result.total_readings
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting sensor statistics: {e}")
            return {}
    
    def get_flood_risk_assessment(self, post_code: str) -> Dict:
        """Get flood risk assessment for a specific post"""
        try:
            # Get latest water data
            latest_water = self.db.query(WaterData).filter(
                WaterData.water_post_code == post_code
            ).order_by(desc(WaterData.created_at)).first()
            
            if not latest_water:
                return {'risk_level': 'unknown', 'message': 'No data available'}
            
            # Get river data for thresholds
            river_data = self.db.query(RiverData).filter(
                RiverData.river_code == post_code
            ).first()
            
            if not river_data:
                return {'risk_level': 'unknown', 'message': 'No river data available'}
            
            water_level = latest_water.water_elevation
            safe_height = river_data.river_safe_height
            warning_height = river_data.river_warning_height
            danger_height = river_data.river_danger_height
            
            # Calculate risk level
            if water_level >= danger_height:
                risk_level = 'high'
                message = 'DANGER: Water level is at dangerous levels!'
            elif water_level >= warning_height:
                risk_level = 'medium'
                message = 'WARNING: Water level is approaching dangerous levels'
            elif water_level >= safe_height:
                risk_level = 'low'
                message = 'CAUTION: Water level is above safe levels'
            else:
                risk_level = 'safe'
                message = 'SAFE: Water level is within normal range'
            
            return {
                'risk_level': risk_level,
                'message': message,
                'current_level': water_level,
                'safe_threshold': safe_height,
                'warning_threshold': warning_height,
                'danger_threshold': danger_height,
                'last_updated': latest_water.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting flood risk assessment: {e}")
            return {'risk_level': 'error', 'message': 'Error calculating risk assessment'} 

class ForecastingService:
    """Enhanced forecasting service with ensemble methods"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.forecaster = None
        self._initialize_forecaster()
    
    def _initialize_forecaster(self):
        """Initialize the enhanced forecaster"""
        try:
            from python.optimized_forecasting import EnhancedFloodForecaster
            
            db_config = {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'database': 'floodeck_alpha'
            }
            
            self.forecaster = EnhancedFloodForecaster(db_config)
            
            # Try to load pre-trained models
            try:
                self.forecaster.load_models()
                logger.info("Pre-trained models loaded successfully")
            except:
                logger.info("No pre-trained models found, will train new models")
                
        except Exception as e:
            logger.error(f"Error initializing forecaster: {e}")
    
    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def get_enhanced_prediction(self, post_code: str, hours_ahead: int = 6) -> Dict:
        """Get enhanced flood prediction using ensemble methods"""
        try:
            if not self.forecaster:
                return {'error': 'Forecaster not initialized'}
            
            # Load recent data
            df = self.forecaster.load_and_preprocess_data(post_code, days_back=30)
            
            if df.empty:
                return {'error': 'No data available for prediction'}
            
            # Make ensemble predictions
            predictions = self.forecaster.predict_ensemble(df)
            
            # Get river data for risk assessment
            river_data = self.db.query(RiverData).filter(
                RiverData.river_code == post_code
            ).first()
            
            if not river_data:
                return {'error': 'River data not found'}
            
            river_dict = {
                'river_safe_height': river_data.river_safe_height,
                'river_warning_height': river_data.river_warning_height,
                'river_danger_height': river_data.river_danger_height
            }
            
            # Calculate risk for ensemble prediction
            ensemble_pred = predictions.get('ensemble', predictions.get('lstm', [0]))
            latest_prediction = ensemble_pred[-1] if len(ensemble_pred) > 0 else 0
            
            risk_assessment = self.forecaster.calculate_flood_risk(latest_prediction, river_dict)
            
            # Evaluate model performance
            model_performance = self.forecaster.evaluate_models(df)
            
            return {
                'predictions': {
                    'ensemble': ensemble_pred[-hours_ahead:] if len(ensemble_pred) >= hours_ahead else ensemble_pred,
                    'lstm': predictions.get('lstm', [])[-hours_ahead:] if 'lstm' in predictions else [],
                    'random_forest': predictions.get('random_forest', [])[-hours_ahead:] if 'random_forest' in predictions else [],
                    'gradient_boosting': predictions.get('gradient_boosting', [])[-hours_ahead:] if 'gradient_boosting' in predictions else []
                },
                'risk_assessment': risk_assessment,
                'model_performance': model_performance,
                'confidence_score': self._calculate_confidence_score(model_performance),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting enhanced prediction: {e}")
            return {'error': str(e)}
    
    def _calculate_confidence_score(self, model_performance: Dict) -> float:
        """Calculate confidence score based on model performance"""
        if not model_performance:
            return 0.0
        
        # Use R2 scores to calculate confidence
        r2_scores = [metrics.get('R2', 0) for metrics in model_performance.values()]
        avg_r2 = sum(r2_scores) / len(r2_scores)
        
        # Convert to confidence score (0-100)
        confidence = max(0, min(100, avg_r2 * 100))
        
        return round(confidence, 2)
    
    def retrain_models(self, post_code: str) -> Dict:
        """Retrain forecasting models with latest data"""
        try:
            if not self.forecaster:
                return {'error': 'Forecaster not initialized'}
            
            # Load more data for retraining
            df = self.forecaster.load_and_preprocess_data(post_code, days_back=60)
            
            if df.empty:
                return {'error': 'No data available for retraining'}
            
            # Train models
            history = self.forecaster.train_ensemble_models(df)
            
            # Evaluate new models
            performance = self.forecaster.evaluate_models(df)
            
            # Save models
            self.forecaster.save_models()
            
            return {
                'status': 'success',
                'message': 'Models retrained successfully',
                'performance': performance,
                'training_history': {
                    'loss': history.history['loss'][-1] if history else None,
                    'val_loss': history.history['val_loss'][-1] if history else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error retraining models: {e}")
            return {'error': str(e)}
    
    def get_feature_importance(self) -> Dict:
        """Get feature importance from trained models"""
        try:
            if not self.forecaster or not self.forecaster.feature_importance:
                return {'error': 'No feature importance data available'}
            
            return self.forecaster.feature_importance
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {'error': str(e)} 
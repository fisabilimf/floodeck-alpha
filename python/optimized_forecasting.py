"""
Optimized Flood Forecasting Module
Enhanced version with better ML practices, feature engineering, and ensemble methods
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional, Conv1D, MaxPooling1D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator

# Statistical Libraries
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Database
import pymysql
from sqlalchemy import create_engine, text
import os

class EnhancedFloodForecaster:
    """
    Enhanced flood forecasting system with multiple models and ensemble methods
    """
    
    def __init__(self, db_config: Dict, model_path: str = "models/"):
        self.db_config = db_config
        self.model_path = model_path
        self.scalers = {}
        self.models = {}
        self.feature_importance = {}
        
        # Initialize database connection
        self.engine = create_engine(
            f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
    
    def load_and_preprocess_data(self, post_code: str, days_back: int = 30) -> pd.DataFrame:
        """
        Load and preprocess sensor data with enhanced feature engineering
        """
        try:
            # Load sensor data
            query = f"""
            SELECT 
                sa.sensor_a_scan_water_height as water_height_a,
                sa.sensor_a_temperature as temperature,
                sa.sensor_a_humidity as humidity,
                sa.sensor_a_raindrop as rainfall,
                sb.sensor_b_scan_water_height as water_height_b,
                sa.created_at,
                rd.river_width,
                rd.river_depth,
                rd.river_slope,
                rd.river_flow_velocity,
                rd.river_roughness
            FROM sensor_a sa
            LEFT JOIN sensor_b sb ON sa.water_post_code = sb.water_post_code 
                AND DATE(sa.created_at) = DATE(sb.created_at)
            LEFT JOIN river_data rd ON sa.water_post_code = rd.river_code
            WHERE sa.water_post_code = '{post_code}'
            AND sa.created_at >= DATE_SUB(NOW(), INTERVAL {days_back} DAY)
            ORDER BY sa.created_at
            """
            
            df = pd.read_sql(query, self.engine)
            
            if df.empty:
                raise ValueError(f"No data found for post_code: {post_code}")
            
            # Data cleaning
            df = self._clean_data(df)
            
            # Feature engineering
            df = self._engineer_features(df)
            
            return df
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enhanced data cleaning with outlier detection
        """
        # Remove duplicates
        df = df.drop_duplicates(subset=['created_at'])
        
        # Handle missing values
        df['water_height_a'] = df['water_height_a'].fillna(method='ffill')
        df['water_height_b'] = df['water_height_b'].fillna(method='ffill')
        df['temperature'] = df['temperature'].fillna(df['temperature'].mean())
        df['humidity'] = df['humidity'].fillna(df['humidity'].mean())
        df['rainfall'] = df['rainfall'].fillna(0)
        
        # Outlier detection using IQR method
        for col in ['water_height_a', 'water_height_b', 'temperature', 'humidity']:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            # Replace outliers with median
            df[col] = np.where((df[col] < lower_bound) | (df[col] > upper_bound), 
                              df[col].median(), df[col])
        
        return df
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Advanced feature engineering for better prediction
        """
        # Time-based features
        df['hour'] = df['created_at'].dt.hour
        df['day_of_week'] = df['created_at'].dt.dayofweek
        df['month'] = df['created_at'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Lag features (previous values)
        for lag in [1, 2, 3, 6, 12, 24]:
            df[f'water_height_a_lag_{lag}'] = df['water_height_a'].shift(lag)
            df[f'water_height_b_lag_{lag}'] = df['water_height_b'].shift(lag)
            df[f'rainfall_lag_{lag}'] = df['rainfall'].shift(lag)
        
        # Rolling statistics
        for window in [3, 6, 12, 24]:
            df[f'water_height_a_rolling_mean_{window}'] = df['water_height_a'].rolling(window=window).mean()
            df[f'water_height_a_rolling_std_{window}'] = df['water_height_a'].rolling(window=window).std()
            df[f'rainfall_rolling_sum_{window}'] = df['rainfall'].rolling(window=window).sum()
        
        # Rate of change
        df['water_height_a_change'] = df['water_height_a'].diff()
        df['water_height_b_change'] = df['water_height_b'].diff()
        df['rainfall_change'] = df['rainfall'].diff()
        
        # Hydrological features
        df['water_height_diff'] = df['water_height_b'] - df['water_height_a']
        df['water_height_ratio'] = df['water_height_a'] / (df['water_height_b'] + 1e-8)
        
        # Weather interaction features
        df['temp_humidity_interaction'] = df['temperature'] * df['humidity']
        df['rainfall_intensity'] = df['rainfall'] * df['humidity']
        
        # Remove rows with NaN values (from lag features)
        df = df.dropna()
        
        return df
    
    def prepare_sequences(self, df: pd.DataFrame, target_col: str, 
                         sequence_length: int = 24, test_size: float = 0.2) -> Tuple:
        """
        Prepare sequences for LSTM with proper train-test split
        """
        # Select features for modeling
        feature_cols = [col for col in df.columns if col not in ['created_at', 'water_post_code']]
        
        # Scale the data
        scaler = RobustScaler()
        scaled_data = scaler.fit_transform(df[feature_cols])
        
        # Create sequences
        X, y = [], []
        for i in range(sequence_length, len(scaled_data)):
            X.append(scaled_data[i-sequence_length:i])
            y.append(scaled_data[i, feature_cols.index(target_col)])
        
        X, y = np.array(X), np.array(y)
        
        # Time series split
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        self.scalers[target_col] = scaler
        
        return X_train, X_test, y_train, y_test, feature_cols
    
    def build_enhanced_lstm(self, input_shape: Tuple, units: List[int] = [128, 64, 32]) -> tf.keras.Model:
        """
        Build enhanced LSTM model with multiple layers and regularization
        """
        model = Sequential([
            # First LSTM layer with return sequences
            LSTM(units[0], return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            
            # Second LSTM layer
            LSTM(units[1], return_sequences=True),
            Dropout(0.2),
            
            # Third LSTM layer
            LSTM(units[2], return_sequences=False),
            Dropout(0.2),
            
            # Dense layers
            Dense(32, activation='relu'),
            Dropout(0.1),
            Dense(16, activation='relu'),
            Dense(1)
        ])
        
        # Compile with appropriate optimizer and loss
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def train_ensemble_models(self, df: pd.DataFrame, target_col: str = 'water_height_a'):
        """
        Train multiple models for ensemble prediction
        """
        # Prepare data for traditional ML models
        feature_cols = [col for col in df.columns if col not in ['created_at', 'water_post_code']]
        X = df[feature_cols].drop(columns=[target_col])
        y = df[target_col]
        
        # Remove rows with NaN
        mask = ~(X.isnull().any(axis=1) | y.isnull())
        X = X[mask]
        y = y[mask]
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train Random Forest
        rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_scaled, y)
        self.models['random_forest'] = rf_model
        self.feature_importance['random_forest'] = dict(zip(X.columns, rf_model.feature_importances_))
        
        # Train Gradient Boosting
        gb_model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        gb_model.fit(X_scaled, y)
        self.models['gradient_boosting'] = gb_model
        self.feature_importance['gradient_boosting'] = dict(zip(X.columns, gb_model.feature_importances_))
        
        # Train LSTM
        X_train, X_test, y_train, y_test, feature_cols = self.prepare_sequences(df, target_col)
        
        lstm_model = self.build_enhanced_lstm((X_train.shape[1], X_train.shape[2]))
        
        # Callbacks for better training
        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True),
            ReduceLROnPlateau(factor=0.5, patience=5),
            ModelCheckpoint(f"{self.model_path}best_lstm_{target_col}.h5", 
                          save_best_only=True)
        ]
        
        # Train LSTM
        history = lstm_model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=100,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        self.models['lstm'] = lstm_model
        
        return history
    
    def predict_ensemble(self, df: pd.DataFrame, target_col: str = 'water_height_a') -> Dict:
        """
        Make ensemble predictions using multiple models
        """
        predictions = {}
        
        # Prepare data for traditional ML models
        feature_cols = [col for col in df.columns if col not in ['created_at', 'water_post_code']]
        X = df[feature_cols].drop(columns=[target_col])
        
        # Remove rows with NaN
        mask = ~X.isnull().any(axis=1)
        X = X[mask]
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Random Forest prediction
        if 'random_forest' in self.models:
            rf_pred = self.models['random_forest'].predict(X_scaled)
            predictions['random_forest'] = rf_pred
        
        # Gradient Boosting prediction
        if 'gradient_boosting' in self.models:
            gb_pred = self.models['gradient_boosting'].predict(X_scaled)
            predictions['gradient_boosting'] = gb_pred
        
        # LSTM prediction
        if 'lstm' in self.models:
            X_train, X_test, y_train, y_test, feature_cols = self.prepare_sequences(df, target_col)
            lstm_pred = self.models['lstm'].predict(X_test)
            # Inverse transform LSTM predictions
            lstm_pred_original = self.scalers[target_col].inverse_transform(
                np.zeros((len(lstm_pred), len(feature_cols)))
            )
            lstm_pred_original[:, feature_cols.index(target_col)] = lstm_pred.flatten()
            predictions['lstm'] = lstm_pred_original[:, feature_cols.index(target_col)]
        
        # Ensemble prediction (weighted average)
        if len(predictions) > 1:
            weights = {'random_forest': 0.3, 'gradient_boosting': 0.3, 'lstm': 0.4}
            ensemble_pred = np.zeros(len(list(predictions.values())[0]))
            
            for model_name, pred in predictions.items():
                if model_name in weights:
                    ensemble_pred += weights[model_name] * pred
            
            predictions['ensemble'] = ensemble_pred
        
        return predictions
    
    def calculate_flood_risk(self, water_level: float, river_data: Dict) -> Dict:
        """
        Enhanced flood risk calculation with multiple factors
        """
        safe_height = river_data.get('river_safe_height', 0)
        warning_height = river_data.get('river_warning_height', 0)
        danger_height = river_data.get('river_danger_height', 0)
        
        # Calculate risk percentage
        if water_level <= safe_height:
            risk_percentage = 0
            risk_level = 'SAFE'
        elif water_level <= warning_height:
            risk_percentage = ((water_level - safe_height) / (warning_height - safe_height)) * 50
            risk_level = 'CAUTION'
        elif water_level <= danger_height:
            risk_percentage = 50 + ((water_level - warning_height) / (danger_height - warning_height)) * 40
            risk_level = 'WARNING'
        else:
            risk_percentage = 90 + min(((water_level - danger_height) / danger_height) * 10, 10)
            risk_level = 'DANGER'
        
        return {
            'risk_level': risk_level,
            'risk_percentage': round(risk_percentage, 2),
            'water_level': water_level,
            'safe_threshold': safe_height,
            'warning_threshold': warning_height,
            'danger_threshold': danger_height
        }
    
    def evaluate_models(self, df: pd.DataFrame, target_col: str = 'water_height_a') -> Dict:
        """
        Evaluate model performance with multiple metrics
        """
        predictions = self.predict_ensemble(df, target_col)
        actual = df[target_col].dropna()
        
        results = {}
        
        for model_name, pred in predictions.items():
            if len(pred) == len(actual):
                mse = mean_squared_error(actual, pred)
                mae = mean_absolute_error(actual, pred)
                r2 = r2_score(actual, pred)
                rmse = np.sqrt(mse)
                
                results[model_name] = {
                    'MSE': round(mse, 4),
                    'MAE': round(mae, 4),
                    'RMSE': round(rmse, 4),
                    'R2': round(r2, 4)
                }
        
        return results
    
    def save_models(self):
        """
        Save trained models for future use
        """
        import joblib
        
        # Save traditional ML models
        for model_name, model in self.models.items():
            if model_name != 'lstm':
                joblib.dump(model, f"{self.model_path}{model_name}.pkl")
        
        # Save LSTM model
        if 'lstm' in self.models:
            self.models['lstm'].save(f"{self.model_path}lstm_model.h5")
        
        # Save scalers
        joblib.dump(self.scalers, f"{self.model_path}scalers.pkl")
        
        # Save feature importance
        joblib.dump(self.feature_importance, f"{self.model_path}feature_importance.pkl")
    
    def load_models(self):
        """
        Load previously trained models
        """
        import joblib
        
        try:
            # Load traditional ML models
            for model_name in ['random_forest', 'gradient_boosting']:
                model_path = f"{self.model_path}{model_name}.pkl"
                if os.path.exists(model_path):
                    self.models[model_name] = joblib.load(model_path)
            
            # Load LSTM model
            lstm_path = f"{self.model_path}lstm_model.h5"
            if os.path.exists(lstm_path):
                self.models['lstm'] = load_model(lstm_path)
            
            # Load scalers and feature importance
            if os.path.exists(f"{self.model_path}scalers.pkl"):
                self.scalers = joblib.load(f"{self.model_path}scalers.pkl")
            
            if os.path.exists(f"{self.model_path}feature_importance.pkl"):
                self.feature_importance = joblib.load(f"{self.model_path}feature_importance.pkl")
                
        except Exception as e:
            print(f"Error loading models: {e}")

# Example usage
if __name__ == "__main__":
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '',
        'database': 'floodeck_alpha'
    }
    
    # Initialize forecaster
    forecaster = EnhancedFloodForecaster(db_config)
    
    # Load and preprocess data
    df = forecaster.load_and_preprocess_data('BRNTS1', days_back=60)
    
    if not df.empty:
        # Train models
        history = forecaster.train_ensemble_models(df)
        
        # Evaluate models
        results = forecaster.evaluate_models(df)
        print("Model Performance:")
        for model, metrics in results.items():
            print(f"\n{model}:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value}")
        
        # Save models
        forecaster.save_models()
        
        # Make predictions
        predictions = forecaster.predict_ensemble(df)
        print(f"\nEnsemble prediction: {predictions.get('ensemble', [])[-1]:.2f}") 
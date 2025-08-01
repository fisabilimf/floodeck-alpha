# Floodeck Alpha - Implementation Guide for Optimized Forecasting

## 🚀 **Quick Start Guide**

### **1. Install Enhanced Dependencies**

```bash
# Install optimized forecasting dependencies
pip install -r requirements_forecasting.txt

# Or install specific packages
pip install tensorflow scikit-learn pandas numpy statsmodels
pip install matplotlib seaborn plotly
pip install joblib sqlalchemy pymysql
```

### **2. Setup Database Connection**

Pastikan database MySQL sudah berjalan dan konfigurasi sudah benar di `config.py`:

```python
# config.py
class Config:
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'your_password'
    MYSQL_DB = 'floodeck_alpha'
```

### **3. Initialize Enhanced Forecasting**

```python
from services import ForecastingService
from database import get_db_session

# Initialize with database session
with get_db_session() as session:
    forecasting_service = ForecastingService(session)
    
    # Get enhanced predictions
    prediction = forecasting_service.get_enhanced_prediction('BRNTS1', hours_ahead=6)
    print(prediction)
```

## 📊 **Detailed Implementation Steps**

### **Step 1: Data Preparation**

#### **Current Implementation Issues:**
- Minimal data cleaning
- No outlier detection
- Limited feature engineering
- No data validation

#### **Optimized Solution:**

```python
# Enhanced data loading and preprocessing
def load_and_preprocess_data(self, post_code: str, days_back: int = 30):
    # Load comprehensive data with joins
    query = f"""
    SELECT 
        sa.sensor_a_scan_water_height as water_height_a,
        sa.sensor_a_temperature as temperature,
        sa.sensor_a_humidity as humidity,
        sa.sensor_a_raindrop as rainfall,
        sb.sensor_b_scan_water_height as water_height_b,
        sa.created_at,
        rd.river_width, rd.river_depth, rd.river_slope,
        rd.river_flow_velocity, rd.river_roughness
    FROM sensor_a sa
    LEFT JOIN sensor_b sb ON sa.water_post_code = sb.water_post_code 
        AND DATE(sa.created_at) = DATE(sb.created_at)
    LEFT JOIN river_data rd ON sa.water_post_code = rd.river_code
    WHERE sa.water_post_code = '{post_code}'
    AND sa.created_at >= DATE_SUB(NOW(), INTERVAL {days_back} DAY)
    ORDER BY sa.created_at
    """
    
    df = pd.read_sql(query, self.engine)
    
    # Enhanced data cleaning
    df = self._clean_data(df)
    
    # Advanced feature engineering
    df = self._engineer_features(df)
    
    return df
```

### **Step 2: Feature Engineering**

#### **Time-based Features:**
```python
def _engineer_features(self, df):
    # Time features
    df['hour'] = df['created_at'].dt.hour
    df['day_of_week'] = df['created_at'].dt.dayofweek
    df['month'] = df['created_at'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Lag features
    for lag in [1, 2, 3, 6, 12, 24]:
        df[f'water_height_a_lag_{lag}'] = df['water_height_a'].shift(lag)
        df[f'rainfall_lag_{lag}'] = df['rainfall'].shift(lag)
    
    # Rolling statistics
    for window in [3, 6, 12, 24]:
        df[f'water_height_a_rolling_mean_{window}'] = df['water_height_a'].rolling(window=window).mean()
        df[f'water_height_a_rolling_std_{window}'] = df['water_height_a'].rolling(window=window).std()
    
    # Rate of change
    df['water_height_a_change'] = df['water_height_a'].diff()
    df['rainfall_change'] = df['rainfall'].diff()
    
    # Interaction features
    df['temp_humidity_interaction'] = df['temperature'] * df['humidity']
    df['rainfall_intensity'] = df['rainfall'] * df['humidity']
    
    return df
```

### **Step 3: Enhanced LSTM Model**

#### **Current vs Optimized:**

**Current Implementation:**
```python
# Simple LSTM (current)
model = Sequential([
    LSTM(100, activation='relu', input_shape=(n_input, 1)),
    Dense(1)
])
```

**Optimized Implementation:**
```python
# Enhanced LSTM with regularization
def build_enhanced_lstm(self, input_shape, units=[128, 64, 32]):
    model = Sequential([
        LSTM(units[0], return_sequences=True, input_shape=input_shape),
        Dropout(0.2),  # Prevent overfitting
        LSTM(units[1], return_sequences=True),
        Dropout(0.2),
        LSTM(units[2], return_sequences=False),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dropout(0.1),
        Dense(16, activation='relu'),
        Dense(1)
    ])
    
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )
    
    return model
```

### **Step 4: Ensemble Methods**

```python
def train_ensemble_models(self, df, target_col='water_height_a'):
    # Train Random Forest
    rf_model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_scaled, y)
    
    # Train Gradient Boosting
    gb_model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42
    )
    gb_model.fit(X_scaled, y)
    
    # Train LSTM with callbacks
    callbacks = [
        EarlyStopping(patience=10, restore_best_weights=True),
        ReduceLROnPlateau(factor=0.5, patience=5),
        ModelCheckpoint('best_lstm_model.h5', save_best_only=True)
    ]
    
    lstm_model.fit(X_train, y_train,
                  validation_data=(X_test, y_test),
                  epochs=100,
                  batch_size=32,
                  callbacks=callbacks)
```

### **Step 5: Model Evaluation**

```python
def evaluate_models(self, df, target_col='water_height_a'):
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
```

## 🔧 **Integration with Existing System**

### **1. Update Services**

Tambahkan `ForecastingService` ke `services.py`:

```python
# services.py
class ForecastingService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.forecaster = None
        self._initialize_forecaster()
    
    def get_enhanced_prediction(self, post_code: str, hours_ahead: int = 6):
        # Implementation as shown above
        pass
```

### **2. Update Routes**

Tambahkan endpoint baru di `routes.py`:

```python
# routes.py
@api_bp.route('/enhanced-forecast/<post_code>')
@handle_exceptions
@monitor_performance('enhanced_forecast')
def enhanced_forecast(post_code):
    hours_ahead = request.args.get('hours', 6, type=int)
    
    with get_db_session() as session:
        forecasting_service = ForecastingService(session)
        prediction = forecasting_service.get_enhanced_prediction(post_code, hours_ahead)
        
        return jsonify(prediction)
```

### **3. Update Frontend**

Tambahkan visualisasi untuk enhanced predictions:

```javascript
// static/js/forecasting.js
function loadEnhancedForecast(postCode) {
    fetch(`/api/enhanced-forecast/${postCode}?hours=6`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Forecast error:', data.error);
                return;
            }
            
            // Update UI with enhanced predictions
            updateForecastChart(data.predictions.ensemble);
            updateRiskAssessment(data.risk_assessment);
            updateModelPerformance(data.model_performance);
            updateConfidenceScore(data.confidence_score);
        });
}
```

## 📈 **Performance Monitoring**

### **1. Model Performance Tracking**

```python
def track_model_performance(self, post_code: str):
    """Track model performance over time"""
    performance_history = []
    
    # Get historical predictions vs actual
    query = f"""
    SELECT 
        f.prediction_water_elevation,
        w.water_elevation as actual_elevation,
        f.created_at
    FROM forecasting f
    JOIN water_data w ON DATE(f.created_at) = DATE(w.created_at)
    WHERE f.river_code = '{post_code}'
    ORDER BY f.created_at DESC
    LIMIT 100
    """
    
    df = pd.read_sql(query, self.engine)
    
    if not df.empty:
        mse = mean_squared_error(df['actual_elevation'], df['prediction_water_elevation'])
        mae = mean_absolute_error(df['actual_elevation'], df['prediction_water_elevation'])
        
        performance_history.append({
            'date': datetime.now(),
            'mse': mse,
            'mae': mae,
            'post_code': post_code
        })
    
    return performance_history
```

### **2. Automated Retraining**

```python
def auto_retrain_check(self, post_code: str):
    """Check if models need retraining"""
    # Get recent performance
    recent_performance = self.track_model_performance(post_code)
    
    if recent_performance:
        latest_mse = recent_performance[-1]['mse']
        
        # If performance degrades, retrain
        if latest_mse > self.performance_threshold:
            logger.info(f"Performance degraded for {post_code}, initiating retraining")
            return self.retrain_models(post_code)
    
    return {'status': 'no_retraining_needed'}
```

## 🧪 **Testing and Validation**

### **1. Run Performance Benchmark**

```bash
# Run comprehensive benchmark
python test_forecasting_performance.py
```

### **2. Validate Predictions**

```python
def validate_predictions(self, post_code: str, days_back: int = 7):
    """Validate predictions against actual data"""
    # Get predictions from last week
    predictions = self.get_enhanced_prediction(post_code, hours_ahead=24*7)
    
    # Get actual data
    actual_data = self.get_actual_data(post_code, days_back)
    
    # Calculate accuracy metrics
    accuracy_metrics = self.calculate_accuracy(predictions, actual_data)
    
    return accuracy_metrics
```

## 🚨 **Error Handling and Logging**

### **1. Comprehensive Error Handling**

```python
def get_enhanced_prediction(self, post_code: str, hours_ahead: int = 6):
    try:
        if not self.forecaster:
            logger.error("Forecaster not initialized")
            return {'error': 'Forecaster not initialized'}
        
        # Load data
        df = self.forecaster.load_and_preprocess_data(post_code, days_back=30)
        
        if df.empty:
            logger.warning(f"No data available for {post_code}")
            return {'error': 'No data available for prediction'}
        
        # Make predictions
        predictions = self.forecaster.predict_ensemble(df)
        
        # Calculate risk
        risk_assessment = self.calculate_risk_assessment(predictions, post_code)
        
        return {
            'predictions': predictions,
            'risk_assessment': risk_assessment,
            'confidence_score': self.calculate_confidence(predictions),
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced prediction: {e}")
        return {'error': str(e)}
```

### **2. Performance Monitoring**

```python
@monitor_performance('enhanced_forecast')
def enhanced_forecast_endpoint(post_code):
    # Implementation with performance monitoring
    pass
```

## 📊 **Deployment Checklist**

### **Pre-deployment:**
- [ ] Install all required dependencies
- [ ] Test database connections
- [ ] Validate data quality
- [ ] Run performance benchmarks
- [ ] Test error handling

### **Deployment:**
- [ ] Deploy optimized forecasting module
- [ ] Update services and routes
- [ ] Configure monitoring and logging
- [ ] Set up automated retraining
- [ ] Test in staging environment

### **Post-deployment:**
- [ ] Monitor model performance
- [ ] Track prediction accuracy
- [ ] Monitor system resources
- [ ] Collect user feedback
- [ ] Plan future improvements

## 🔄 **Maintenance Schedule**

### **Daily:**
- Monitor model performance metrics
- Check data quality and availability
- Review error logs

### **Weekly:**
- Retrain models with new data
- Analyze feature importance changes
- Update performance reports

### **Monthly:**
- Comprehensive model evaluation
- Update model architecture if needed
- Review and update thresholds

### **Quarterly:**
- Major system updates
- Performance optimization
- Feature engineering improvements

## 📞 **Support and Troubleshooting**

### **Common Issues:**

1. **Model Training Fails:**
   - Check data availability
   - Verify database connections
   - Review error logs

2. **Poor Prediction Accuracy:**
   - Retrain models with more data
   - Check feature engineering
   - Validate data quality

3. **Performance Issues:**
   - Monitor system resources
   - Check caching configuration
   - Optimize database queries

### **Getting Help:**
- Check logs in `floodeck.log`
- Review performance metrics
- Contact development team
- Create issue in repository

## 🎯 **Success Metrics**

### **Technical Metrics:**
- Prediction accuracy improvement: 15-25%
- Execution time reduction: 20-40%
- Feature count increase: 50+ features
- Model confidence score: >80%

### **Business Metrics:**
- False alarm reduction: 30-50%
- Early warning time: 2-4 hours
- System reliability: >99%
- User satisfaction: >90%

---

**Note:** This implementation guide provides a comprehensive approach to optimizing the forecasting system. Follow the steps carefully and test thoroughly before deploying to production. 
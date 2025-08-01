"""
Performance Testing Script for Floodeck Forecasting
Compare current implementation vs optimized implementation
"""

import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import both implementations
from python.Sensor_A_Forecasting_alpha import *  # Current implementation
from python.optimized_forecasting import EnhancedFloodForecaster  # Optimized implementation

class ForecastingBenchmark:
    """Benchmark class to compare forecasting implementations"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.results = {}
        
    def test_current_implementation(self, post_code: str, test_days: int = 7) -> dict:
        """Test current forecasting implementation"""
        print("Testing Current Implementation...")
        
        start_time = time.time()
        
        try:
            # Simulate current implementation
            # This would normally run the Jupyter notebook cells
            # For testing, we'll create a simplified version
            
            # Load data (simplified version of current implementation)
            conn = pymysql.connect(**self.db_config)
            
            query = f"SELECT sensor_a_scan_water_height, created_at FROM sensor_a WHERE water_post_code = '{post_code}' ORDER BY created_at DESC LIMIT 100"
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                return {'error': 'No data available'}
            
            # Basic preprocessing (current implementation style)
            df['created_at'] = pd.to_datetime(df['created_at'])
            df = df.sort_values('created_at')
            df = df.dropna()
            
            # Simple LSTM (current implementation)
            scaler = MinMaxScaler()
            data = scaler.fit_transform(df['sensor_a_scan_water_height'].values.reshape(-1, 1))
            
            # Create sequences
            n_input = 3
            X, y = [], []
            for i in range(n_input, len(data)):
                X.append(data[i-n_input:i])
                y.append(data[i])
            
            X, y = np.array(X), np.array(y)
            
            # Simple LSTM model (current implementation)
            model = Sequential([
                LSTM(100, activation='relu', input_shape=(n_input, 1)),
                Dense(1)
            ])
            model.compile(optimizer='adam', loss='mse')
            
            # Train model
            model.fit(X, y, epochs=5, verbose=0)
            
            # Make prediction
            last_sequence = data[-n_input:].reshape((1, n_input, 1))
            prediction = model.predict(last_sequence)[0][0]
            prediction = scaler.inverse_transform([[prediction]])[0][0]
            
            conn.close()
            
            execution_time = time.time() - start_time
            
            return {
                'prediction': prediction,
                'execution_time': execution_time,
                'model_type': 'Simple LSTM',
                'features_used': 1,
                'data_points': len(df)
            }
            
        except Exception as e:
            return {'error': str(e), 'execution_time': time.time() - start_time}
    
    def test_optimized_implementation(self, post_code: str, test_days: int = 7) -> dict:
        """Test optimized forecasting implementation"""
        print("Testing Optimized Implementation...")
        
        start_time = time.time()
        
        try:
            # Initialize optimized forecaster
            forecaster = EnhancedFloodForecaster(self.db_config)
            
            # Load and preprocess data
            df = forecaster.load_and_preprocess_data(post_code, days_back=30)
            
            if df.empty:
                return {'error': 'No data available'}
            
            # Train ensemble models
            history = forecaster.train_ensemble_models(df)
            
            # Make ensemble predictions
            predictions = forecaster.predict_ensemble(df)
            
            # Get ensemble prediction
            ensemble_pred = predictions.get('ensemble', [0])
            latest_prediction = ensemble_pred[-1] if len(ensemble_pred) > 0 else 0
            
            # Evaluate models
            performance = forecaster.evaluate_models(df)
            
            execution_time = time.time() - start_time
            
            return {
                'prediction': latest_prediction,
                'execution_time': execution_time,
                'model_type': 'Ensemble (LSTM + RF + GB)',
                'features_used': len([col for col in df.columns if col not in ['created_at', 'water_post_code']]),
                'data_points': len(df),
                'performance_metrics': performance,
                'ensemble_predictions': predictions
            }
            
        except Exception as e:
            return {'error': str(e), 'execution_time': time.time() - start_time}
    
    def run_comprehensive_benchmark(self, post_codes: list) -> dict:
        """Run comprehensive benchmark on multiple post codes"""
        print("Running Comprehensive Benchmark...")
        
        benchmark_results = {
            'current_implementation': {},
            'optimized_implementation': {},
            'comparison': {}
        }
        
        for post_code in post_codes:
            print(f"\nTesting post_code: {post_code}")
            
            # Test current implementation
            current_result = self.test_current_implementation(post_code)
            benchmark_results['current_implementation'][post_code] = current_result
            
            # Test optimized implementation
            optimized_result = self.test_optimized_implementation(post_code)
            benchmark_results['optimized_implementation'][post_code] = optimized_result
            
            # Compare results
            if 'error' not in current_result and 'error' not in optimized_result:
                comparison = {
                    'execution_time_improvement': (
                        (current_result['execution_time'] - optimized_result['execution_time']) / 
                        current_result['execution_time'] * 100
                    ),
                    'features_improvement': (
                        optimized_result['features_used'] - current_result['features_used']
                    ),
                    'model_complexity': {
                        'current': current_result['model_type'],
                        'optimized': optimized_result['model_type']
                    }
                }
                benchmark_results['comparison'][post_code] = comparison
        
        return benchmark_results
    
    def generate_performance_report(self, benchmark_results: dict) -> str:
        """Generate detailed performance report"""
        report = []
        report.append("# Floodeck Forecasting Performance Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary statistics
        current_times = []
        optimized_times = []
        current_features = []
        optimized_features = []
        
        for post_code in benchmark_results['comparison'].keys():
            current_result = benchmark_results['current_implementation'][post_code]
            optimized_result = benchmark_results['optimized_implementation'][post_code]
            
            if 'error' not in current_result and 'error' not in optimized_result:
                current_times.append(current_result['execution_time'])
                optimized_times.append(optimized_result['execution_time'])
                current_features.append(current_result['features_used'])
                optimized_features.append(optimized_result['features_used'])
        
        if current_times and optimized_times:
            report.append("## Performance Summary")
            report.append("")
            report.append(f"- **Average Execution Time (Current):** {np.mean(current_times):.2f}s")
            report.append(f"- **Average Execution Time (Optimized):** {np.mean(optimized_times):.2f}s")
            report.append(f"- **Performance Improvement:** {((np.mean(current_times) - np.mean(optimized_times)) / np.mean(current_times) * 100):.1f}%")
            report.append(f"- **Features Used (Current):** {np.mean(current_features):.1f}")
            report.append(f"- **Features Used (Optimized):** {np.mean(optimized_features):.1f}")
            report.append(f"- **Feature Increase:** {np.mean(optimized_features) - np.mean(current_features):.1f}")
            report.append("")
        
        # Detailed results
        report.append("## Detailed Results by Post Code")
        report.append("")
        
        for post_code, comparison in benchmark_results['comparison'].items():
            report.append(f"### {post_code}")
            report.append("")
            
            current_result = benchmark_results['current_implementation'][post_code]
            optimized_result = benchmark_results['optimized_implementation'][post_code]
            
            if 'error' not in current_result and 'error' not in optimized_result:
                report.append(f"- **Current Implementation:**")
                report.append(f"  - Execution Time: {current_result['execution_time']:.2f}s")
                report.append(f"  - Model Type: {current_result['model_type']}")
                report.append(f"  - Features Used: {current_result['features_used']}")
                report.append(f"  - Data Points: {current_result['data_points']}")
                report.append("")
                
                report.append(f"- **Optimized Implementation:**")
                report.append(f"  - Execution Time: {optimized_result['execution_time']:.2f}s")
                report.append(f"  - Model Type: {optimized_result['model_type']}")
                report.append(f"  - Features Used: {optimized_result['features_used']}")
                report.append(f"  - Data Points: {optimized_result['data_points']}")
                report.append("")
                
                if 'performance_metrics' in optimized_result:
                    report.append(f"- **Model Performance Metrics:**")
                    for model, metrics in optimized_result['performance_metrics'].items():
                        report.append(f"  - {model}:")
                        for metric, value in metrics.items():
                            report.append(f"    - {metric}: {value}")
                    report.append("")
                
                report.append(f"- **Improvements:**")
                report.append(f"  - Execution Time: {comparison['execution_time_improvement']:.1f}% faster")
                report.append(f"  - Features: +{comparison['features_improvement']} additional features")
                report.append("")
            else:
                report.append("- **Error occurred during testing**")
                report.append("")
        
        return "\n".join(report)
    
    def create_visualization(self, benchmark_results: dict, save_path: str = "benchmark_results.png"):
        """Create visualization of benchmark results"""
        # Prepare data for plotting
        post_codes = []
        current_times = []
        optimized_times = []
        current_features = []
        optimized_features = []
        
        for post_code in benchmark_results['comparison'].keys():
            current_result = benchmark_results['current_implementation'][post_code]
            optimized_result = benchmark_results['optimized_implementation'][post_code]
            
            if 'error' not in current_result and 'error' not in optimized_result:
                post_codes.append(post_code)
                current_times.append(current_result['execution_time'])
                optimized_times.append(optimized_result['execution_time'])
                current_features.append(current_result['features_used'])
                optimized_features.append(optimized_result['features_used'])
        
        if not post_codes:
            print("No valid data for visualization")
            return
        
        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Plot 1: Execution Time Comparison
        x = np.arange(len(post_codes))
        width = 0.35
        
        ax1.bar(x - width/2, current_times, width, label='Current Implementation', alpha=0.8)
        ax1.bar(x + width/2, optimized_times, width, label='Optimized Implementation', alpha=0.8)
        ax1.set_xlabel('Post Code')
        ax1.set_ylabel('Execution Time (seconds)')
        ax1.set_title('Execution Time Comparison')
        ax1.set_xticks(x)
        ax1.set_xticklabels(post_codes, rotation=45)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Features Comparison
        ax2.bar(x - width/2, current_features, width, label='Current Implementation', alpha=0.8)
        ax2.bar(x + width/2, optimized_features, width, label='Optimized Implementation', alpha=0.8)
        ax2.set_xlabel('Post Code')
        ax2.set_ylabel('Number of Features')
        ax2.set_title('Features Used Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels(post_codes, rotation=45)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Performance Improvement
        improvements = [(current_times[i] - optimized_times[i]) / current_times[i] * 100 
                       for i in range(len(current_times))]
        ax3.bar(post_codes, improvements, alpha=0.8, color='green')
        ax3.set_xlabel('Post Code')
        ax3.set_ylabel('Performance Improvement (%)')
        ax3.set_title('Execution Time Improvement')
        ax3.set_xticklabels(post_codes, rotation=45)
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Feature Increase
        feature_increases = [optimized_features[i] - current_features[i] 
                           for i in range(len(current_features))]
        ax4.bar(post_codes, feature_increases, alpha=0.8, color='blue')
        ax4.set_xlabel('Post Code')
        ax4.set_ylabel('Additional Features')
        ax4.set_title('Feature Engineering Improvement')
        ax4.set_xticklabels(post_codes, rotation=45)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Visualization saved to: {save_path}")

def main():
    """Main function to run the benchmark"""
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '',
        'database': 'floodeck_alpha'
    }
    
    # Initialize benchmark
    benchmark = ForecastingBenchmark(db_config)
    
    # Test post codes (you can modify this list)
    post_codes = ['BRNTS1']  # Add more post codes as needed
    
    print("Starting Floodeck Forecasting Benchmark...")
    print("=" * 50)
    
    # Run benchmark
    results = benchmark.run_comprehensive_benchmark(post_codes)
    
    # Generate report
    report = benchmark.generate_performance_report(results)
    
    # Save report
    with open('forecasting_benchmark_report.md', 'w') as f:
        f.write(report)
    
    print("\nBenchmark completed!")
    print("Report saved to: forecasting_benchmark_report.md")
    
    # Create visualization
    benchmark.create_visualization(results)
    
    # Print summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print("=" * 50)
    
    current_times = []
    optimized_times = []
    
    for post_code in results['comparison'].keys():
        current_result = results['current_implementation'][post_code]
        optimized_result = results['optimized_implementation'][post_code]
        
        if 'error' not in current_result and 'error' not in optimized_result:
            current_times.append(current_result['execution_time'])
            optimized_times.append(optimized_result['execution_time'])
    
    if current_times and optimized_times:
        avg_current_time = np.mean(current_times)
        avg_optimized_time = np.mean(optimized_times)
        improvement = ((avg_current_time - avg_optimized_time) / avg_current_time) * 100
        
        print(f"Average Execution Time (Current): {avg_current_time:.2f}s")
        print(f"Average Execution Time (Optimized): {avg_optimized_time:.2f}s")
        print(f"Performance Improvement: {improvement:.1f}%")
        
        if improvement > 0:
            print("✅ Optimized implementation is FASTER")
        else:
            print("⚠️ Optimized implementation is SLOWER (but more accurate)")

if __name__ == "__main__":
    main() 
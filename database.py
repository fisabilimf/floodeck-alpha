import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from typing import Generator
import time

from config import Config

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection manager with connection pooling"""
    
    def __init__(self, config: Config):
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._setup_engine()
    
    def _setup_engine(self):
        """Setup SQLAlchemy engine with connection pooling"""
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                self.config.SQLALCHEMY_DATABASE_URI,
                poolclass=QueuePool,
                pool_size=self.config.SQLALCHEMY_ENGINE_OPTIONS.get('pool_size', 10),
                max_overflow=20,
                pool_recycle=self.config.SQLALCHEMY_ENGINE_OPTIONS.get('pool_recycle', 3600),
                pool_pre_ping=self.config.SQLALCHEMY_ENGINE_OPTIONS.get('pool_pre_ping', True),
                echo=self.config.DEBUG,  # Log SQL queries in debug mode
                connect_args={
                    'charset': 'utf8mb4',
                    'autocommit': False
                }
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Setup connection event listeners
            self._setup_event_listeners()
            
            logger.info("Database engine setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup database engine: {e}")
            raise
    
    def _setup_event_listeners(self):
        """Setup database event listeners for monitoring"""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance"""
            if hasattr(dbapi_connection, 'execute'):
                dbapi_connection.execute("PRAGMA journal_mode=WAL")
                dbapi_connection.execute("PRAGMA synchronous=NORMAL")
                dbapi_connection.execute("PRAGMA cache_size=10000")
                dbapi_connection.execute("PRAGMA temp_store=MEMORY")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout"""
            if self.config.DEBUG:
                logger.debug("Database connection checked out")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin"""
            if self.config.DEBUG:
                logger.debug("Database connection checked in")
    
    @contextmanager
    def get_session(self) -> Generator:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
                logger.info("Database connection test successful")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """Get database connection information"""
        try:
            with self.get_session() as session:
                # Get MySQL version
                result = session.execute("SELECT VERSION()")
                version = result.scalar()
                
                # Get connection pool info
                pool_info = {
                    'pool_size': self.engine.pool.size(),
                    'checked_in': self.engine.pool.checkedin(),
                    'checked_out': self.engine.pool.checkedout(),
                    'overflow': self.engine.pool.overflow(),
                    'invalid': self.engine.pool.invalid()
                }
                
                return {
                    'version': version,
                    'pool_info': pool_info,
                    'database_url': str(self.engine.url).replace(
                        self.config.MYSQL_PASSWORD, '***'
                    ) if self.config.MYSQL_PASSWORD else str(self.engine.url)
                }
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

class DatabaseHealthCheck:
    """Database health check utilities"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def check_health(self) -> dict:
        """Perform comprehensive database health check"""
        health_status = {
            'status': 'healthy',
            'checks': {},
            'timestamp': time.time()
        }
        
        # Test basic connection
        connection_check = self.db_manager.test_connection()
        health_status['checks']['connection'] = {
            'status': 'pass' if connection_check else 'fail',
            'message': 'Database connection successful' if connection_check else 'Database connection failed'
        }
        
        if not connection_check:
            health_status['status'] = 'unhealthy'
        
        # Test query performance
        try:
            with self.db_manager.get_session() as session:
                start_time = time.time()
                session.execute("SELECT COUNT(*) FROM sensor_a")
                query_time = time.time() - start_time
                
                health_status['checks']['query_performance'] = {
                    'status': 'pass' if query_time < 1.0 else 'warning',
                    'message': f'Query executed in {query_time:.3f}s',
                    'query_time': query_time
                }
                
                if query_time > 5.0:
                    health_status['status'] = 'degraded'
                    
        except Exception as e:
            health_status['checks']['query_performance'] = {
                'status': 'fail',
                'message': f'Query performance check failed: {e}'
            }
            health_status['status'] = 'unhealthy'
        
        # Check connection pool
        try:
            pool_info = self.db_manager.get_connection_info()
            if 'pool_info' in pool_info:
                pool = pool_info['pool_info']
                
                # Check if pool is exhausted
                if pool['checked_out'] >= pool['pool_size'] + pool['overflow']:
                    health_status['checks']['connection_pool'] = {
                        'status': 'warning',
                        'message': 'Connection pool is exhausted'
                    }
                    if health_status['status'] == 'healthy':
                        health_status['status'] = 'degraded'
                else:
                    health_status['checks']['connection_pool'] = {
                        'status': 'pass',
                        'message': f'Pool: {pool["checked_out"]}/{pool["pool_size"]} connections in use'
                    }
            else:
                health_status['checks']['connection_pool'] = {
                    'status': 'fail',
                    'message': 'Unable to get pool information'
                }
                health_status['status'] = 'unhealthy'
                
        except Exception as e:
            health_status['checks']['connection_pool'] = {
                'status': 'fail',
                'message': f'Pool check failed: {e}'
            }
            health_status['status'] = 'unhealthy'
        
        return health_status

# Global database manager instance
db_manager = None
health_checker = None

def init_database(config: Config):
    """Initialize database manager"""
    global db_manager, health_checker
    
    try:
        db_manager = DatabaseManager(config)
        health_checker = DatabaseHealthCheck(db_manager)
        logger.info("Database manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database manager: {e}")
        raise

def get_db_session():
    """Get database session"""
    if not db_manager:
        raise RuntimeError("Database manager not initialized")
    return db_manager.get_session()

def get_health_check():
    """Get database health check"""
    if not health_checker:
        raise RuntimeError("Health checker not initialized")
    return health_checker.check_health() 
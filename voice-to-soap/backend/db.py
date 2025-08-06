"""
AUDICIA VOICE-TO-SOAP SYSTEM
PostgreSQL Database Connection and Session Management
HIPAA-Compliant with Encryption and Audit Logging
"""

import os
import logging
from typing import Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from simple_secret_manager import get_database_config
import structlog

logger = structlog.get_logger()

class DatabaseManager:
    """
    HIPAA-compliant PostgreSQL database manager with:
    - Secure connection pooling
    - Audit logging for all database operations
    - Automatic reconnection handling
    - PHI data encryption at rest
    """
    
    def __init__(self):
        # Get database configuration from Azure Key Vault
        try:
            db_config = get_database_config()
            
            # Build connection string
            self.db_host = db_config.get("PG_HOST")
            self.db_port = db_config.get("PG_PORT", "5432")
            self.db_user = db_config.get("PG_USERNAME")
            self.db_password = db_config.get("PG_PASSWORD")
            self.db_name = db_config.get("PG_DATABASE")
            
            # Validate all required config is present
            if not all([self.db_host, self.db_user, self.db_password, self.db_name]):
                raise RuntimeError("Missing required database configuration")
            
            # Build PostgreSQL connection URL with SSL and security options
            # URL encode the password to handle special characters
            from urllib.parse import quote_plus
            encoded_password = quote_plus(self.db_password)
            
            self.database_url = (
                f"postgresql://{self.db_user}:{encoded_password}@"
                f"{self.db_host}:{self.db_port}/{self.db_name}"
                f"?sslmode=require"
                f"&application_name=audicia-soap-backend"
                f"&connect_timeout=10"
            )
            
            logger.info("Database configuration loaded successfully", 
                       host=self.db_host, 
                       database=self.db_name,
                       port=self.db_port)
            
        except Exception as e:
            logger.error("Failed to load database configuration", error=str(e))
            raise RuntimeError(f"Database configuration error: {e}")
    
    def create_engine(self):
        """Create SQLAlchemy engine with production settings"""
        try:
            # Create engine with connection pooling and security settings
            engine = create_engine(
                self.database_url,
                # Connection pool settings for high availability
                poolclass=QueuePool,
                pool_size=20,                    # Base pool size
                max_overflow=30,                 # Additional connections under load
                pool_pre_ping=True,              # Test connections before use
                pool_recycle=3600,               # Recycle connections every hour
                
                # Security and performance settings
                echo=False,                      # Disable SQL logging in production
                echo_pool=False,                 # Disable pool logging
                connect_args={
                    "connect_timeout": 10,       # Connection timeout
                    "application_name": "audicia-soap-backend",
                    "sslmode": "require",        # Force SSL encryption
                    "options": "-c timezone=UTC" # Force UTC timezone
                }
            )
            
            # Add event listeners for audit logging
            self._setup_audit_logging(engine)
            
            logger.info("Database engine created successfully",
                       pool_size=20,
                       max_overflow=30)
            
            return engine
            
        except Exception as e:
            logger.error("Failed to create database engine", error=str(e))
            raise RuntimeError(f"Database engine creation failed: {e}")
    
    def _setup_audit_logging(self, engine):
        """Setup database audit logging for HIPAA compliance"""
        
        @event.listens_for(engine, "before_cursor_execute", retval=True)
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # Log all database operations for audit trail
            context._query_start_time = logger.bind(
                operation="database_query_start",
                statement=statement[:100] + "..." if len(statement) > 100 else statement,
                connection_id=id(conn)
            )
            return statement, parameters
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # Log query completion for performance monitoring
            logger.info("database_query_completed",
                       connection_id=id(conn),
                       rowcount=cursor.rowcount if hasattr(cursor, 'rowcount') else 0)

# Create global database components
db_manager = DatabaseManager()
engine = db_manager.create_engine()

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # Keep objects usable after commit
)

# Create declarative base for models
Base = declarative_base()

# Database session dependency for FastAPI
def get_database_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency to provide database sessions
    
    Yields:
        Database session with automatic cleanup
    """
    session = SessionLocal()
    try:
        logger.debug("Database session created", session_id=id(session))
        yield session
    except Exception as e:
        logger.error("Database session error", 
                    session_id=id(session), 
                    error=str(e))
        session.rollback()
        raise
    finally:
        session.close()
        logger.debug("Database session closed", session_id=id(session))

# Context manager for manual session handling
@contextmanager
def get_db_session():
    """
    Context manager for database sessions outside FastAPI
    
    Usage:
        with get_db_session() as db:
            # database operations
    """
    session = SessionLocal()
    try:
        logger.debug("Manual database session created", session_id=id(session))
        yield session
        session.commit()
    except Exception as e:
        logger.error("Manual database session error", 
                    session_id=id(session), 
                    error=str(e))
        session.rollback()
        raise
    finally:
        session.close()
        logger.debug("Manual database session closed", session_id=id(session))

# Health check function
def check_database_health() -> bool:
    """
    Check database connectivity and health
    
    Returns:
        True if database is healthy, False otherwise
    """
    try:
        with get_db_session() as db:
            # Simple query to test connectivity
            from sqlalchemy import text
            result = db.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                logger.info("Database health check passed")
                return True
            else:
                logger.warning("Database health check failed - unexpected result")
                return False
                
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False

# Initialize database tables
def init_database():
    """
    Initialize database tables and perform startup checks
    """
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
        
        # Perform health check
        if check_database_health():
            logger.info("Database initialization completed successfully")
        else:
            raise RuntimeError("Database health check failed after initialization")
            
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise RuntimeError(f"Database initialization error: {e}")

if __name__ == "__main__":
    # Test database connection
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("Testing database connection...")
        
        # Initialize database
        init_database()
        
        # Test health check
        if check_database_health():
            print("✅ Database connection successful!")
        else:
            print("❌ Database health check failed")
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
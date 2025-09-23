import os
import secrets
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from a .env file if it exists
load_dotenv()

def generate_secret_key():
    """Generate a secure random secret key if not provided."""
    return secrets.token_urlsafe(32)

def get_database_uri(default_uri):
    """Get database URI with support for different database types."""
    database_url = os.getenv("DATABASE_URI", default_uri)
    
    # Handle PostgreSQL with psycopg2 driver if needed
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return database_url

def get_int_env(var_name, default_value):
    """Safely get an integer environment variable."""
    try:
        return int(os.getenv(var_name, str(default_value)))
    except ValueError:
        return default_value

def get_bool_env(var_name, default_value):
    """Safely get a boolean environment variable."""
    value = os.getenv(var_name, str(default_value)).lower()
    return value in ('true', '1', 'yes', 'on')

class Config:
    """Base configuration class with all default settings."""
    
    # Environment
    MY_ENVIRONMENT = os.getenv("MY_ENVIRONMENT", "PRODUCTION")
    DEBUG = get_bool_env("DEBUG", False)
    TESTING = False
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", generate_secret_key())
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", generate_secret_key())
    
    # Database
    SQLALCHEMY_DATABASE_URI = get_database_uri(os.getenv("DATABASE_URI", "sqlite:///app.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # JWT Settings
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]
    JWT_ACCESS_COOKIE_NAME = os.getenv("JWT_ACCESS_COOKIE_NAME", "access_token_cookie")
    JWT_REFRESH_COOKIE_NAME = os.getenv("JWT_REFRESH_COOKIE_NAME", "refresh_token_cookie")
    JWT_COOKIE_SECURE = get_bool_env("JWT_COOKIE_SECURE", True)
    JWT_COOKIE_CSRF_PROTECT = get_bool_env("JWT_COOKIE_CSRF_PROTECT", True)
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    
    # Token Lifetimes
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=get_int_env("JWT_ACCESS_TOKEN_MINUTES", 60)
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        minutes=get_int_env("JWT_REFRESH_TOKEN_MINUTES", 43200)  # 30 days
    )
    REFRESH_TOKEN_EXPIRES_MINUTES = get_int_env("REFRESH_TOKEN_EXPIRES_MINUTES", 43200)
    
    # Superadmin Bootstrap
    SUPERADMIN_USERNAME = os.getenv('SUPERADMIN_USERNAME', 'superadmin')
    SUPERADMIN_EMAIL = os.getenv('SUPERADMIN_EMAIL', 'superadmin@example.com')
    SUPERADMIN_EMPLOYEE_ID = os.getenv('SUPERADMIN_EMPLOYEE_ID', 'SUPER001')
    SUPERADMIN_MOBILE = os.getenv('SUPERADMIN_MOBILE', '9000000000')
    SUPERADMIN_PASSWORD = os.getenv('SUPERADMIN_PASSWORD')  # No default for security
    
    # Default Admin User (for development/testing)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_EMPLOYEE_ID = os.getenv("ADMIN_EMPLOYEE_ID", "ADMIN001")
    ADMIN_MOBILE = os.getenv("ADMIN_MOBILE", "9000000001")
    
    # Default User (for development/testing)
    USER_USERNAME = os.getenv("USER_USERNAME", "user")
    USER_EMAIL = os.getenv("USER_EMAIL", "user@example.com")
    USER_PASSWORD = os.getenv("USER_PASSWORD", "user123")
    USER_EMPLOYEE_ID = os.getenv("USER_EMPLOYEE_ID", "USER001")
    USER_MOBILE = os.getenv("USER_MOBILE", "9000000002")
    
    # Verifier User (for development/testing)
    VERIFIER_USERNAME = os.getenv("VERIFIER_USERNAME", "verifier")
    VERIFIER_EMAIL = os.getenv("VERIFIER_EMAIL", "verifier@example.com")
    VERIFIER_PASSWORD = os.getenv("VERIFIER_PASSWORD", "verifier123")
    VERIFIER_EMPLOYEE_ID = os.getenv("VERIFIER_EMPLOYEE_ID", "VERIF001")
    VERIFIER_MOBILE = os.getenv("VERIFIER_MOBILE", "9000000003")
    
    # Viewer User (for development/testing)
    VIEWER_USERNAME = os.getenv("VIEWER_USERNAME", "viewer")
    VIEWER_EMAIL = os.getenv("VIEWER_EMAIL", "viewer@example.com")
    VIEWER_PASSWORD = os.getenv("VIEWER_PASSWORD", "viewer123")
    VIEWER_EMPLOYEE_ID = os.getenv("VIEWER_EMPLOYEE_ID", "VIEW001")
    VIEWER_MOBILE = os.getenv("VIEWER_MOBILE", "9000000004")
    
    # Role Constants
    SUPERADMIN_ROLE = "superadmin"
    ADMIN_ROLE = "admin"
    USER_ROLE = "user"
    VERIFIER_ROLE = "verifier"
    VIEWER_ROLE = "viewer"
    
    # SMS Service Configuration
    SMS_API_URL = os.getenv("SMS_API_URL", "")
    SMS_API_TOKEN = os.getenv("SMS_API_TOKEN", "")
    SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "")
    
    # eHospital API Configuration
    EHOSPITAL_INIT_URL = os.getenv("EHOSPITAL_INIT_URL", "")
    EHOSPITAL_FETCH_PATIENT_URL = os.getenv("EHOSPITAL_FETCH_PATIENT_URL", "")
    EHOSPITAL_USERNAME = os.getenv("EHOSPITAL_USERNAME", "")
    EHOSPITAL_PASSWORD = os.getenv("EHOSPITAL_PASSWORD", "")
    EHOSPITAL_HOSPITAL_ID = os.getenv("EHOSPITAL_HOSPITAL_ID", "0")
    
    # CDAC Service Configuration
    CDAC_AUTH_BEARER = os.getenv("CDAC_AUTH_BEARER", "")
    CDAC_SERVER = os.getenv("CDAC_SERVER", "")
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), "app", "uploads"))
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH_MB = get_int_env("MAX_CONTENT_LENGTH_MB", 600)
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_MB * 1024 * 1024
    ID_UPLOAD_MAX_MB = get_int_env("ID_UPLOAD_MAX_MB", 10)
    
    # Public Access
    ALLOW_PUBLIC_PLAYBACK = get_bool_env("ALLOW_PUBLIC_PLAYBACK", False)
    
    # Auto Migration
    AUTO_MIGRATE_ON_STARTUP = get_bool_env("AUTO_MIGRATE_ON_STARTUP", False)
    
    # Typesense Search Configuration
    TYPESENSE_HOST = os.getenv("TYPESENSE_HOST")
    TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", "8108")
    TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
    TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY")
    TYPESENSE_COLLECTION = os.getenv("TYPESENSE_COLLECTION", "videos")
    TYPESENSE_QUERY_BY = os.getenv("TYPESENSE_QUERY_BY", "title,description,transcript,tags,category")
    
    # Redis Configuration (for caching, sessions, etc.)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "/tmp/research_excellence_app.log")
    LOG_MAX_BYTES = get_int_env("LOG_MAX_BYTES", 10485760)  # 10MB
    LOG_BACKUP_COUNT = get_int_env("LOG_BACKUP_COUNT", 5)
    
    # Email Configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = get_int_env("MAIL_PORT", 587)
    MAIL_USE_TLS = get_bool_env("MAIL_USE_TLS", True)
    MAIL_USE_SSL = get_bool_env("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    
    # Application Settings
    APP_NAME = os.getenv("APP_NAME", "Research Excellence")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "AIIMS Research Excellence Portal")
    
    # API Settings
    API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
    
    # CORS Settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Rate Limiting
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200/hour")
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")
    
    # Session Configuration
    SESSION_TYPE = os.getenv("SESSION_TYPE", "filesystem")
    SESSION_FILE_DIR = os.getenv("SESSION_FILE_DIR", "/tmp/research_excellence_sessions")
    SESSION_PERMANENT = get_bool_env("SESSION_PERMANENT", False)
    SESSION_USE_SIGNER = get_bool_env("SESSION_USE_SIGNER", True)
    SESSION_KEY_PREFIX = os.getenv("SESSION_KEY_PREFIX", "research_app:")
    
    # Cache Configuration
    CACHE_TYPE = os.getenv("CACHE_TYPE", "simple")
    CACHE_DEFAULT_TIMEOUT = get_int_env("CACHE_DEFAULT_TIMEOUT", 300)
    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration."""
        # Ensure upload directory exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Ensure session directory exists
        if Config.SESSION_TYPE == "filesystem":
            os.makedirs(Config.SESSION_FILE_DIR, exist_ok=True)


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG = True
    MY_ENVIRONMENT = "DEVELOPMENT"
    
    # Database
    SQLALCHEMY_DATABASE_URI = get_database_uri(
        os.getenv("DEVELOPMENT_DATABASE_URI", "sqlite:///dev.db")
    )
    
    # Security (relaxed for development)
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    
    # Logging
    LOG_LEVEL = os.getenv("DEV_LOG_LEVEL", "DEBUG")
    
    # Auto Migration
    AUTO_MIGRATE_ON_STARTUP = get_bool_env("DEV_AUTO_MIGRATE_ON_STARTUP", True)
    
    # Development Users
    ADMIN_USERNAME = os.getenv("DEV_ADMIN_USERNAME", "dev_admin")
    ADMIN_EMAIL = os.getenv("DEV_ADMIN_EMAIL", "dev_admin@example.com")
    ADMIN_PASSWORD = os.getenv("DEV_ADMIN_PASSWORD", "dev123")
    ADMIN_EMPLOYEE_ID = os.getenv("DEV_ADMIN_EMPLOYEE_ID", "DEVADMIN001")
    ADMIN_MOBILE = os.getenv("DEV_ADMIN_MOBILE", "9000000001")
    
    USER_USERNAME = os.getenv("DEV_USER_USERNAME", "dev_user")
    USER_EMAIL = os.getenv("DEV_USER_EMAIL", "dev_user@example.com")
    USER_PASSWORD = os.getenv("DEV_USER_PASSWORD", "dev123")
    USER_EMPLOYEE_ID = os.getenv("DEV_USER_EMPLOYEE_ID", "DEVUSER001")
    USER_MOBILE = os.getenv("DEV_USER_MOBILE", "9000000002")
    
    VERIFIER_USERNAME = os.getenv("DEV_VERIFIER_USERNAME", "dev_verifier")
    VERIFIER_EMAIL = os.getenv("DEV_VERIFIER_EMAIL", "dev_verifier@example.com")
    VERIFIER_PASSWORD = os.getenv("DEV_VERIFIER_PASSWORD", "dev123")
    VERIFIER_EMPLOYEE_ID = os.getenv("DEV_VERIFIER_EMPLOYEE_ID", "DEVVERIF001")
    VERIFIER_MOBILE = os.getenv("DEV_VERIFIER_MOBILE", "9000000003")
    
    VIEWER_USERNAME = os.getenv("DEV_VIEWER_USERNAME", "dev_viewer")
    VIEWER_EMAIL = os.getenv("DEV_VIEWER_EMAIL", "dev_viewer@example.com")
    VIEWER_PASSWORD = os.getenv("DEV_VIEWER_PASSWORD", "dev123")
    VIEWER_EMPLOYEE_ID = os.getenv("DEV_VIEWER_EMPLOYEE_ID", "DEVVIEW001")
    VIEWER_MOBILE = os.getenv("DEV_VIEWER_MOBILE", "9000000004")
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Development-specific initialization
        import logging
        logging.basicConfig(level=logging.DEBUG)


class TestingConfig(Config):
    """Testing environment configuration."""
    
    TESTING = True
    MY_ENVIRONMENT = "TESTING"
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URI", "sqlite:///test.db")
    
    # Security
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret"
    
    # Test Users
    ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "test_admin")
    ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "test_admin@example.com")
    ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "test123")
    ADMIN_EMPLOYEE_ID = os.getenv("TEST_ADMIN_EMPLOYEE_ID", "TESTADMIN001")
    ADMIN_MOBILE = os.getenv("TEST_ADMIN_MOBILE", "9000000001")
    
    USER_USERNAME = os.getenv("TEST_USER_USERNAME", "test_user")
    USER_EMAIL = os.getenv("TEST_USER_EMAIL", "test_user@example.com")
    USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "test123")
    USER_EMPLOYEE_ID = os.getenv("TEST_USER_EMPLOYEE_ID", "TESTUSER001")
    USER_MOBILE = os.getenv("TEST_USER_MOBILE", "9000000002")
    
    VERIFIER_USERNAME = os.getenv("TEST_VERIFIER_USERNAME", "test_verifier")
    VERIFIER_EMAIL = os.getenv("TEST_VERIFIER_EMAIL", "test_verifier@example.com")
    VERIFIER_PASSWORD = os.getenv("TEST_VERIFIER_PASSWORD", "test123")
    VERIFIER_EMPLOYEE_ID = os.getenv("TEST_VERIFIER_EMPLOYEE_ID", "TESTVERIF001")
    VERIFIER_MOBILE = os.getenv("TEST_VERIFIER_MOBILE", "9000000003")
    
    VIEWER_USERNAME = os.getenv("TEST_VIEWER_USERNAME", "test_viewer")
    VIEWER_EMAIL = os.getenv("TEST_VIEWER_EMAIL", "test_viewer@example.com")
    VIEWER_PASSWORD = os.getenv("TEST_VIEWER_PASSWORD", "test123")
    VIEWER_EMPLOYEE_ID = os.getenv("TEST_VIEWER_EMPLOYEE_ID", "TESTVIEW001")
    VIEWER_MOBILE = os.getenv("TEST_VIEWER_MOBILE", "9000000004")
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # In-memory database for faster tests
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URI", "sqlite:///:memory:")
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Testing-specific initialization


class ProductionConfig(Config):
    """Production environment configuration."""
    
    MY_ENVIRONMENT = "PRODUCTION"
    
    # Database
    SQLALCHEMY_DATABASE_URI = get_database_uri(
        os.getenv("DATABASE_URI", "postgresql://user:password@localhost/dbname")
    )
    
    # Security (strict for production)
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_CSRF_PROTECT = True
    
    # Logging
    LOG_LEVEL = os.getenv("PROD_LOG_LEVEL", "WARNING")
    
    # Auto Migration (usually disabled in production)
    AUTO_MIGRATE_ON_STARTUP = False
    
    # Production Users (typically set via environment variables)
    ADMIN_USERNAME = os.getenv("PROD_ADMIN_USERNAME", "prod_admin")
    ADMIN_EMAIL = os.getenv("PROD_ADMIN_EMAIL", "prod_admin@example.com")
    ADMIN_EMPLOYEE_ID = os.getenv("PROD_ADMIN_EMPLOYEE_ID", "PRODADMIN001")
    ADMIN_MOBILE = os.getenv("PROD_ADMIN_MOBILE", "9000000001")
    
    USER_USERNAME = os.getenv("PROD_USER_USERNAME", "prod_user")
    USER_EMAIL = os.getenv("PROD_USER_EMAIL", "prod_user@example.com")
    USER_EMPLOYEE_ID = os.getenv("PROD_USER_EMPLOYEE_ID", "PRODUSER001")
    USER_MOBILE = os.getenv("PROD_USER_MOBILE", "9000000002")
    
    VERIFIER_USERNAME = os.getenv("PROD_VERIFIER_USERNAME", "prod_verifier")
    VERIFIER_EMAIL = os.getenv("PROD_VERIFIER_EMAIL", "prod_verifier@example.com")
    VERIFIER_EMPLOYEE_ID = os.getenv("PROD_VERIFIER_EMPLOYEE_ID", "PRODVERIF001")
    VERIFIER_MOBILE = os.getenv("PROD_VERIFIER_MOBILE", "9000000003")
    
    VIEWER_USERNAME = os.getenv("PROD_VIEWER_USERNAME", "prod_viewer")
    VIEWER_EMAIL = os.getenv("PROD_VIEWER_EMAIL", "prod_viewer@example.com")
    VIEWER_EMPLOYEE_ID = os.getenv("PROD_VIEWER_EMPLOYEE_ID", "PRODVIEW001")
    VIEWER_MOBILE = os.getenv("PROD_VIEWER_MOBILE", "9000000004")
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific initialization
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Set up file logging
        file_handler = RotatingFileHandler(
            cls.LOG_FILE, 
            maxBytes=cls.LOG_MAX_BYTES, 
            backupCount=cls.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, cls.LOG_LEVEL))


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}

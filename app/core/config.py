import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'bankflow-production-secret-key-super-secure')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'bankflow-jwt-super-secret-key-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', '24')))
    
    # Retrieve DATABASE_URL and normalize mysql:// to mysql+pymysql://
    raw_db_url = os.getenv('DATABASE_URL', 'mysql+pymysql://root@localhost:3307/bankflow')
    if raw_db_url.startswith('mysql://'):
        raw_db_url = raw_db_url.replace('mysql://', 'mysql+pymysql://', 1)
    
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection pooling settings for high-concurrency handling in MySQL InnoDB
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True
    }
    
    CORS_ORIGINS = [origin.strip() for origin in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173').split(',') if origin.strip()]


class TestConfig(Config):
    TESTING = True
    RATELIMIT_ENABLED = False
    raw_test_db_url = os.getenv('TEST_DATABASE_URL', 'mysql+pymysql://root@localhost:3307/bankflow_test')
    if raw_test_db_url.startswith('mysql://'):
        raw_test_db_url = raw_test_db_url.replace('mysql://', 'mysql+pymysql://', 1)
    SQLALCHEMY_DATABASE_URI = raw_test_db_url
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

def _build_db_config():
    raw_db_url = os.getenv('DATABASE_URL', 'mysql+pymysql://root@localhost:3307/bankflow')
    if raw_db_url.startswith('mysql://'):
        raw_db_url = raw_db_url.replace('mysql://', 'mysql+pymysql://', 1)
    
    clean_db_url = raw_db_url.split('?')[0] if '?' in raw_db_url else raw_db_url
    needs_ssl = any(kw in raw_db_url.lower() for kw in ['aivencloud.com', 'tidb', 'ssl', 'aws', 'railway'])
    
    engine_options = {
        'pool_size': 20,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True
    }
    if needs_ssl and not ('localhost' in clean_db_url or '127.0.0.1' in clean_db_url):
        engine_options['connect_args'] = {'ssl': {}}
        
    return clean_db_url, engine_options

_db_uri, _db_engine_options = _build_db_config()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'bankflow-production-secret-key-super-secure')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'bankflow-jwt-super-secret-key-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', '24')))
    
    SQLALCHEMY_DATABASE_URI = _db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _db_engine_options
    
    CORS_ORIGINS = [origin.strip() for origin in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173').split(',') if origin.strip()]


class TestConfig(Config):
    TESTING = True
    RATELIMIT_ENABLED = False
    raw_test_db_url = os.getenv('TEST_DATABASE_URL', 'mysql+pymysql://root@localhost:3307/bankflow_test')
    if raw_test_db_url.startswith('mysql://'):
        raw_test_db_url = raw_test_db_url.replace('mysql://', 'mysql+pymysql://', 1)
    SQLALCHEMY_DATABASE_URI = raw_test_db_url
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

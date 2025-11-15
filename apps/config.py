import os
import random
import string


class Config(object):
    basedir = os.path.abspath(os.path.dirname(__file__))

    # Assets Management
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')

    # Set up the App SECRET_KEY
    SECRET_KEY = os.getenv('SECRET_KEY') or ''.join(random.choice(string.ascii_lowercase) for _ in range(32))

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # PostgreSQL DB config (required)
    DB_ENGINE   = os.getenv('DB_CONNECTION', 'postgresql')
    DB_USERNAME = os.getenv('DB_USERNAME', '')
    DB_PASS     = os.getenv('DB_PASSWORD', '')
    DB_HOST     = os.getenv('DB_HOST', '')
    DB_PORT     = os.getenv('DB_PORT', '')
    DB_NAME     = os.getenv('DB_DATABASE', '')

    try:
        SQLALCHEMY_DATABASE_URI = f'{DB_ENGINE}://{DB_USERNAME}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    except Exception as e:
        print('> Error: DBMS Exception: ' + str(e))
        raise e 


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600


class DebugConfig(Config):
    DEBUG = True
    # Session Configuration for local development
    SESSION_COOKIE_SECURE = False  # Allow cookies over HTTP (not HTTPS) in development
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    # Remember me cookie
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = False  # Allow cookies over HTTP in development
    REMEMBER_COOKIE_DURATION = 3600


# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug': DebugConfig
}

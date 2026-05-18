"""
Configuration settings for the JobConnect application.

Uses environment variables for sensitive settings with sensible defaults
for development. Production should always use environment variables.
"""

import os
from pathlib import Path
from datetime import timedelta

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration class with shared settings."""

    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'jobconnect-dev-secret-key-change-in-production-2024')
    WTF_CSRF_ENABLED = True

    # Application
    APP_NAME = os.environ.get('APP_NAME', 'JobConnect')
    MAX_FILENAME_LENGTH = 255

    # Database - fix Railway's postgres:// to postgresql:// for SQLAlchemy 2.x
    @staticmethod
    def _fix_database_url(url):
        if url and url.startswith('postgres://'):
            return url.replace('postgres://', 'postgresql://', 1)
        return url

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f'sqlite:///{BASE_DIR / "instance" / "jobconnect.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Internationalization
    BABEL_DEFAULT_LOCALE = os.environ.get('BABEL_DEFAULT_LOCALE', 'es')
    BABEL_DEFAULT_TIMEZONE = 'UTC'
    LANGUAGES = {
        'en': 'English',
        'es': 'Español',
        'it': 'Italiano'
    }

    # File uploads
    UPLOAD_FOLDER = os.environ.get(
        'UPLOAD_FOLDER', str(BASE_DIR / 'uploads')
    )
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}

    # JobSpy settings (multi-platform job scraping)
    JOBSPY_SITES = ['indeed', 'linkedin', 'google', 'zip_recruiter']
    JOBSPY_COUNTRY = os.environ.get('JOBSPY_COUNTRY', 'USA')
    JOBSPY_RESULTS_WANTED = int(os.environ.get('JOBSPY_RESULTS_WANTED', 25))
    JOBSPY_HOURS_OLD = int(os.environ.get('JOBSPY_HOURS_OLD', 168))  # 7 days

    # Scraping settings (fallback)
    SCRAPING_TIMEOUT = int(os.environ.get('SCRAPING_TIMEOUT', 30))
    MAX_RETRIES = 3

    # Cache settings
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))

    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour;10 per minute"
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_STRATEGY = "fixed-window"

    # Logging
    LOG_DIR = str(BASE_DIR / 'static' / 'logs')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    @staticmethod
    def init_app(app):
        """Initialize application-specific settings."""
        # Fix Railway/Heroku postgres:// to postgresql:// for SQLAlchemy 2.x
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_url and db_url.startswith('postgres://'):
            app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace(
                'postgres://', 'postgresql://', 1
            )
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
        os.makedirs(app.config.get('LOG_DIR', 'static/logs'), exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False
    SCRAPING_DELAY = (1, 3)
    SESSION_COOKIE_SECURE = False

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        import logging
        app.logger.setLevel(logging.DEBUG)


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    USE_PROXY = True

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        import logging
        app.logger.setLevel(logging.WARNING)


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SCRAPING_DELAY = (0, 0.5)
    MAX_RETRIES = 1
    WTF_CSRF_ENABLED = False

    @staticmethod
    def init_app(app):
        Config.init_app(app)


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
